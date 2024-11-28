"""Tests for the author rewriter functionality in git-surgeon."""

import io
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
def fast_export_output():
    """Sample git fast-export output for testing."""
    return io.BytesIO(b"""blob
mark :1
data 15
Initial content
reset refs/heads/main
commit refs/heads/main
mark :2
author Old User <old@example.com> 1732744600 -0800
committer Git User <git@example.com> 1732744600 -0800
data 14
Initial commit
M 100644 :1 test.txt

blob
mark :3
data 15
Updated content
commit refs/heads/main
mark :4
author Another User <another@example.com> 1732744600 -0800
committer Git User <git@example.com> 1732744600 -0800
data 14
Update content
from :2
M 100644 :3 test.txt
""")


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


def test_rewrite_single_author(repo_with_commits, fast_export_output, monkeypatch):
    """Test rewriting a single author's information using git-filter-repo."""
    rewriter = AuthorRewriter(repo_with_commits)

    # Mock subprocess.Popen and subprocess.run
    def mock_popen(*args, **_):
        mock = Mock()
        mock.stdout = fast_export_output
        mock.__enter__ = Mock(return_value=mock)
        mock.__exit__ = Mock(return_value=None)
        return mock if args[0][1] == "fast-export" else Mock(stdout=Mock())

    def mock_run(*_, **__):
        return Mock(returncode=0)

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(subprocess, "run", mock_run)

    rewriter.rewrite_authors(
        [
            AuthorMapping(
                old="Old User <old@example.com>", new="New User <new@example.com>"
            )
        ]
    )


def test_rewrite_from_file(
    repo_with_commits, fast_export_output, tmp_path, monkeypatch
):
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

    # Mock subprocess.Popen and subprocess.run
    def mock_popen(*args, **_):
        mock = Mock()
        mock.stdout = fast_export_output
        mock.__enter__ = Mock(return_value=mock)
        mock.__exit__ = Mock(return_value=None)
        return mock if args[0][1] == "fast-export" else Mock(stdout=Mock())

    def mock_run(*_, **__):
        return Mock(returncode=0)

    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    monkeypatch.setattr(subprocess, "run", mock_run)

    rewriter = AuthorRewriter(repo_with_commits)
    rewriter.rewrite_authors(mapping_file)


def test_git_filter_repo_error(repo_with_commits, fast_export_output, monkeypatch):
    """Test handling of git-filter-repo errors."""

    def mock_run(*args, **__):
        if args[0][0] == "git" and args[0][1] == "fast-import":
            raise CalledProcessError(
                returncode=1,
                cmd="git fast-import",
                stderr="Some error occurred",
                output="",
            )
        return Mock(returncode=0)

    # Create a mock that supports context management
    mock_popen = Mock()
    mock_popen.stdout = fast_export_output
    mock_popen.__enter__ = Mock(return_value=mock_popen)
    mock_popen.__exit__ = Mock(return_value=None)

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(subprocess, "Popen", Mock(return_value=mock_popen))

    rewriter = AuthorRewriter(repo_with_commits)

    with pytest.raises(
        RuntimeError, match="git-filter-repo failed: Some error occurred"
    ):
        rewriter.rewrite_authors(
            [
                AuthorMapping(
                    old="Old User <old@example.com>", new="New User <new@example.com>"
                )
            ]
        )


def test_update_committer(repo_with_commits, fast_export_output, monkeypatch):
    """Test updating committer information."""

    # Mock subprocess.Popen and subprocess.run
    def mock_popen(*args, **_):
        mock = Mock()
        mock.stdout = fast_export_output
        mock.__enter__ = Mock(return_value=mock)
        mock.__exit__ = Mock(return_value=None)
        return mock if args[0][1] == "fast-export" else Mock(stdout=Mock())

    mock_run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
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

    # Verify git fast-import was called with the right arguments
    mock_run.assert_called_with(
        ["git", "fast-import", "--force"],
        input=ANY,
        cwd=repo_with_commits.path,
        capture_output=True,
        text=True,
        check=True,
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
