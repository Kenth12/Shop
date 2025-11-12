# Tienda_ropa — despliegue en Netlify (sitio estático)

Este repositorio contiene una pequeña aplicación Flask que gestiona ventas y usuarios.
Para desplegar en Netlify se genera una versión estática del sitio usando Frozen-Flask.

Resumen rápido
- Ejecutar `python freeze.py` genera el sitio estático en la carpeta `build/`.
- Netlify está configurado mediante `netlify.toml` para instalar dependencias y ejecutar ese script automáticamente.

Limitaciones importantes
- El sitio resultante es estático: formularios (POST), sesiones dinámicas y escritura a `data/*.json` NO funcionarán en producción.
- Si necesitas edición o persistencia en la web, despliega el backend Flask en un host con Python (Render/Railway) y conecta el frontend a la API.

Pasos para preparar y desplegar (local)

1. Crear virtualenv e instalar dependencias:

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Generar sitio estático:

```zsh
python freeze.py
# -> genera ./build/
```

3. Probar localmente el contenido estático:

```zsh
python -m http.server --directory build 8080
# abrir http://127.0.0.1:8080
```

Cómo desplegar en Netlify

1. Empuja este repositorio a GitHub (o Git provider soportado).
2. En Netlify, crea un nuevo sitio desde Git y conecta tu repo.
3. Netlify usará `netlify.toml`. El build command instalará las dependencias y ejecutará `python freeze.py`.
4. Publish directory: `build` (ya viene configurado en `netlify.toml`).
5. En Site settings > Build & deploy > Environment, añade `SECRET_KEY` si deseas reemplazar el valor por defecto.

Notas finales
- Antes de ejecutar `python freeze.py` en Netlify, asegúrate de que `data/sales.json` contiene las páginas que quieres publicar (los IDs de ventas). El freeze genera páginas a partir de los datos actuales.
- Si quieres que te prepare un flujo con backend dinámico en Render en lugar de Netlify, dímelo y lo preparo.
