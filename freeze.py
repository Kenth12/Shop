from pathlib import Path
import os
import json

from flask_frozen import Freezer, walk_directory

from app import create_app

# Set FREEZE before creating the app
os.environ["FREEZE"] = "1"

app = create_app()

# Configure freezer
app.config['FREEZER_DESTINATION'] = 'build'
app.config['FREEZER_RELATIVE_URLS'] = True

freezer = Freezer(app)


if __name__ == "__main__":
    # Freeze only specific URLs, avoiding POST-only endpoints
    with app.test_client() as client:
        # Create build directory
        build_dir = Path('build')
        build_dir.mkdir(exist_ok=True)
        
        # Copy static files
        import shutil
        static_src = Path('static')
        static_dst = build_dir / 'static'
        if static_src.exists():
            if static_dst.exists():
                shutil.rmtree(static_dst)
            shutil.copytree(static_src, static_dst)
        
        # Freeze pages manually
        pages = [
            ('/', 'index.html'),
            ('/login/', 'login/index.html'),
            ('/ventas/', 'ventas/index.html'),
            ('/ventas/nueva/', 'ventas/nueva/index.html'),
        ]
        
        # Add sale edit pages
        data_file = Path("data/sales.json")
        if data_file.exists():
            with data_file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                sales = data.get("sales", [])
                for s in sales:
                    sale_id = s.get("id")
                    if sale_id:
                        pages.append((
                            f'/ventas/{sale_id}/editar/',
                            f'ventas/{sale_id}/editar/index.html'
                        ))
        
        # Generate HTML for each page
        for url, filepath in pages:
            response = client.get(url, follow_redirects=True)
            if response.status_code == 200:
                full_path = build_dir / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with full_path.open('w', encoding='utf-8') as f:
                    f.write(response.data.decode('utf-8'))
                print(f"✓ Generated: {filepath}")
            else:
                print(f"✗ Failed: {url} (status {response.status_code})")
