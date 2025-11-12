from pathlib import Path
import os
import json

from app import create_app

if __name__ == "__main__":
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
    
    print("=== Generating LOGIN page (without FREEZE) ===")
    # Generate login page WITHOUT FREEZE (so it shows actual login form)
    app_no_freeze = create_app()
    with app_no_freeze.test_client() as client:
        response = client.get('/login/')
        if response.status_code == 200:
            # Save as index.html (main entry point)
            with (build_dir / 'index.html').open('w', encoding='utf-8') as f:
                f.write(response.data.decode('utf-8'))
            print(f"✓ Generated: index.html (login page)")
            
            # Also save in /login/ for consistency
            login_dir = build_dir / 'login'
            login_dir.mkdir(exist_ok=True)
            with (login_dir / 'index.html').open('w', encoding='utf-8') as f:
                f.write(response.data.decode('utf-8'))
            print(f"✓ Generated: login/index.html")
        else:
            print(f"✗ Failed to generate login (status {response.status_code})")
    
    print("\n=== Generating VENTAS pages (with FREEZE) ===")
    # Generate ventas pages WITH FREEZE (simulate logged in)
    os.environ["FREEZE"] = "1"
    app_freeze = create_app()
    
    with app_freeze.test_client() as client:
        ventas_pages = [
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
                        ventas_pages.append((
                            f'/ventas/{sale_id}/editar/',
                            f'ventas/{sale_id}/editar/index.html'
                        ))
        
        # Generate each ventas page
        for url, filepath in ventas_pages:
            response = client.get(url)
            if response.status_code == 200:
                full_path = build_dir / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with full_path.open('w', encoding='utf-8') as f:
                    f.write(response.data.decode('utf-8'))
                print(f"✓ Generated: {filepath}")
            else:
                print(f"✗ Failed: {url} (status {response.status_code})")
    
    print(f"\n✅ Build complete! Files in: {build_dir.absolute()}")
