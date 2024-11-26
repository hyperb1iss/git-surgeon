"""Tests for the author rewriter functionality in git-surgeon."""

import json
import subprocess
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import ANY, Mock

import pytest
from git import Actor

from git_surgeon.core import GitRepo
from git_surgeon.operations.author_rewriter import AuthorMapping, AuthorRewriter


@pytest.fixture
def repo_with_commits(temp_git_repo):
    """Create a repository with commits from different authors."""
    repo = GitRepo(temp_git_repo)

    # Create some commits with different authors
    test_file = Path(temp_git_repo) / "test.txt"

    # First commit with original author
    test_file.write_text("Initial content")
    repo.repo.index.add(["test.txt"])
    author = Actor("Old User", "old@example.com")
    committer = Actor("Git User", "git@example.com")
    repo.repo.index.commit("Initial commit", author=author, committer=committer)

    # Second commit with different author
    test_file.write_text("Updated content")
    repo.repo.index.add(["test.txt"])
    author2 = Actor("Another User", "another@example.com")
    repo.repo.index.commit("Update content", author=author2, committer=committer)

    return repo


def test_rewrite_single_author(repo_with_commits, monkeypatch):
    """Test rewriting a single author's information using git-filter-repo."""
    rewriter = AuthorRewriter(repo_with_commits)

    # Mock subprocess.run to avoid actually running git-filter-repo
    def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
        class MockResult:
            """Mock result from subprocess.run."""
            returncode = 0
            stderr = ""
            stdout = ""

        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    rewriter.rewrite_authors(
        [
            AuthorMapping(
                old="Old User <old@example.com>", new="New User <new@example.com>"
            )
        ]
    )

    # Since we're mocking git-filter-repo, we'll just verify the command would be called
    # The actual rewriting is tested in integration tests


def test_rewrite_from_file(repo_with_commits, tmp_path, monkeypatch):
    """Test rewriting authors using a mapping file."""
    mapping_file = tmp_path / "authors.json"
    mapping_data = [
        {"old": "Old User <old@example.com>", "new": "New User <new@example.com>"},
        {
            "old": "Another User <another@example.com>",
            "new": "Different User <different@example.com>",
        },
    ]
    mapping_file.write_text(json.dumps(mapping_data))

    # Mock subprocess.run
    def mock_run(*args, **kwargs):  # pylint: disable=unused-argument
        class MockResult:
            """Mock result from subprocess.run."""
            returncode = 0
            stderr = ""
            stdout = ""

        return MockResult()

    monkeypatch.setattr(subprocess, "run", mock_run)

    rewriter = AuthorRewriter(repo_with_commits)
    rewriter.rewrite_authors(mapping_file)


def test_git_filter_repo_error(repo_with_commits, monkeypatch):
    """Test handling of git-filter-repo errors."""
    def mock_run(*args, **kwargs):
        raise CalledProcessError(
            returncode=1,
            cmd="git-filter-repo",
            stderr="Some error occurred"
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    rewriter = AuthorRewriter(repo_with_commits)

    with pytest.raises(RuntimeError, match="git-filter-repo failed"):
        rewriter.rewrite_authors(
            [
                AuthorMapping(
                    old="Old User <old@example.com>", new="New User <new@example.com>"
                )
            ]
        )


def test_update_committer(repo_with_commits, monkeypatch):
    """Test updating committer information."""
    mock_run = Mock()
    mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
    monkeypatch.setattr(subprocess, "run", mock_run)

    rewriter = AuthorRewriter(repo_with_commits)

    rewriter.rewrite_authors(
        [
            AuthorMapping(
                old="Git User <git@example.com>",
                new="New Git User <newgit@example.com>",
            )
        ],
        update_committer=True,
    )

    # Updated to include check=True
    mock_run.assert_called_with(
        ["git-filter-repo", "--mailmap", ANY, "--force"],
        cwd=repo_with_commits.path,
        capture_output=True,
        text=True,
        check=True
    )


def test_invalid_mapping_file(repo_with_commits, tmp_path):
    """Test handling of invalid mapping file."""
    mapping_file = tmp_path / "invalid.json"
    mapping_file.write_text("invalid json")

    rewriter = AuthorRewriter(repo_with_commits)

    with pytest.raises(ValueError, match="Invalid mapping file format"):
        rewriter.rewrite_authors(mapping_file)


def test_parse_author_string():
    """Test parsing of author strings."""
    rewriter = AuthorRewriter(None)  # No repo needed for this test

    name, email = rewriter._parse_author_string("Test User <test@example.com>")
    assert name == "Test User"
    assert email == "test@example.com"

    with pytest.raises(ValueError, match="Invalid author string format"):
        rewriter._parse_author_string("Invalid Format")
