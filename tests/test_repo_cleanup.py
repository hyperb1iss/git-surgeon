"""Tests for repository cleanup operations."""

from pathlib import Path

import git
import pytest

from git_surgeon.core import GitRepo
from git_surgeon.operations.repo_cleanup import RepoCleanup


@pytest.fixture
def repo_with_large_files(temp_git_repo):
    """Create a repository with some large files."""
    repo_path = temp_git_repo
    repo = GitRepo(repo_path)

    # Create a large file
    large_file = repo_path / "large.bin"
    large_file.write_bytes(b"0" * (10 * 1024 * 1024))  # 10MB file

    repo.repo.index.add(["large.bin"])
    repo.repo.index.commit("Add large file")

    return repo_path


def test_parse_size():
    """Test size parsing."""
    repo = GitRepo(Path())  # Path doesn't matter for this test
    cleanup = RepoCleanup(repo)

    assert cleanup._parse_size("10B") == 10
    assert cleanup._parse_size("1KB") == 1024
    assert cleanup._parse_size("1MB") == 1024 * 1024
    assert cleanup._parse_size("1GB") == 1024 * 1024 * 1024

    with pytest.raises(ValueError):
        cleanup._parse_size("invalid")


def test_clean_large_files(repo_with_large_files):
    """Test cleaning large files."""
    repo = GitRepo(repo_with_large_files)
    cleanup = RepoCleanup(repo)

    # Clean files larger than 5MB
    cleanup.clean_large_files("5MB")

    # Verify large file is removed from working directory
    assert not (repo_with_large_files / "large.bin").exists()

    # Verify large file is removed from git history
    try:
        repo.repo.git.rev_list("--objects", "--all", "large.bin")
        raise AssertionError("large.bin should not be in git history")
    except git.exc.GitCommandError:
        # Expected - file should not be found
        pass
