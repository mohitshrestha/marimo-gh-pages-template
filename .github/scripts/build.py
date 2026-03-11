"""
Build script for marimo notebooks/apps.

- Scans publish/notebooks and publish/apps (recursively)
- Handles nested folders as categories
- Skips drafts automatically
- Logs empty categories for debugging
- Exits with code 1 if no notebooks or apps found
- Generates index.html using Jinja2 templates
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Union

import fire
import jinja2
from loguru import logger

# ----------------------------
# CONFIG
# ----------------------------
PUBLISH_DIR = Path("publish")
DRAFTS_DIR = Path("drafts")


# ----------------------------
# EXPORT FUNCTION
# ----------------------------
def _export_html_wasm(notebook_path: Path, output_dir: Path, as_app: bool = False) -> bool:
    """Export a single marimo notebook to HTML/WebAssembly."""
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
        logger.debug(f"Command succeeded: {' '.join(cmd)}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error exporting {notebook_path}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error exporting {notebook_path}: {e}")
        return False


# ----------------------------
# COLLECT FILES FUNCTION
# ----------------------------
def collect_files(folder: Path) -> List[Path]:
    """Recursively collect all Python files in a folder."""
    if not folder.exists():
        return []
    return sorted(folder.rglob("*.py"))


# ----------------------------
# BUILD DATA FUNCTION
# ----------------------------
def build_data(folder: Path, output_dir: Path, as_app: bool = False) -> List[Dict]:
    """
    Build structured data for template rendering.
    - Groups files by first-level subfolder (category)
    - Logs empty categories
    """
    data = []

    if not folder.exists():
        logger.warning(f"Folder does not exist: {folder}")
        return []

    # Find all categories (first-level subfolders)
    for category_path in [p for p in folder.rglob("*") if p.is_dir() and p.parent == folder]:
        category_files = [f for f in category_path.rglob("*.py") if DRAFTS_DIR not in f.parents]
        if not category_files:
            logger.warning(f"No notebooks/apps in category: {category_path}")
            continue
        for file in category_files:
            html_path = output_dir / file.with_suffix(".html")
            if _export_html_wasm(file, output_dir, as_app):
                data.append({
                    "display_name": file.stem.replace("_", " ").title(),
                    "html_path": str(html_path.relative_to(output_dir)),
                    "category": category_path.name
                })

    # Also handle files directly under the folder (Uncategorized)
    top_level_files = [f for f in folder.glob("*.py") if DRAFTS_DIR not in f.parents]
    for file in top_level_files:
        html_path = output_dir / file.with_suffix(".html")
        if _export_html_wasm(file, output_dir, as_app):
            data.append({
                "display_name": file.stem.replace("_", " ").title(),
                "html_path": str(html_path.relative_to(output_dir)),
                "category": "Uncategorized"
            })

    return data


# ----------------------------
# INDEX GENERATION FUNCTION
# ----------------------------
def generate_index(output_dir: Path, template_file: Path, notebooks: List[Dict], apps: List[Dict]):
    """Render index.html using Jinja2 template, grouped by category."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_file.parent),
                             autoescape=jinja2.select_autoescape(["html", "xml"]))
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
# MAIN FUNCTION
# ----------------------------
def main(output_dir: Union[str, Path] = "_site", template: Union[str, Path] = "templates/tailwind.html.j2"):
    logger.info("Starting build process")
    output_dir = Path(output_dir)
    template_file = Path(template)

    # Export notebooks and apps
    notebooks = build_data(PUBLISH_DIR / "notebooks", output_dir, as_app=False)
    apps = build_data(PUBLISH_DIR / "apps", output_dir, as_app=True)

    # Exit if nothing to build
    if not notebooks and not apps:
        logger.error("No notebooks or apps found! Exiting.")
        sys.exit(1)

    generate_index(output_dir, template_file, notebooks, apps)
    logger.info("Build completed successfully")


if __name__ == "__main__":
    fire.Fire(main)
