"""Tests for the history truncation functionality."""

import pytest
from git_nuke.core import GitRepo
from git_nuke.operations.history_truncator import HistoryTruncator


@pytest.fixture
def repo_with_history(temp_git_repo):
    """Create a repository with multiple commits."""
    repo_path = temp_git_repo
    repo = GitRepo(repo_path)

    # Create several commits
    for i in range(5):
        (repo_path / f"file{i}.txt").write_text(f"Content {i}")
        repo.repo.index.add([f"file{i}.txt"])
        repo.repo.index.commit(f"Commit {i}")

    return repo_path

def test_keep_recent(repo_with_history):
    """Test keeping N most recent commits."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    initial_count = len(list(repo.repo.iter_commits()))
    truncator.keep_recent(2)
    final_count = len(list(repo.repo.iter_commits()))

    assert final_count == 2
    assert initial_count == 6  # Including initial commit

def test_truncate_before(repo_with_history):
    """Test truncating history before a point."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    # Get all commits before truncation
    original_commits = list(repo.repo.iter_commits())

    # Get middle commit
    middle_commit = next(repo.repo.iter_commits(max_count=1, skip=2))
    truncator.truncate_before(middle_commit.hexsha)

    # Get commits after truncation
    new_commits = list(repo.repo.iter_commits())

    # Verify we have fewer commits
    assert len(new_commits) < len(original_commits)

    # Verify the middle commit is still in history
    commit_hashes = [c.hexsha for c in new_commits]
    assert middle_commit.hexsha in commit_hashes
