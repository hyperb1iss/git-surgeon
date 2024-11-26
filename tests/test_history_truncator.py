"""Tests for the history truncation functionality."""

import pytest

from git_surgeon.core import GitRepo
from git_surgeon.operations.history_truncator import HistoryTruncator


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

    truncator.keep_recent(2)
    final_count = len(list(repo.repo.iter_commits()))

    # Verify we kept exactly 2 commits
    assert final_count == 2


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


def test_truncate_before_with_squash(repo_with_history):
    """Test truncating history before a point with squash enabled."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    # Get all commits before truncation
    original_commits = list(repo.repo.iter_commits())

    # Get middle commit
    middle_commit = next(repo.repo.iter_commits(max_count=1, skip=2))
    truncator.truncate_before(middle_commit.hexsha, squash=True)

    # Get commits after truncation
    new_commits = list(repo.repo.iter_commits())

    # Verify we have fewer commits
    assert len(new_commits) < len(original_commits)

    # The first commit should be a squashed commit containing "Squashed history" in message
    first_commit = list(repo.repo.iter_commits())[-1]
    assert "Squashed history" in first_commit.message

    # Verify the file contents are preserved
    for i in range(3):  # Check first 3 files that should be in squashed commit
        assert (repo_with_history / f"file{i}.txt").read_text() == f"Content {i}"


def test_keep_recent_with_squash(repo_with_history):
    """Test keeping N most recent commits with squash enabled."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    truncator.keep_recent(2, squash=True)
    final_commits = list(repo.repo.iter_commits())

    # Should have exactly 2 commits
    assert len(final_commits) == 2

    # Verify the file contents are preserved
    for i in range(5):  # Check all files
        assert (repo_with_history / f"file{i}.txt").read_text() == f"Content {i}"


def test_truncate_before_squash_preserves_later_commits(repo_with_history):
    """Test that truncate_before with squash preserves later commit messages."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    # Get middle commit
    middle_commit = next(repo.repo.iter_commits(max_count=1, skip=2))

    # Get messages of commits after middle point for comparison
    later_commits = list(repo.repo.iter_commits(f"{middle_commit.hexsha}..HEAD"))
    later_messages = [commit.message.strip() for commit in later_commits]

    truncator.truncate_before(middle_commit.hexsha, squash=True)

    # Get new commit messages
    new_commits = list(repo.repo.iter_commits())
    new_messages = [
        commit.message.strip() for commit in new_commits[:-1]
    ]  # Exclude squashed commit

    # Verify later commit messages are preserved
    assert new_messages == later_messages


def test_invalid_keep_recent_count(repo_with_history):
    """Test that keep_recent raises error for invalid count."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    with pytest.raises(ValueError, match="Count must be positive"):
        truncator.keep_recent(0)

    with pytest.raises(ValueError, match="Count must be positive"):
        truncator.keep_recent(-1)


def test_truncate_after(repo_with_history):
    """Test truncating history after a point."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    # Get all commits before truncation
    all_commits = list(repo.repo.iter_commits())
    initial_count = len(all_commits)

    # Get middle commit
    middle_commit = next(repo.repo.iter_commits(max_count=1, skip=2))
    truncator.truncate_after(middle_commit.hexsha)

    # Get commits after truncation
    new_commits = list(repo.repo.iter_commits())

    # Verify we have fewer commits than we started with
    assert len(new_commits) < initial_count
    # Verify we have all commits up to and including the middle commit
    assert len(new_commits) == 4  # First 4 commits should remain

    # Verify the middle commit is now the latest commit
    assert new_commits[0].hexsha == middle_commit.hexsha

    # Verify the file contents are preserved up to middle commit
    for i in range(3):  # First 3 files should exist
        assert (repo_with_history / f"file{i}.txt").read_text() == f"Content {i}"

    # Later files should not exist
    for i in range(3, 5):
        assert not (repo_with_history / f"file{i}.txt").exists()


def test_truncate_after_with_squash(repo_with_history):
    """Test truncating history after a point with squash enabled."""
    repo = GitRepo(repo_with_history)
    truncator = HistoryTruncator(repo)

    # Get middle commit
    middle_commit = next(repo.repo.iter_commits(max_count=1, skip=2))
    truncator.truncate_after(middle_commit.hexsha, squash=True)

    # Get commits after truncation
    new_commits = list(repo.repo.iter_commits())

    # Should have exactly one commit after squashing
    assert len(new_commits) == 1

    # The commit should be a squashed commit containing "Squashed commits" in message
    assert "Squashed commits" in new_commits[0].message

    # Original commit hash should be mentioned in the squashed commit message
    assert middle_commit.hexsha[:8] in new_commits[0].message

    # Verify the file contents are preserved
    for i in range(3):  # First 3 files should exist
        assert (repo_with_history / f"file{i}.txt").read_text() == f"Content {i}"

    # Later files should not exist
    for i in range(3, 5):
        assert not (repo_with_history / f"file{i}.txt").exists()
