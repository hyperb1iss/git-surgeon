"""Tests for file purging functionality."""

import pytest
from git import Repo

from git_surgeon.core import GitRepo
from git_surgeon.operations.file_purger import FilePurger


@pytest.fixture
def repo_with_sensitive_files(temp_git_repo):
    """Create a repository with some sensitive files for testing."""
    repo_path = temp_git_repo

    # Create .env files in different locations
    (repo_path / ".env").write_text("SECRET=123")

    # Create config directory and .env file
    config_dir = repo_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / ".env").write_text("API_KEY=456")

    # Add and commit the files
    repo = Repo(repo_path)
    repo.index.add([".env", "config/.env"])
    repo.index.commit("Add sensitive files")

    return repo_path


def test_find_matches(repo_with_sensitive_files):
    """Test finding files matching pattern."""
    repo = GitRepo(repo_with_sensitive_files)
    purger = FilePurger(repo, "**/.env")

    matches = purger.find_matches()
    assert len(matches) == 2
    assert any(m.name == ".env" for m in matches)


def test_calculate_size_impact(repo_with_sensitive_files):
    """Test calculation of size impact."""
    repo = GitRepo(repo_with_sensitive_files)
    purger = FilePurger(repo, "**/.env")

    size = purger.calculate_size_impact()
    assert size > 0


def test_execute_purge(repo_with_sensitive_files):
    """Test actual file purge operation."""
    repo = GitRepo(repo_with_sensitive_files)
    purger = FilePurger(repo, "**/.env")

    purger.execute()

    # Verify files are removed from history
    assert not (repo_with_sensitive_files / ".env").exists()
    assert not (repo_with_sensitive_files / "config" / ".env").exists()
