"""Tests for configuration settings."""
# ruff: noqa: E1101
# pylint: disable=no-member

from pathlib import Path

import pytest
from pydantic import ValidationError

from git_surgeon.config import Settings


def test_default_settings():
    """Test default settings values."""
    settings = Settings()
    assert settings.create_backup is True
    assert settings.backup_dir is None
    assert settings.force is False
    assert settings.dry_run is False
    assert settings.preserve_recent is False
    assert settings.selected_branches == []
    assert settings.large_file_threshold == 50 * 1024 * 1024  # 50MB
    assert "password" in settings.sensitive_patterns
    assert "secret" in settings.sensitive_patterns
    assert "key" in settings.sensitive_patterns
    assert "token" in settings.sensitive_patterns
    assert "credential" in settings.sensitive_patterns


def test_custom_settings():
    """Test custom settings values."""
    settings = Settings(
        create_backup=False,
        backup_dir=Path("/tmp/backup"),
        force=True,
        dry_run=True,
        preserve_recent=True,
        selected_branches=["main", "dev"],
        large_file_threshold=100 * 1024 * 1024,  # 100MB
        sensitive_patterns=["custom_pattern"],
    )
    assert settings.create_backup is False
    assert settings.backup_dir == Path("/tmp/backup")
    assert settings.force is True
    assert settings.dry_run is True
    assert settings.preserve_recent is True
    assert settings.selected_branches == ["main", "dev"]
    assert settings.large_file_threshold == 100 * 1024 * 1024
    assert settings.sensitive_patterns == ["custom_pattern"]


def test_settings_validation():
    """Test settings validation."""
    # Test that large_file_threshold must be positive
    with pytest.raises(ValidationError) as exc_info:
        Settings(large_file_threshold=0)
    assert "Input should be greater than 0" in str(exc_info.value)

    # Test that backup_dir must be a valid path
    with pytest.raises(ValidationError) as exc_info:
        Settings(backup_dir=123)  # type: ignore
    assert "Input is not a valid path" in str(exc_info.value)


def test_settings_type_conversion():
    """Test automatic type conversion of settings."""
    # Test integer conversion
    settings = Settings(large_file_threshold="52428800")
    assert isinstance(settings.large_file_threshold, int)
    assert settings.large_file_threshold == 52428800

    # Test path conversion
    settings = Settings(backup_dir=str(Path("/tmp/backup")))
    assert isinstance(settings.backup_dir, Path)

    # Test list conversion
    settings = Settings(selected_branches=["main"])
    assert isinstance(settings.selected_branches, list)
    assert settings.selected_branches == ["main"]


def test_settings_modification():
    """Test that settings can be modified after creation."""
    settings = Settings()

    # Test modifying simple values
    settings.force = True
    assert settings.force is True

    # Test modifying lists
    settings.selected_branches.append("main")
    assert "main" in settings.selected_branches

    # Test modifying paths
    settings.backup_dir = Path("/new/path")
    assert settings.backup_dir == Path("/new/path")
