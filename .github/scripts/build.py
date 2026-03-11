"""
Build script for exporting marimo notebooks to WebAssembly HTML.

This script performs the following steps:

1. Scans the `publish/` directory for notebooks and apps
2. Reads optional metadata from each notebook
3. Skips notebooks marked as drafts
4. Exports notebooks to HTML WebAssembly using marimo
5. Generates an index.html page using Jinja templates

Key features:
- Supports nested folders
- Supports draft mode
- Supports metadata titles
- Keeps templates simple

Compatible with:
marimo WebAssembly export
GitHub Pages deployment
"""

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "jinja2",
#     "fire",
#     "loguru"
# ]
# ///

import subprocess
from pathlib import Path
from typing import List, Dict

import jinja2
import fire
from loguru import logger


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

# Only notebooks inside this directory will be published
PUBLISH_DIR = Path("publish")

# Output directory for GitHub Pages
OUTPUT_DIR = Path("_site")

# Template used to render homepage
DEFAULT_TEMPLATE = Path("templates/tailwind.html.j2")


# -------------------------------------------------------------------
# Metadata utilities
# -------------------------------------------------------------------

def read_metadata(file: Path) -> Dict:
    """
    Read metadata from the top of a notebook file.

    Supported metadata:

    # title: Custom Notebook Title
    # draft: true

    Only the first few lines are inspected to keep parsing fast.
    """

    metadata = {
        "title": file.stem.replace("_", " ").title(),
        "draft": False
    }

    try:
        with open(file) as f:
            for _ in range(5):
                line = f.readline().strip().lower()

                if line.startswith("# title:"):
                    metadata["title"] = line.split(":", 1)[1].strip()

                if line.startswith("# draft:"):
                    metadata["draft"] = "true" in line

    except Exception as e:
        logger.warning(f"Could not read metadata from {file}: {e}")

    return metadata


# -------------------------------------------------------------------
# Export notebooks using marimo
# -------------------------------------------------------------------

def export_notebook(file: Path, as_app: bool) -> Path:
    """
    Export a single notebook using marimo export.

    Parameters
    ----------
    file : Path
        Notebook file (.py)

    as_app : bool
        True  -> export as application (run mode)
        False -> export as notebook (edit mode)
    """

    output_file = OUTPUT_DIR / file.relative_to(PUBLISH_DIR).with_suffix(".html")

    # ensure directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "uvx",
        "marimo",
        "export",
        "html-wasm",
        "--sandbox"
    ]

    if as_app:
        cmd += ["--mode", "run", "--no-show-code"]
    else:
        cmd += ["--mode", "edit"]

    cmd += [str(file), "-o", str(output_file)]

    logger.info(f"Exporting {file}")

    subprocess.run(cmd, check=True)

    return output_file.relative_to(OUTPUT_DIR)


# -------------------------------------------------------------------
# Scan publish directory
# -------------------------------------------------------------------

def collect_content():
    """
    Discover notebooks and apps in publish directory.

    Returns
    -------
    notebooks : List[dict]
    apps : List[dict]
    """

    notebooks = []
    apps = []

    for file in PUBLISH_DIR.rglob("*.py"):

        metadata = read_metadata(file)

        # skip drafts
        if metadata["draft"]:
            logger.info(f"Skipping draft: {file}")
            continue

        is_app = "apps" in file.parts

        html_path = export_notebook(file, is_app)

        entry = {
            "display_name": metadata["title"],
            "html_path": str(html_path)
        }

        if is_app:
            apps.append(entry)
        else:
            notebooks.append(entry)

    return notebooks, apps


# -------------------------------------------------------------------
# Generate index page
# -------------------------------------------------------------------

def generate_index(notebooks, apps, template_file):
    """
    Render homepage using Jinja template.
    """

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_file.parent),
        autoescape=True
    )

    template = env.get_template(template_file.name)

    OUTPUT_DIR.mkdir(exist_ok=True)

    html = template.render(
        notebooks=notebooks,
        apps=apps
    )

    with open(OUTPUT_DIR / "index.html", "w") as f:
        f.write(html)

    logger.info("Generated index.html")


# -------------------------------------------------------------------
# Main build function
# -------------------------------------------------------------------

def main(
    template: str = str(DEFAULT_TEMPLATE)
):
    """
    Run the full build process.
    """

    logger.info("Starting marimo build")

    template_file = Path(template)

    notebooks, apps = collect_content()

    generate_index(notebooks, apps, template_file)

    logger.info("Build completed")


if __name__ == "__main__":
    fire.Fire(main)
