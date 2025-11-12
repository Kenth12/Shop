# 🛍️ Tienda de Ropa - Sistema CRUD de Ventas

Aplicación Flask para gestionar ventas de una tienda de ropa con autenticación y CRUD completo.

## ✨ Características

- 🔐 Sistema de login con sesiones
- 📊 CRUD completo de ventas (Crear, Leer, Actualizar, Eliminar)
- 💾 Persistencia en archivos JSON
- 🎨 Interfaz moderna con gradientes y iconos SVG
- 📱 Diseño responsive

## 🚀 Despliegue en Render.com

### Opción 1: Deploy Automático (Recomendado)

1. **Sube tu código a GitHub** (ya lo tienes listo)

2. **Crea cuenta en Render.com**
   - Ve a [render.com](https://render.com)
   - Regístrate con tu cuenta de GitHub

3. **Conecta tu repositorio**
   - Click en "New +" → "Web Service"
   - Conecta tu repo: `Kenth12/Shop`
   - Branch: `develop`

4. **Configuración automática**
   - Render detectará el archivo `render.yaml` automáticamente
   - Click en "Create Web Service"
   
5. **¡Listo!** 🎉
   - Tu app estará disponible en: `https://tienda-ropa.onrender.com`
   - Los deploys futuros son automáticos con cada push a GitHub

### Opción 2: Deploy Manual

Si prefieres configurar manualmente:

1. En Render.com → "New Web Service"
2. Conecta tu repo `Kenth12/Shop`
3. Configura:
   - **Name**: `tienda-ropa`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

4. Variables de entorno (opcional):
   - `SECRET_KEY`: Render lo genera automáticamente

## 💻 Desarrollo Local

### Instalación

```bash
# Clonar repo
git clone https://github.com/Kenth12/Shop.git
cd Shop

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Ejecutar localmente

```bash
# Activar entorno virtual
source .venv/bin/activate

# Iniciar servidor
python app.py
```

La app estará disponible en: `http://localhost:5000`

### Credenciales por defecto

- **Usuario**: `admin`
- **Contraseña**: `admin123`

## 📁 Estructura del Proyecto

```
tienda_ropa/
├── app.py                 # Aplicación Flask principal
├── wsgi.py               # Entry point para Gunicorn
├── requirements.txt      # Dependencias Python
├── render.yaml          # Configuración de Render.com
├── Procfile             # Para otros servicios (Railway, Heroku)
├── data/
│   ├── users.json       # Usuarios del sistema
│   └── sales.json       # Datos de ventas
├── static/
│   └── css/
│       └── styles.css   # Estilos modernos
└── templates/
    ├── base.html        # Plantilla base
    ├── login.html       # Página de login
    ├── sales_list.html  # Lista de ventas
    └── sales_form.html  # Formulario crear/editar
```

## 🔧 Tecnologías

- **Backend**: Flask 2.0+
- **Server**: Gunicorn
- **Frontend**: HTML5, CSS3, JavaScript
- **Diseño**: Gradientes CSS, SVG Icons
- **Persistencia**: JSON files

## 📝 Funcionalidades CRUD

- ✅ **Crear**: Agregar nuevas ventas con producto, cliente, cantidad y precio
- ✅ **Leer**: Visualizar lista de ventas con diseño moderno
- ✅ **Actualizar**: Editar información de ventas existentes
- ✅ **Eliminar**: Borrar ventas con confirmación

## 🎨 Diseño UI

- Fondo con gradiente púrpura/azul
- Botones con efectos hover y transiciones
- Iconos SVG inline para mejor rendimiento
- Tablas con hover effects
- Sistema de badges y alerts
- Glassmorphism en el header

## 🔐 Seguridad

- Autenticación con sesiones Flask
- Protección de rutas con decorador `require_login`
- SECRET_KEY generado automáticamente en Render
- Confirmación antes de eliminar registros

## 📊 Datos de Ejemplo

El sistema incluye 2 ventas de ejemplo:
- Camiseta: $19.99 (2 unidades)
- Pantalones: $39.99 (1 unidad)

## 🐛 Solución de Problemas

### Error al iniciar en Render

Si el deploy falla, verifica:
1. El archivo `render.yaml` existe en la raíz
2. Las dependencias en `requirements.txt` están correctas
3. La variable `SECRET_KEY` está configurada

### Datos no persisten

Los archivos JSON se crean automáticamente en:
- `/data/users.json`
- `/data/sales.json`

En Render, estos archivos se reinician con cada deploy (es normal en el plan Free).

## 📄 Licencia

MIT License - Siéntete libre de usar este proyecto como base para tus aplicaciones.

## 👤 Autor

Kenneth Mendoza (@Kenth12)

---

**¿Preguntas o sugerencias?** Abre un issue en GitHub.
