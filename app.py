from __future__ import annotations

import json
import csv
import io
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from flask import (
    Flask,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
SALES_FILE = DATA_DIR / "sales.json"
PRODUCTS_FILE = DATA_DIR / "products.json"


def load_json(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(file_path: Path, payload: Dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def get_users() -> List[Dict[str, Any]]:
    data = load_json(USERS_FILE)
    return data.get("users", [])


def get_sales() -> List[Dict[str, Any]]:
    data = load_json(SALES_FILE)
    return data.get("sales", [])


def get_products() -> List[Dict[str, Any]]:
    data = load_json(PRODUCTS_FILE)
    return data.get("products", [])


def persist_products(products: List[Dict[str, Any]]) -> None:
    save_json(PRODUCTS_FILE, {"products": products})


def persist_sales(sales: List[Dict[str, Any]]) -> None:
    save_json(SALES_FILE, {"sales": sales})


def find_user(username: str) -> Dict[str, Any] | None:
    for user in get_users():
        if user.get("username") == username:
            return user
    return None


def require_login() -> bool:
    return bool(session.get("username"))


def is_admin() -> bool:
    """Consider 'admin' username as administrator."""
    return session.get("username") == "admin"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-secret-key"

    @app.before_request
    def ensure_data_files() -> None:
        if not USERS_FILE.exists():
            save_json(
                USERS_FILE,
                {
                    "users": [
                        {
                            "username": "admin",
                            "password": "admin123",
                            "name": "Administrador",
                        }
                    ]
                },
            )
        if not SALES_FILE.exists():
            save_json(SALES_FILE, {"sales": []})
        if not PRODUCTS_FILE.exists():
            save_json(PRODUCTS_FILE, {"products": []})

    @app.route("/")
    def index():
        if require_login():
            # send admins to sales, regular users to products (tienda)
            if session.get("username") == "admin":
                return redirect(url_for("sales_list"))
            return redirect(url_for("products_list"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = find_user(username)

            if user and user.get("password") == password:
                session["username"] = user["username"]
                session["display_name"] = user.get("name", user["username"])
                # store contact info in session when available
                session["email"] = user.get("email", "")
                session["phone"] = user.get("phone", "")
                flash(f"Bienvenido, {session['display_name']}!", "success")
                # redirect admin to sales, regular users to products
                if session.get("username") == "admin":
                    return redirect(url_for("sales_list"))
                return redirect(url_for("products_list"))

            flash("Usuario o contraseña incorrectos.", "error")

        if require_login():
            return redirect(url_for("sales_list"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Has cerrado sesión.", "info")
        return redirect(url_for("login"))

    # ----- Cart helpers (stored in cookies) -----
    def _get_cart() -> List[Dict[str, Any]]:
        raw = request.cookies.get("cart")
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    def _set_cart(response, cart: List[Dict[str, Any]]) -> None:
        try:
            response.set_cookie("cart", json.dumps(cart), max_age=60 * 60 * 24 * 30)
        except Exception:
            # if cookie too large or other error, ignore silently
            pass

    # ----- User registration (buyer) -----
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            if not username or not password:
                flash("Usuario y contraseña son requeridos.", "error")
                return render_template("register.html")
            # check existing
            if find_user(username):
                flash("El usuario ya existe.", "error")
                return render_template("register.html")
            users = get_users()
            users.append({"username": username, "password": password, "name": name, "email": email, "phone": phone})
            save_json(USERS_FILE, {"users": users})
            flash("Usuario registrado. Puedes iniciar sesión.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    # ----- Cart routes -----
    @app.route("/carrito")
    def cart_view():
        # only non-admin users (buyers) can use cart
        if not require_login():
            flash("Debes iniciar sesión para ver el carrito.", "error")
            return redirect(url_for("login"))
        if is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))
        cart = _get_cart()
        return render_template("cart.html", cart=cart)

    @app.route("/carrito/agregar", methods=["POST"])
    def cart_add():
        # only buyers can add to cart
        if not require_login():
            flash("Debes iniciar sesión para agregar al carrito.", "error")
            return redirect(url_for("login"))
        if is_admin():
            flash("Los administradores no pueden usar el carrito.", "error")
            return redirect(url_for("products_list"))

        product_id = request.form.get("product_id", "").strip()
        qty = request.form.get("quantity", "1").strip()
        try:
            qty_value = int(qty)
            if qty_value < 1:
                qty_value = 1
        except Exception:
            qty_value = 1
        prod = next((p for p in get_products() if p.get("id") == product_id), None)
        if not prod:
            flash("Producto no encontrado.", "error")
            return redirect(url_for("products_list"))
        cart = _get_cart()
        # if exists, increment
        existing = next((c for c in cart if c.get("product_id") == product_id), None)
        if existing:
            existing["quantity"] = existing.get("quantity", 0) + qty_value
        else:
            cart.append({
                "product_id": product_id,
                "name": prod.get("name"),
                "price": prod.get("price", 0),
                "quantity": qty_value,
            })
        resp = make_response(redirect(url_for("cart_view")))
        _set_cart(resp, cart)
        flash("Producto agregado al carrito.", "success")
        return resp

    @app.route("/carrito/remover", methods=["POST"])
    def cart_remove():
        if not require_login():
            flash("Debes iniciar sesión.", "error")
            return redirect(url_for("login"))
        if is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))
        product_id = request.form.get("product_id", "").strip()
        cart = _get_cart()
        new_cart = [c for c in cart if c.get("product_id") != product_id]
        resp = make_response(redirect(url_for("cart_view")))
        _set_cart(resp, new_cart)
        flash("Artículo eliminado.", "info")
        return resp

    @app.route("/carrito/checkout", methods=["POST"])
    def cart_checkout():
        if not require_login():
            flash("Debes iniciar sesión para pagar.", "error")
            return redirect(url_for("login"))
        if is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))
        # assume current user is buyer
        cart = _get_cart()
        if not cart:
            flash("El carrito está vacío.", "error")
            return redirect(url_for("cart_view"))
        sales = get_sales()
        for item in cart:
            try:
                quantity = int(item.get("quantity", 0))
                price = float(item.get("price", 0))
            except Exception:
                continue
            sale = {
                "id": str(uuid4()),
                "product": item.get("name"),
                "product_id": item.get("product_id"),
                "quantity": quantity,
                "price": price,
                "customer": {"name": session.get("display_name"), "email": session.get("email", ""), "phone": session.get("phone", "")},
                "seller": session.get("display_name"),
            }
            sales.append(sale)
            # decrement stock if product exists
            products = get_products()
            prod = next((p for p in products if p.get("id") == item.get("product_id")), None)
            if prod and isinstance(prod.get("stock"), int):
                try:
                    prod_stock = int(prod.get("stock", 0))
                    prod["stock"] = max(0, prod_stock - quantity)
                except Exception:
                    pass
            persist_products(products)
        persist_sales(sales)
        # after checkout redirect buyers to the tienda
        resp = make_response(redirect(url_for("products_list")))
        # clear cart
        _set_cart(resp, [])
        flash("Compra realizada correctamente.", "success")
        return resp

    @app.route("/ventas")
    def sales_list():
        # only admin can view sales list
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))
        sales = get_sales()
        # Normalize customer field: allow older sales where customer is a string
        for s in sales:
            cust = s.get("customer")
            if cust is None:
                s["customer"] = {"name": "", "email": "", "phone": ""}
            elif isinstance(cust, str):
                s["customer"] = {"name": cust, "email": "", "phone": ""}
            else:
                # ensure all keys exist
                s["customer"] = {
                    "name": cust.get("name", "") if isinstance(cust, dict) else str(cust),
                    "email": cust.get("email", "") if isinstance(cust, dict) else "",
                    "phone": cust.get("phone", "") if isinstance(cust, dict) else "",
                }

        return render_template("sales_list.html", sales=sales)

    @app.route("/ventas/nueva", methods=["GET", "POST"])
    def sales_create():
        # only admin can create manual sales
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))

        products = get_products()

        if request.method == "POST":
            product = request.form.get("product", "").strip()
            # allow selecting a product from inventory
            product_id = request.form.get("product_id", "").strip()
            quantity = request.form.get("quantity", "").strip()
            price = request.form.get("price", "").strip()
            # customer details
            customer_name = request.form.get("customer_name", "").strip()
            customer_email = request.form.get("customer_email", "").strip()
            customer_phone = request.form.get("customer_phone", "").strip()

            # if product selected from inventory, override name/price BEFORE validation
            if product_id:
                prod = next((p for p in products if p.get("id") == product_id), None)
                if prod:
                    product = prod.get("name", product)
                    # if price not provided, use product price
                    if not price:
                        price = str(prod.get("price", ""))

            errors = []
            if not product:
                errors.append("El producto es obligatorio.")
            if not quantity or not quantity.isdigit():
                errors.append("La cantidad debe ser un número entero.")
            if not price:
                errors.append("El precio es obligatorio.")

            try:
                price_value = float(price)
                if price_value < 0:
                    errors.append("El precio debe ser positivo.")
            except ValueError:
                errors.append("El precio debe ser numérico.")

            quantity_value = int(quantity) if quantity.isdigit() else 0

            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template(
                    "sales_form.html",
                    action="Crear",
                    sale={
                        "product": product,
                        "product_id": product_id,
                        "quantity": quantity,
                        "price": price,
                        "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                    },
                    products=products,
                )

            new_sale = {
                "id": str(uuid4()),
                "product": product,
                "product_id": product_id,
                "quantity": quantity_value,
                "price": price_value,
                "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                "seller": session.get("display_name"),
            }
            sales = get_sales()
            sales.append(new_sale)
            persist_sales(sales)
            # decrement stock if product used
            if product_id:
                prod = next((p for p in products if p.get("id") == product_id), None)
                if prod and isinstance(prod.get("stock"), int):
                    try:
                        prod_stock = int(prod.get("stock", 0))
                        if quantity_value > prod_stock:
                            flash("Stock insuficiente para el producto seleccionado.", "error")
                            return redirect(url_for("sales_create"))
                        prod["stock"] = prod_stock - quantity_value
                        persist_products(products)
                    except Exception:
                        pass
            flash("Venta creada correctamente.", "success")
            return redirect(url_for("sales_list"))
        return render_template("sales_form.html", action="Crear", sale=None, products=products)

    @app.route("/ventas/<sale_id>/editar", methods=["GET", "POST"])
    def sales_edit(sale_id: str):
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))

        sales = get_sales()
        sale = next((item for item in sales if item["id"] == sale_id), None)
        if sale is None:
            abort(404, description="Venta no encontrada")

        # Normalize existing sale customer to dict for editing
        cust = sale.get("customer")
        if cust is None:
            sale["customer"] = {"name": "", "email": "", "phone": ""}
        elif isinstance(cust, str):
            sale["customer"] = {"name": cust, "email": "", "phone": ""}
        else:
            sale["customer"] = {
                "name": cust.get("name", "") if isinstance(cust, dict) else str(cust),
                "email": cust.get("email", "") if isinstance(cust, dict) else "",
                "phone": cust.get("phone", "") if isinstance(cust, dict) else "",
            }

        products = get_products()

        if request.method == "POST":
            product = request.form.get("product", "").strip()
            product_id = request.form.get("product_id", "").strip()
            quantity = request.form.get("quantity", "").strip()
            price = request.form.get("price", "").strip()
            customer_name = request.form.get("customer_name", "").strip()
            customer_email = request.form.get("customer_email", "").strip()
            customer_phone = request.form.get("customer_phone", "").strip()

            # if product selected from inventory, override name/price BEFORE validation
            if product_id:
                prod = next((p for p in products if p.get("id") == product_id), None)
                if prod:
                    product = prod.get("name", product)
                    if not price:
                        price = str(prod.get("price", ""))

            errors = []
            if not product:
                errors.append("El producto es obligatorio.")
            if not quantity or not quantity.isdigit():
                errors.append("La cantidad debe ser un número entero.")
            if not price:
                errors.append("El precio es obligatorio.")

            try:
                price_value = float(price)
                if price_value < 0:
                    errors.append("El precio debe ser positivo.")
            except ValueError:
                errors.append("El precio debe ser numérico.")

            quantity_value = int(quantity) if quantity.isdigit() else sale["quantity"]

            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template(
                    "sales_form.html",
                    action="Editar",
                    sale={
                        "id": sale["id"],
                        "product": product,
                        "product_id": product_id,
                        "quantity": quantity,
                        "price": price,
                        "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                    },
                    products=products,
                )

            sale.update(
                {
                    "product": product,
                    "product_id": product_id,
                    "quantity": quantity_value,
                    "price": price_value,
                    "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                }
            )
            persist_sales(sales)
            flash("Venta actualizada.", "success")
            return redirect(url_for("sales_list"))

        return render_template("sales_form.html", action="Editar", sale=sale, products=products)

    @app.route("/ventas/<sale_id>/eliminar", methods=["POST"])
    def sales_delete(sale_id: str):
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))

        sales = get_sales()
        new_sales = [sale for sale in sales if sale["id"] != sale_id]
        if len(new_sales) == len(sales):
            abort(404, description="Venta no encontrada")

        persist_sales(new_sales)
        flash("Venta eliminada.", "info")
        return redirect(url_for("sales_list"))

    @app.route("/ventas/reporte")
    def sales_report():
        """Genera un CSV con todas las ventas y el inventario y lo devuelve como descarga."""
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))

        sales = get_sales()

        # Normalize customer info
        for s in sales:
            cust = s.get("customer")
            if cust is None:
                s["customer"] = {"name": "", "email": "", "phone": ""}
            elif isinstance(cust, str):
                s["customer"] = {"name": cust, "email": "", "phone": ""}
            else:
                s["customer"] = {
                    "name": cust.get("name", "") if isinstance(cust, dict) else str(cust),
                    "email": cust.get("email", "") if isinstance(cust, dict) else "",
                    "phone": cust.get("phone", "") if isinstance(cust, dict) else "",
                }

        # Produce an Excel (.xlsx) file with two sheets: Sales and Inventory.
        # openpyxl is required. If missing, inform the admin and redirect back.
        try:
            from openpyxl import Workbook
        except Exception:
            flash("No se puede generar el reporte: falta la librería 'openpyxl'. Instala con: pip install openpyxl", "error")
            return redirect(url_for("sales_list"))

        wb = Workbook()
        ws_sales = wb.active
        ws_sales.title = "Sales"

        sales_header = [
            "id",
            "product",
            "quantity",
            "price",
            "seller",
            "customer_name",
            "customer_email",
            "customer_phone",
            "total",
        ]
        ws_sales.append(sales_header)

        for s in sales:
            cust = s.get("customer", {}) or {}
            qty = s.get("quantity", 0)
            price = s.get("price", 0)
            total = qty * price if isinstance(qty, (int, float)) and isinstance(price, (int, float)) else ""
            ws_sales.append([
                s.get("id", ""),
                s.get("product", ""),
                qty,
                price,
                s.get("seller", ""),
                cust.get("name", ""),
                cust.get("email", ""),
                cust.get("phone", ""),
                total,
            ])

        # Inventory sheet
        ws_inv = wb.create_sheet(title="Inventory")
        inv_header = ["inventory_id", "name", "sku", "price", "stock"]
        ws_inv.append(inv_header)
        products = get_products()
        for p in products:
            ws_inv.append([
                p.get("id", ""),
                p.get("name", ""),
                p.get("sku", ""),
                p.get("price", ""),
                p.get("stock", ""),
            ])

        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        resp = Response(bio.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp.headers["Content-Disposition"] = "attachment; filename=reporte_ventas_e_inventario.xlsx"
        return resp

    # --- Inventory (products) CRUD ---
    @app.route("/inventario")
    def products_list():
        # allow both admin and users to view products; render differs in template
        if not require_login():
            return redirect(url_for("login"))
        products = get_products()
        return render_template("products_list.html", products=products)

    @app.route("/inventario/nuevo", methods=["GET", "POST"])
    def product_create():
        # only admin can create products
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            sku = request.form.get("sku", "").strip()
            price = request.form.get("price", "").strip()
            stock = request.form.get("stock", "").strip()
            image_base64 = request.form.get("image_base64", "").strip()

            errors = []
            if not name:
                errors.append("El nombre es obligatorio.")
            try:
                price_value = float(price) if price else 0.0
                if price_value < 0:
                    errors.append("El precio debe ser positivo.")
            except ValueError:
                errors.append("El precio debe ser numérico.")
            try:
                stock_value = int(stock) if stock else 0
                if stock_value < 0:
                    errors.append("El stock no puede ser negativo.")
            except ValueError:
                errors.append("El stock debe ser un número entero.")

            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("products_form.html", action="Crear", product={"name": name, "sku": sku, "price": price, "stock": stock})

            new_prod = {"id": str(uuid4()), "name": name, "sku": sku, "price": price_value, "stock": stock_value, "image_base64": image_base64}
            products = get_products()
            products.append(new_prod)
            persist_products(products)
            flash("Producto agregado.", "success")
            return redirect(url_for("products_list"))

        return render_template("products_form.html", action="Crear", product=None)

    @app.route("/inventario/<product_id>/editar", methods=["GET", "POST"])
    def product_edit(product_id: str):
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))

        products = get_products()
        prod = next((p for p in products if p.get("id") == product_id), None)
        if not prod:
            abort(404, description="Producto no encontrado")

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            sku = request.form.get("sku", "").strip()
            price = request.form.get("price", "").strip()
            stock = request.form.get("stock", "").strip()
            image_base64 = request.form.get("image_base64", "").strip()

            errors = []
            if not name:
                errors.append("El nombre es obligatorio.")
            try:
                price_value = float(price) if price else 0.0
                if price_value < 0:
                    errors.append("El precio debe ser positivo.")
            except ValueError:
                errors.append("El precio debe ser numérico.")
            try:
                stock_value = int(stock) if stock else 0
                if stock_value < 0:
                    errors.append("El stock no puede ser negativo.")
            except ValueError:
                errors.append("El stock debe ser un número entero.")

            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("products_form.html", action="Editar", product={"id": product_id, "name": name, "sku": sku, "price": price, "stock": stock})

            prod.update({"name": name, "sku": sku, "price": price_value, "stock": stock_value, "image_base64": image_base64})
            persist_products(products)
            flash("Producto actualizado.", "success")
            return redirect(url_for("products_list"))

        return render_template("products_form.html", action="Editar", product=prod)

    @app.route("/inventario/<product_id>/eliminar", methods=["POST"])
    def product_delete(product_id: str):
        if not require_login() or not is_admin():
            flash("Acceso denegado.", "error")
            return redirect(url_for("products_list"))
        products = get_products()
        new_products = [p for p in products if p.get("id") != product_id]
        if len(new_products) == len(products):
            abort(404, description="Producto no encontrado")
        persist_products(new_products)
        flash("Producto eliminado.", "info")
        return redirect(url_for("products_list"))

    return app


if __name__ == "__main__":
    flask_app = create_app()
    # Escucha en todas las interfaces (necesario para EC2)
    flask_app.run(host="0.0.0.0", port=5000, debug=True)
