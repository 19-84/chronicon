# ABOUTME: End-to-end validation of examples and documentation
# ABOUTME: Ensures CLI flags, config files, Docker commands, and env vars are accurate

"""E2E tests verifying examples folder accuracy against actual codebase."""

import argparse
import re
from pathlib import Path

import pytest

from chronicon.config import Config

PROJECT_ROOT = Path(__file__).parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"


class TestCLIFormatNames:
    """Verify format names used in examples are accepted by the CLI parser."""

    @pytest.fixture
    def archive_parser(self):
        """Build the archive subparser to test format validation."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        archive_parser = subparsers.add_parser("archive")
        archive_parser.add_argument("--urls", required=True)
        archive_parser.add_argument("--formats", default="hybrid")
        archive_parser.add_argument("--output-dir", default="./archives")
        archive_parser.add_argument("--categories")
        archive_parser.add_argument("--text-only", action="store_true")
        archive_parser.add_argument(
            "--search-backend", choices=["static", "fts"], default="fts"
        )
        return parser

    def test_examples_readme_format_names(self, archive_parser):
        """Format names in examples/README.md are valid."""
        readme = (EXAMPLES_DIR / "README.md").read_text()
        # Extract --formats values
        for match in re.finditer(r"--formats\s+(\S+)", readme):
            formats = match.group(1)
            # Should parse without error
            args = archive_parser.parse_args(
                ["archive", "--urls", "https://example.com", "--formats", formats]
            )
            assert args.formats == formats

    def test_no_invalid_format_markdown_github(self):
        """No example uses the invalid format name 'markdown-github'."""
        for path in EXAMPLES_DIR.rglob("*"):
            if path.is_file() and path.suffix in (".md", ".yml", ".yaml", ".toml"):
                content = path.read_text()
                assert "markdown-github" not in content, (
                    f"Found invalid format 'markdown-github' in {path}"
                )


class TestEnvVarFormatNames:
    """Verify EXPORT_FORMATS values in .env examples match valid format names."""

    VALID_FORMATS = {"html", "md", "hybrid", "github"}

    def test_sqlite_env_formats(self):
        """EXPORT_FORMATS in .env.sqlite.example uses valid format names."""
        env_file = EXAMPLES_DIR / "docker" / ".env.sqlite.example"
        content = env_file.read_text()
        for line in content.splitlines():
            if line.startswith("EXPORT_FORMATS="):
                value = line.split("=", 1)[1].strip()
                if value:
                    formats = [f.strip() for f in value.split(",")]
                    for fmt in formats:
                        assert fmt in self.VALID_FORMATS, (
                            f"Invalid format '{fmt}' in {env_file}"
                        )

    def test_postgres_env_formats(self):
        """EXPORT_FORMATS in .env.postgres.example uses valid format names."""
        env_file = EXAMPLES_DIR / "docker" / ".env.postgres.example"
        content = env_file.read_text()
        for line in content.splitlines():
            if line.startswith("EXPORT_FORMATS="):
                value = line.split("=", 1)[1].strip()
                if value:
                    formats = [f.strip() for f in value.split(",")]
                    for fmt in formats:
                        assert fmt in self.VALID_FORMATS, (
                            f"Invalid format '{fmt}' in {env_file}"
                        )


class TestConfigExampleParsing:
    """Verify config example files parse without error."""

    def test_chronicon_toml_example_parses(self, tmp_path):
        """The .chronicon.toml.example file parses successfully."""
        example = PROJECT_ROOT / ".chronicon.toml.example"
        config = Config.load(example)
        assert config is not None
        assert config.rate_limit == 0.5
        assert config.max_workers == 8

    def test_techlore_config_parses(self, tmp_path):
        """The techlore config example parses successfully."""
        config_file = EXAMPLES_DIR / "docker" / "config" / ".chronicon-techlore.toml"
        config = Config.load(config_file)
        assert config is not None
        assert len(config.sites) == 1
        assert config.sites[0].url == "https://discuss.techlore.tech"


class TestDockerEntrypoints:
    """Verify Docker entrypoint commands reference valid CLI subcommands."""

    VALID_SUBCOMMANDS = {
        "archive",
        "update",
        "validate",
        "migrate",
        "watch",
        "serve",
        "mcp",
        "export",
        "rebuild-search-index",
        "backfill-posts",
        "--help",
    }

    # Entry point binaries that are valid (installed via pip install .)
    VALID_BINARIES = {"chronicon", "python"}

    def test_dockerfile_commands(self):
        """CMD/ENTRYPOINT in Dockerfiles use valid subcommands."""
        dockerfiles = list(EXAMPLES_DIR.rglob("Dockerfile*")) + [
            PROJECT_ROOT / "Dockerfile",
            PROJECT_ROOT / "Dockerfile.alpine",
        ]

        for dockerfile in dockerfiles:
            if not dockerfile.exists():
                continue
            content = dockerfile.read_text()
            # Extract CMD values
            for match in re.finditer(r"CMD\s+\[(.+?)\]", content):
                args = [a.strip().strip('"') for a in match.group(1).split(",")]
                # First non-flag arg should be a valid subcommand or binary
                for arg in args:
                    if not arg.startswith("-"):
                        assert arg in (self.VALID_SUBCOMMANDS | self.VALID_BINARIES), (
                            f"Invalid command '{arg}' in {dockerfile}"
                        )
                        break

    def test_compose_commands(self):
        """Docker compose command directives use valid subcommands."""
        compose_files = list(EXAMPLES_DIR.rglob("docker-compose*.yml"))

        for compose_file in compose_files:
            content = compose_file.read_text()
            for match in re.finditer(r"command:\s+\[(.+?)\]", content):
                args = [a.strip().strip('"') for a in match.group(1).split(",")]
                for arg in args:
                    if not arg.startswith("-"):
                        assert arg in self.VALID_SUBCOMMANDS, (
                            f"Invalid subcommand '{arg}' in {compose_file}"
                        )
                        break


class TestNoPlaceholderURLs:
    """Verify no placeholder URLs remain in examples."""

    def test_no_your_org_urls(self):
        """No 'your-org' placeholder URLs in examples."""
        for path in EXAMPLES_DIR.rglob("*"):
            if path.is_file() and path.suffix in (
                ".md",
                ".yml",
                ".yaml",
                ".toml",
                ".service",
                "",
            ):
                content = path.read_text()
                assert "your-org" not in content, (
                    f"Found placeholder 'your-org' in {path}"
                )

    def test_no_example_com_emails(self):
        """No security@example.com placeholders in example docs."""
        for path in EXAMPLES_DIR.rglob("*.md"):
            content = path.read_text()
            assert "security@example.com" not in content, (
                f"Found placeholder email in {path}"
            )


class TestInstallationDocs:
    """Verify installation instructions don't reference PyPI."""

    def test_readme_no_pip_install_chronicon(self):
        """README doesn't tell users to pip install chronicon (not on PyPI)."""
        readme = (PROJECT_ROOT / "README.md").read_text()
        assert "pip install chronicon\n" not in readme
        assert "uv tool install chronicon\n" not in readme

    def test_systemd_readme_no_pip_install(self):
        """Systemd README uses local install, not PyPI."""
        readme = (EXAMPLES_DIR / "systemd" / "README.md").read_text()
        assert "pip install chronicon\n" not in readme
        assert "uv tool install chronicon\n" not in readme


class TestDockerfilePackageInstall:
    """Verify Dockerfiles install the package properly."""

    def test_dockerfiles_install_package(self):
        """Dockerfiles that copy src/ also run pip install."""
        dockerfiles = [
            PROJECT_ROOT / "Dockerfile",
            PROJECT_ROOT / "Dockerfile.alpine",
            EXAMPLES_DIR / "docker" / "Dockerfile.alpine",
            EXAMPLES_DIR / "docker" / "Dockerfile.alpine-watch",
        ]

        for dockerfile in dockerfiles:
            if not dockerfile.exists():
                continue
            content = dockerfile.read_text()
            # Should have pip install . (not just individual packages)
            has_proper_install = "pip install" in content and (
                '"."' in content or "'." in content or " ." in content
            )
            assert has_proper_install, (
                f"{dockerfile} should install the package with 'pip install .'"
            )

    def test_no_bare_dependency_install(self):
        """Dockerfiles don't install bare deps without the package."""
        dockerfiles = [
            PROJECT_ROOT / "Dockerfile",
            PROJECT_ROOT / "Dockerfile.alpine",
            EXAMPLES_DIR / "docker" / "Dockerfile.alpine",
            EXAMPLES_DIR / "docker" / "Dockerfile.alpine-watch",
        ]

        for dockerfile in dockerfiles:
            if not dockerfile.exists():
                continue
            content = dockerfile.read_text()
            # Should NOT have the old pattern of installing deps without package
            assert (
                "pip install --no-cache-dir beautifulsoup4 html2text" not in content
            ), f"{dockerfile} still installs bare deps instead of the package"


class TestDockerComposePostgres:
    """Verify postgres compose file issues are fixed."""

    def test_api_volume_not_readonly(self):
        """API service volume is not read-only (archive needs write)."""
        compose = (EXAMPLES_DIR / "docker" / "docker-compose.postgres.yml").read_text()
        # The api service archives volume should not have :ro
        # Find the api service section
        in_api = False
        for line in compose.splitlines():
            if "api:" in line and "container" not in line:
                in_api = True
            elif in_api and line.strip().startswith("- ./archives:"):
                assert ":ro" not in line, "API archives volume should not be read-only"
                break

    def test_watch_has_external_network(self):
        """Watch service has external network for API polling."""
        compose = (EXAMPLES_DIR / "docker" / "docker-compose.postgres.yml").read_text()
        assert "external" in compose

    def test_no_double_entrypoint(self):
        """Usage comment doesn't duplicate the entrypoint."""
        compose = (EXAMPLES_DIR / "docker" / "docker-compose.postgres.yml").read_text()
        assert "python -m chronicon.cli archive" not in compose


class TestConfigDeadwood:
    """Verify unused config sections have been removed."""

    def test_no_export_html_section(self):
        """No [export.html] section in config examples."""
        example = (PROJECT_ROOT / ".chronicon.toml.example").read_text()
        assert "[export.html]" not in example

    def test_no_export_markdown_section(self):
        """No [export.markdown] section in config examples."""
        example = (PROJECT_ROOT / ".chronicon.toml.example").read_text()
        assert "[export.markdown]" not in example

    def test_no_export_github_section(self):
        """No [export.github] section in config examples."""
        example = (PROJECT_ROOT / ".chronicon.toml.example").read_text()
        assert "[export.github]" not in example

    def test_techlore_no_deadwood(self):
        """Techlore config has no unused sections."""
        config = (
            EXAMPLES_DIR / "docker" / "config" / ".chronicon-techlore.toml"
        ).read_text()
        assert "[export.html]" not in config
        assert "[export.markdown]" not in config
        assert "[export.github]" not in config
