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


def persist_sales(sales: List[Dict[str, Any]]) -> None:
    save_json(SALES_FILE, {"sales": sales})


def find_user(username: str) -> Dict[str, Any] | None:
    for user in get_users():
        if user.get("username") == username:
            return user
    return None


def require_login() -> bool:
    return bool(session.get("username"))


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

    @app.route("/")
    def index():
        if require_login():
            return redirect(url_for("sales_list"))
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
                flash(f"Bienvenido, {session['display_name']}!", "success")
                return redirect(url_for("sales_list"))

            flash("Usuario o contraseña incorrectos.", "error")

        if require_login():
            return redirect(url_for("sales_list"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Has cerrado sesión.", "info")
        return redirect(url_for("login"))

    @app.route("/ventas")
    def sales_list():
        if not require_login():
            return redirect(url_for("login"))
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
        if not require_login():
            return redirect(url_for("login"))

        if request.method == "POST":
            product = request.form.get("product", "").strip()
            quantity = request.form.get("quantity", "").strip()
            price = request.form.get("price", "").strip()
            # customer details
            customer_name = request.form.get("customer_name", "").strip()
            customer_email = request.form.get("customer_email", "").strip()
            customer_phone = request.form.get("customer_phone", "").strip()

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
                        "quantity": quantity,
                        "price": price,
                        "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                    },
                )

            new_sale = {
                "id": str(uuid4()),
                "product": product,
                "quantity": quantity_value,
                "price": price_value,
                "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                "seller": session.get("display_name"),
            }
            sales = get_sales()
            sales.append(new_sale)
            persist_sales(sales)
            flash("Venta creada correctamente.", "success")
            return redirect(url_for("sales_list"))

        return render_template("sales_form.html", action="Crear", sale=None)

    @app.route("/ventas/<sale_id>/editar", methods=["GET", "POST"])
    def sales_edit(sale_id: str):
        if not require_login():
            return redirect(url_for("login"))

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

        if request.method == "POST":
            product = request.form.get("product", "").strip()
            quantity = request.form.get("quantity", "").strip()
            price = request.form.get("price", "").strip()
            customer_name = request.form.get("customer_name", "").strip()
            customer_email = request.form.get("customer_email", "").strip()
            customer_phone = request.form.get("customer_phone", "").strip()

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
                        "quantity": quantity,
                        "price": price,
                        "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                    },
                )

            sale.update(
                {
                    "product": product,
                    "quantity": quantity_value,
                    "price": price_value,
                    "customer": {"name": customer_name, "email": customer_email, "phone": customer_phone},
                }
            )
            persist_sales(sales)
            flash("Venta actualizada.", "success")
            return redirect(url_for("sales_list"))

        return render_template("sales_form.html", action="Editar", sale=sale)

    @app.route("/ventas/<sale_id>/eliminar", methods=["POST"])
    def sales_delete(sale_id: str):
        if not require_login():
            return redirect(url_for("login"))

        sales = get_sales()
        new_sales = [sale for sale in sales if sale["id"] != sale_id]
        if len(new_sales) == len(sales):
            abort(404, description="Venta no encontrada")

        persist_sales(new_sales)
        flash("Venta eliminada.", "info")
        return redirect(url_for("sales_list"))

    @app.route("/ventas/reporte")
    def sales_report():
        """Genera un CSV con todas las ventas y lo devuelve como descarga."""
        if not require_login():
            return redirect(url_for("login"))

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

        output = io.StringIO()
        writer = csv.writer(output)
        # Header
        writer.writerow([
            "id",
            "product",
            "quantity",
            "price",
            "seller",
            "customer_name",
            "customer_email",
            "customer_phone",
            "total",
        ])

        for s in sales:
            cust = s.get("customer", {}) or {}
            qty = s.get("quantity", 0)
            price = s.get("price", 0)
            total = qty * price if isinstance(qty, (int, float)) and isinstance(price, (int, float)) else ""
            writer.writerow(
                [
                    s.get("id", ""),
                    s.get("product", ""),
                    qty,
                    price,
                    s.get("seller", ""),
                    cust.get("name", ""),
                    cust.get("email", ""),
                    cust.get("phone", ""),
                    total,
                ]
            )

        csv_data = output.getvalue()
        output.close()

        resp = Response(csv_data, mimetype="text/csv")
        resp.headers["Content-Disposition"] = "attachment; filename=reporte_ventas.csv"
        return resp

    return app


if __name__ == "__main__":
    flask_app = create_app()
    # Escucha en todas las interfaces (necesario para EC2)
    flask_app.run(host="0.0.0.0", port=5000, debug=True)
