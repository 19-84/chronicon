# Test file for configuration management
from pathlib import Path

from chronicon.config import Config


def test_config_defaults():
    """Test that default configuration is correct."""
    config = Config.defaults()

    assert config.output_dir == Path("./archives")
    assert config.default_formats == ["html", "md"]
    assert config.rate_limit == 0.5
    assert config.max_workers == 8
    assert config.retry_max == 5
    assert config.timeout == 15
    assert config.exponential_backoff_base == 2
    assert not config.include_users
    assert not config.text_only


def test_config_load_nonexistent_file():
    """Test loading config when file doesn't exist returns defaults."""
    config = Config.load(Path("/nonexistent/path.toml"))

    # Should return defaults
    assert config.output_dir == Path("./archives")
    assert config.rate_limit == 0.5


def test_config_load_from_toml(tmp_path):
    """Test loading configuration from TOML file."""
    # Create a test config file
    config_file = tmp_path / "test_config.toml"
    config_file.write_text("""
[general]
output_dir = "/custom/output"
default_formats = ["html"]

[fetching]
rate_limit_seconds = 1.5
max_workers = 16
retry_max = 10
timeout = 30
exponential_backoff_base = 3

[export]
include_users = true
text_only = true
""")

    # Load config
    config = Config.load(config_file)

    # Verify parsed values
    assert config.output_dir == Path("/custom/output")
    assert config.default_formats == ["html"]
    assert config.rate_limit == 1.5
    assert config.max_workers == 16
    assert config.retry_max == 10
    assert config.timeout == 30
    assert config.exponential_backoff_base == 3
    assert config.include_users
    assert config.text_only


def test_config_load_partial_toml(tmp_path):
    """Test loading config with only some values specified."""
    # Create a partial config file
    config_file = tmp_path / "partial_config.toml"
    config_file.write_text("""
[general]
output_dir = "/tmp/archives"

[fetching]
rate_limit_seconds = 2.0
""")

    # Load config
    config = Config.load(config_file)

    # Check overridden values
    assert config.output_dir == Path("/tmp/archives")
    assert config.rate_limit == 2.0

    # Check that other values remain defaults
    assert config.max_workers == 8
    assert config.default_formats == ["html", "md"]
    assert not config.include_users


def test_config_load_malformed_toml(tmp_path):
    """Test that malformed TOML falls back to defaults."""
    # Create a malformed config file
    config_file = tmp_path / "bad_config.toml"
    config_file.write_text("""
[general
output_dir = "/broken
""")

    # Load config (should fall back to defaults without crashing)
    config = Config.load(config_file)

    # Should have defaults
    assert config.output_dir == Path("./archives")
    assert config.rate_limit == 0.5


def test_config_load_with_site_specific_settings(tmp_path):
    """
    Test config file with site-specific settings (currently not parsed
    but shouldn't break).
    """
    config_file = tmp_path / "site_config.toml"
    config_file.write_text("""
[general]
output_dir = "./archives"
default_formats = ["html", "markdown", "github"]

[fetching]
rate_limit_seconds = 0.5

[[sites]]
url = "https://meta.discourse.org"
nickname = "meta"
categories = [1, 2, 7]
rate_limit_seconds = 1.0
""")

    # Load config (sites section not used yet but shouldn't break)
    config = Config.load(config_file)

    # Check that general settings were loaded
    assert config.output_dir == Path("./archives")
    assert config.rate_limit == 0.5


def test_config_load_without_path_searches_defaults():
    """Test that loading without path checks default locations."""
    # This test verifies the fallback behavior
    # We can't easily test if it finds files in home directory
    # but we can verify it doesn't crash

    config = Config.load()  # No path provided

    # Should return defaults (no config file in test environment)
    assert config.output_dir == Path("./archives")
    assert config.rate_limit == 0.5


def test_config_all_sections(tmp_path):
    """Test loading all configuration sections."""
    config_file = tmp_path / "full_config.toml"
    config_file.write_text("""
[general]
output_dir = "/data/archives"
default_formats = ["markdown", "github"]

[fetching]
rate_limit_seconds = 0.8
max_workers = 12
retry_max = 7
timeout = 20
exponential_backoff_base = 2

[export]
include_users = false
text_only = false

[export.html]
theme_adaptation = "simplified"
enable_search = true
responsive = true

[export.markdown]
convert_html = true
preserve_formatting = true
include_metadata_header = true

[export.github]
generate_readme = true
relative_image_paths = true
gfm_syntax = true
""")

    config = Config.load(config_file)

    # Verify all general/fetching/export settings loaded
    assert config.output_dir == Path("/data/archives")
    assert config.default_formats == ["markdown", "github"]
    assert config.rate_limit == 0.8
    assert config.max_workers == 12
    assert config.retry_max == 7
    assert config.timeout == 20
    assert config.exponential_backoff_base == 2
    assert not config.include_users
    assert not config.text_only
