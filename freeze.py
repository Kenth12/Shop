from pathlib import Path
import os
import json

from flask_frozen import Freezer

from app import create_app

app = create_app()
freezer = Freezer(app)


@freezer.register_generator
def sales_edit():
    """Generate arguments for the `sales_edit` endpoint so pages like
    `/ventas/<sale_id>/editar` are frozen.
    """
    data_file = Path(__file__).resolve().parent / "data" / "sales.json"
    if not data_file.exists():
        return
    with data_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
        sales = data.get("sales", [])
    for s in sales:
        sale_id = s.get("id")
        if sale_id:
            yield {"sale_id": sale_id}


if __name__ == "__main__":
    # Ensure FREEZE is set so the app bypasses login and renders as if an
    # authenticated user is present during the build step.
    os.environ["FREEZE"] = "1"
    freezer.freeze()
