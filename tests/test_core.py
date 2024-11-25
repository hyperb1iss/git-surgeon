"""Tests for the core GitRepo functionality."""

from pathlib import Path

import pytest

from git_surgeon.core import GitRepo


def test_git_repo_initialization(temp_git_repo):
    """Test GitRepo class initialization."""
    repo = GitRepo(temp_git_repo)
    assert repo.path == temp_git_repo
    assert repo.current_branch in ["main", "master"]

def test_create_backup(temp_git_repo):
    """Test repository backup creation."""
    repo = GitRepo(temp_git_repo)
    backup_path = repo.create_backup()

    assert backup_path.exists()
    assert (backup_path / ".git").exists()
    assert (backup_path / "test.txt").exists()

def test_validate_state_clean_repo(temp_git_repo):
    """Test state validation with clean repository."""
    repo = GitRepo(temp_git_repo)
    assert repo.validate_state() is True

def test_validate_state_dirty_repo(temp_git_repo):
    """Test state validation with dirty repository."""
    repo = GitRepo(temp_git_repo)
    (temp_git_repo / "test.txt").write_text("Modified content")

    with pytest.raises(ValueError, match="Repository has uncommitted changes"):
        repo.validate_state()

def test_get_modified_files(temp_git_repo):
    """Test getting modified files from a commit."""
    repo = GitRepo(temp_git_repo)

    # Create a new file and commit
    new_file = temp_git_repo / "new.txt"
    new_file.write_text("New content")
    repo.repo.index.add(["new.txt"])
    commit = repo.repo.index.commit("Add new file")

    modified = repo.get_modified_files(commit)
    assert "new.txt" in modified

def test_get_file_size(temp_git_repo):
    """Test getting file size."""
    repo = GitRepo(temp_git_repo)
    test_file = temp_git_repo / "test.txt"

    # Write known content
    content = "Test content" * 100
    test_file.write_text(content)
    repo.repo.index.add(["test.txt"])
    repo.repo.index.commit("Update test file")

    size = repo.get_file_size("test.txt")
    assert size == len(content.encode())

def test_invalid_repo():
    """Test initialization with invalid repository."""
    with pytest.raises(ValueError, match="Not a git repository"):
        GitRepo(Path("/tmp/not_a_repo"))

def test_untracked_files(temp_git_repo):
    """Test validation with untracked files."""
    repo = GitRepo(temp_git_repo)

    # Create untracked file
    (temp_git_repo / "untracked.txt").write_text("Untracked content")

    with pytest.raises(ValueError, match="Repository has untracked files"):
        repo.validate_state()

def test_detached_head(temp_git_repo):
    """Test validation in detached HEAD state."""
    repo = GitRepo(temp_git_repo)

    # Create some commits and detach HEAD
    for i in range(3):
        (temp_git_repo / f"file{i}.txt").write_text(f"Content {i}")
        repo.repo.index.add([f"file{i}.txt"])
        repo.repo.index.commit(f"Commit {i}")

    repo.repo.git.checkout("HEAD^")

    with pytest.raises(ValueError, match="Repository is in detached HEAD state"):
        repo.validate_state()
