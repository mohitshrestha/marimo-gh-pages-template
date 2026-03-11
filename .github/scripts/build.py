"""
Build script for publishing notebooks and apps to GitHub Pages.

Features:
- Automatically detects notebooks and apps in `publish/` folder.
- Supports nested folders for categories.
- Skips draft files stored in `drafts/` folder.
- Generates an index.html grouped by category.
- Logs empty categories for easier debugging.
- Tool-agnostic: works with Python scripts, Jupyter, Quarto, etc.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Union
import jinja2
import fire
from loguru import logger

# -----------------------------------------------
# CONFIGURATION
# -----------------------------------------------
PUBLISH_DIR = Path("publish")
DRAFTS_DIR = Path("drafts")


# -----------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------
def human_readable_name(file: Path) -> str:
    """Convert a filename to a readable title for display."""
    return file.stem.replace("_", " ").title()


def collect_files(folder: Path) -> List[Path]:
    """Recursively collect all .py files under a folder."""
    if not folder.exists():
        return []
    return sorted(folder.rglob("*.py"))  # sorted for consistent ordering


def export_file(file: Path, output_dir: Path, as_app: bool = False) -> Path:
    """
    Export a Python script or notebook to HTML.
    Placeholder: currently copies the file or runs Marimo export.
    """
    output_file = output_dir / file.with_suffix(".html")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # TODO: Replace with your actual export command for Marimo or other tools
    # Example:
    # cmd = ["uvx", "marimo", "export", "html-wasm", str(file), "-o", str(output_file)]
    # if as_app:
    #     cmd.extend(["--mode", "run", "--no-show-code"])
    # else:
    #     cmd.extend(["--mode", "edit"])
    # subprocess.run(cmd, check=True)

    # For now, just create an empty HTML file as placeholder
    output_file.write_text(f"<h1>{human_readable_name(file)}</h1>")
    logger.info(f"Exported {file} → {output_file}")
    return output_file


def build_data(folder: Path, output_dir: Path, as_app: bool = False) -> List[Dict]:
    """
    Build structured data for template rendering:
    - groups files by first-level subfolder (category)
    - creates display_name and html_path
    - logs empty categories
    """
    data = []
    categories_seen = set()

    for file in collect_files(folder):
        # Skip drafts
        if DRAFTS_DIR in file.parents:
            logger.info(f"Skipping draft: {file}")
            continue

        # Determine category
        category = file.parent.relative_to(folder).parts[0] if file.parent != folder else "Uncategorized"
        categories_seen.add(category)

        html_path = export_file(file, output_dir, as_app)
        data.append({
            "display_name": human_readable_name(file),
            "html_path": str(html_path.relative_to(output_dir)),
            "category": category
        })

    # Optional logging: detect empty categories
    all_categories = {p.name for p in folder.iterdir() if p.is_dir()} or {"Uncategorized"}
    empty_categories = all_categories - categories_seen
    for cat in empty_categories:
        logger.warning(f"No notebooks/apps found in category: '{cat}'")

    return data


def generate_index(output_dir: Path, template_file: Path, notebooks: List[Dict], apps: List[Dict]):
    """Render index.html using Jinja2 template, grouped by category."""
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
    logger.info(f"Generated homepage: {index_path}")


# -----------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------
def main(
    output_dir: Union[str, Path] = "_site",
    template: Union[str, Path] = "templates/tailwind.html.j2"
):
    """
    Build the website:
    1. Export notebooks and apps from publish/ folder.
    2. Skip drafts automatically.
    3. Log empty categories.
    4. Generate grouped index.html.
    5. Exit with code 1 if no files found (GitHub Actions fails explicitly).
    """
    output_dir = Path(output_dir)
    template_file = Path(template)

    logger.info("Starting build process")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Using template: {template_file}")

    # Export notebooks and apps
    notebooks = build_data(PUBLISH_DIR / "notebooks", output_dir, as_app=False)
    apps = build_data(PUBLISH_DIR / "apps", output_dir, as_app=True)

    # Exit with proper code if nothing to publish
    if not notebooks and not apps:
        logger.error("No notebooks or apps found to publish! Exiting with code 1.")
        sys.exit(1)

    generate_index(output_dir, template_file, notebooks, apps)
    logger.info("Build completed successfully.")


if __name__ == "__main__":
    fire.Fire(main)
