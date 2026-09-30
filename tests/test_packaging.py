# ABOUTME: Tests that HTML templates and static assets ship inside the chronicon package
# ABOUTME: Guards against wheels that install without templates/ and static/

import tomllib
from importlib.resources import files
from pathlib import Path

import pytest

from chronicon.exporters.html_static import HTMLStaticExporter
from chronicon.storage.database import ArchiveDatabase

PACKAGE_DIR = Path(str(files("chronicon")))
REPO_ROOT = Path(__file__).parent.parent


def test_templates_and_static_live_inside_package():
    """Templates and static assets must live under the package to ship in the wheel."""
    assert (PACKAGE_DIR / "templates" / "base.html").is_file()
    assert (PACKAGE_DIR / "templates" / "topic.html").is_file()
    assert (PACKAGE_DIR / "static" / "css").is_dir()
    assert (PACKAGE_DIR / "static" / "js").is_dir()


def test_html_exporter_uses_packaged_templates_and_static(tmp_path):
    """Default template lookup and copied assets come from the package directory."""
    db = ArchiveDatabase(tmp_path / "test.db")
    output_dir = tmp_path / "out"
    exporter = HTMLStaticExporter(db, output_dir, search_backend="static")

    assert exporter.template_dir == PACKAGE_DIR / "templates"

    exporter.copy_assets()
    assert (output_dir / "assets" / "css" / "archive.css").is_file()
    assert any((output_dir / "assets" / "fonts").iterdir())
    assert (output_dir / "assets" / "js" / "search.js").is_file()
    db.close()


def test_search_html_uses_packaged_templates(monkeypatch):
    """The FTS search pages load templates from the package directory."""
    pytest.importorskip("fastapi")
    # Import the app first; importing the route module alone is circular
    import chronicon.api.app  # noqa: F401
    from chronicon.api.routes import search_html

    monkeypatch.setattr(search_html, "_template_env", None)
    env = search_html.get_template_env()

    assert env.get_template("search-results.html").filename == str(
        PACKAGE_DIR / "templates" / "search-results.html"
    )


def test_pyproject_uses_hatch_build_config():
    """Hatch ignores [tool.hatchling]; build settings must live under [tool.hatch]."""
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)

    assert "hatchling" not in pyproject["tool"]
    wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == ["src/chronicon"]
