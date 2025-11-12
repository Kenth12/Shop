from pathlib import Path
import os
import json

from flask_frozen import Freezer

from app import create_app

# Set FREEZE before creating the app so it's available during initialization
os.environ["FREEZE"] = "1"

app = create_app()

# Configure freezer
app.config['FREEZER_DESTINATION'] = 'build'
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_IGNORE_MIMETYPE_WARNINGS'] = True

freezer = Freezer(app)


# Register custom URL generators that return URLs with trailing slashes
@freezer.register_generator
def index():
    yield '/'


@freezer.register_generator
def login():
    yield '/login/'


@freezer.register_generator
def logout():
    yield '/logout/'


@freezer.register_generator
def sales_list():
    yield '/ventas/'


@freezer.register_generator
def sales_create():
    yield '/ventas/nueva/'


@freezer.register_generator
def sales_edit():
    """Generate sale edit pages with trailing slashes."""
    data_file = Path(__file__).resolve().parent / "data" / "sales.json"
    if not data_file.exists():
        return
    with data_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
        sales = data.get("sales", [])
    for s in sales:
        sale_id = s.get("id")
        if sale_id:
            # Return dict with sale_id for url_for, but we need to ensure trailing slash
            yield {'sale_id': sale_id}


if __name__ == "__main__":
    freezer.freeze()
