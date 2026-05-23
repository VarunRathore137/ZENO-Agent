import shutil
from pathlib import Path

def create_config():
    """
    Copy the default config template to ~/Zeno/config.yaml if it doesn't exist.
    """
    repo_root = Path(__file__).parent.parent
    template_path = repo_root / "templates" / "config.yaml.template"
    target_dir = Path.home() / "Zeno"
    target_path = target_dir / "config.yaml"
    
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}")
        return
    
    if target_path.exists():
        print(f"Config already exists at {target_path}, skipping.")
        return
    
    # Ensure target directory exists (though init_db should have done this)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating default config at {target_path}...")
    shutil.copy(template_path, target_path)
    print("Success.")

if __name__ == "__main__":
    create_config()
