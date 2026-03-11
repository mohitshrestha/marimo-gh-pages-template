"""
Build script for publishing notebooks and apps to GitHub Pages.

Features:
- Detects notebooks and apps in `publish/` folder, supports nested subfolders.
- Skips drafts stored in `drafts/` folder.
- Generates structured data for Jinja2 templates grouped by first-level category.
- Logs empty categories for better debugging.
- Exits with proper exit codes to ensure GitHub Actions detect failures.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Union
import jinja2
import fire
from loguru import logger
import sys

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
    Placeholder: currently writes minimal HTML.
    Replace with actual export logic (Marimo, Jupyter, Quarto, etc.).
    """
    # Determine output path preserving folder structure
    relative_path = file.relative_to(PUBLISH_DIR)
    output_file = output_dir / relative_path.with_suffix(".html")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Placeholder export (replace with actual export commands)
    output_file.write_text(f"<h1>{human_readable_name(file)}</h1>")
    logger.info(f"Exported {file} → {output_file}")
    return output_file


def build_data(folder: Path, output_dir: Path, as_app: bool = False) -> List[Dict]:
    """
    Build structured data for template rendering:
    - Groups files by first-level subfolder (category)
    - Skips drafts
    - Logs empty categories
    """
    files = collect_files(folder)
    data = []
    categories_seen = set()

    # Gather files and categories
    for file in files:
        # Skip drafts
        if DRAFTS_DIR in file.parents:
            logger.info(f"Skipping draft: {file}")
            continue

        # Determine category (first-level subfolder)
        if file.parent == folder:
            category = "Uncategorized"
        else:
            category = file.parent.relative_to(folder).parts[0]
        categories_seen.add(category)

        html_path = export_file(file, output_dir, as_app)
        data.append({
            "display_name": human_readable_name(file),
            "html_path": str(html_path.relative_to(output_dir)),
            "category": category
        })

    # Check for empty categories
    all_categories = {p.parts[0] for p in folder.iterdir() if p.is_dir()}
    empty_categories = all_categories - categories_seen
    for cat in empty_categories:
        logger.warning(f"No notebooks/apps found in category: {cat}")

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
    5. Exit with code 1 if no notebooks or apps found.
    """
    output_dir = Path(output_dir)
    template_file = Path(template)

    logger.info("Starting build process")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Using template: {template_file}")

    # Export notebooks and apps
    notebooks = build_data(PUBLISH_DIR / "notebooks", output_dir, as_app=False)
    apps = build_data(PUBLISH_DIR / "apps", output_dir, as_app=True)

    if not notebooks and not apps:
        logger.error("No notebooks or apps found to publish! Exiting.")
        sys.exit(1)  # Fail explicitly for GitHub Actions

    generate_index(output_dir, template_file, notebooks, apps)
    logger.info("Build completed successfully.")


if __name__ == "__main__":
    fire.Fire(main)
