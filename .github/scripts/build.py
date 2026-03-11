"""
build.py - GitHub Pages–ready build script for marimo notebooks/apps

Features:
- Recursively scans publish/notebooks and publish/apps
- Treats first-level subfolders as categories
- Skips drafts in drafts/ automatically
- Logs empty categories for debugging
- Exits with code 1 if no notebooks or apps are found
- Generates index.html using a Jinja2 template
- Generates GitHub Pages–friendly URLs automatically
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Union

import fire
import jinja2
from loguru import logger

# ----------------------------
# CONFIGURATION
# ----------------------------
PUBLISH_DIR = Path("publish")  # Folder containing notebooks/apps ready to publish
DRAFTS_DIR = Path("drafts")    # Folder containing draft notebooks/apps

# ----------------------------
# EXPORT SINGLE NOTEBOOK/APP
# ----------------------------
def _export_html_wasm(notebook_path: Path, output_dir: Path, as_app: bool = False) -> bool:
    """
    Export a single marimo notebook or app to HTML/WebAssembly format.
    """
    output_file: Path = output_dir / notebook_path.with_suffix(".html")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["uvx", "marimo", "export", "html-wasm", "--sandbox"]
    if as_app:
        logger.info(f"Exporting {notebook_path} as app")
        cmd.extend(["--mode", "run", "--no-show-code"])
    else:
        logger.info(f"Exporting {notebook_path} as notebook")
        cmd.extend(["--mode", "edit"])

    cmd.extend([str(notebook_path), "-o", str(output_file)])

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error exporting {notebook_path}:\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error exporting {notebook_path}: {e}")
        return False

# ----------------------------
# BUILD DATA FOR TEMPLATE
# ----------------------------
def build_data(
    folder: Path,
    output_dir: Path,
    as_app: bool = False,
    base_url: str = "publish/"
) -> List[Dict]:
    """
    Build structured data for Jinja2 template rendering with GitHub Pages–friendly links.
    """
    data = []

    if not folder.exists():
        logger.warning(f"Folder does not exist: {folder}")
        return []

    # Detect first-level subfolders as categories
    categories = [p for p in folder.iterdir() if p.is_dir()]
    for category_path in categories:
        files_in_category = [f for f in category_path.rglob("*.py") if DRAFTS_DIR not in f.parents]
        if not files_in_category:
            logger.warning(f"No notebooks/apps in category: {category_path}")
            continue

        for file in files_in_category:
            output_html = output_dir / file.with_suffix(".html")
            if _export_html_wasm(file, output_dir, as_app):
                # Prepend base_url to make GitHub Pages–friendly links
                relative_path = Path(base_url) / output_html.relative_to(output_dir)
                data.append({
                    "display_name": file.stem.replace("_", " ").title(),
                    "html_path": str(relative_path.as_posix()),
                    "category": category_path.name
                })

    # Handle top-level (uncategorized) files
    top_level_files = [f for f in folder.glob("*.py") if DRAFTS_DIR not in f.parents]
    for file in top_level_files:
        output_html = output_dir / file.with_suffix(".html")
        if _export_html_wasm(file, output_dir, as_app):
            relative_path = Path(base_url) / output_html.relative_to(output_dir)
            data.append({
                "display_name": file.stem.replace("_", " ").title(),
                "html_path": str(relative_path.as_posix()),
                "category": "Uncategorized"
            })

    return data

# ----------------------------
# GENERATE INDEX.HTML
# ----------------------------
def generate_index(output_dir: Path, template_file: Path, notebooks: List[Dict], apps: List[Dict]):
    """
    Render index.html using Jinja2 template.
    """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_file.parent),
        autoescape=jinja2.select_autoescape(["html", "xml"])
    )
    template = env.get_template(template_file.name)

    # Group items by category
    def group_by_category(items: List[Dict]) -> Dict[str, List[Dict]]:
        grouped = {}
        for item in items:
            grouped.setdefault(item["category"], []).append(item)
        return grouped

    rendered = template.render(
        notebooks=group_by_category(notebooks),
        apps=group_by_category(apps)
    )

    index_path = output_dir / "index.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(rendered)
    logger.info(f"Generated index.html at {index_path}")

# ----------------------------
# MAIN ENTRY POINT
# ----------------------------
def main(
    output_dir: Union[str, Path] = "_site",
    template: Union[str, Path] = "templates/tailwind.html.j2",
    base_url: str = "publish/"  # <-- Set "" if deploying publish/ as GitHub Pages root
):
    """
    Main build process.
    """
    logger.info("Starting marimo build process")
    output_dir = Path(output_dir)
    template_file = Path(template)

    notebooks = build_data(PUBLISH_DIR / "notebooks", output_dir, as_app=False, base_url=base_url)
    apps = build_data(PUBLISH_DIR / "apps", output_dir, as_app=True, base_url=base_url)

    if not notebooks and not apps:
        logger.error("No notebooks or apps found! Exiting.")
        sys.exit(1)

    generate_index(output_dir, template_file, notebooks, apps)
    logger.info("Build completed successfully")

# Run via Fire CLI
if __name__ == "__main__":
    fire.Fire(main)
