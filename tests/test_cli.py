"""Tests for the command-line interface."""
# pylint: disable=unused-argument

from unittest.mock import ANY, Mock, patch

import pytest
from typer.testing import CliRunner

from git_surgeon.cli import app
from git_surgeon.core import GitRepo

runner = CliRunner()


@pytest.fixture
def mock_repo():
    """Provide a mock GitRepo instance for testing."""
    with patch("git_surgeon.cli.GitRepo") as mock:
        repo = Mock(spec=GitRepo)
        mock.return_value = repo
        repo.validate_state.return_value = None
        repo.create_backup.return_value = None
        yield repo


@pytest.fixture
def mock_file_purger():
    """Provide a mock FilePurger instance for testing."""
    with patch("git_surgeon.cli.FilePurger") as mock:
        purger = Mock()
        mock.return_value = purger
        # Mock required methods
        purger.find_matches.return_value = ["file1", "file2"]
        purger.calculate_size_impact.return_value = 1024
        purger.affected_commits = ["commit1", "commit2"]
        purger.run.return_value = None
        purger.execute.return_value = None
        yield purger


@pytest.fixture
def mock_history_truncator():
    """Provide a mock HistoryTruncator instance for testing."""
    with patch("git_surgeon.cli.HistoryTruncator") as mock:
        truncator = Mock()
        mock.return_value = truncator
        truncator.run.return_value = None
        truncator.execute.return_value = None
        # Mock required methods
        truncator.truncate_before.return_value = None
        truncator.truncate_after.return_value = None
        truncator.keep_recent.return_value = None
        yield truncator


@pytest.fixture
def mock_repo_cleanup():
    """Provide a mock RepoCleanup instance for testing."""
    with patch("git_surgeon.cli.RepoCleanup") as mock:
        cleanup = Mock()
        mock.return_value = cleanup
        cleanup.run.return_value = None
        cleanup.execute.return_value = None
        # Mock required methods
        cleanup.clean_large_files.return_value = None
        cleanup.clean_sensitive_data.return_value = None
        yield cleanup


@pytest.fixture
def mock_author_rewriter():
    """Provide a mock AuthorRewriter instance for testing."""
    with patch("git_surgeon.cli.AuthorRewriter") as mock:
        rewriter = Mock()
        mock.return_value = rewriter
        rewriter.run.return_value = None
        rewriter.execute.return_value = None
        # Mock required methods
        mock.load_mappings = Mock(
            return_value=[{"old": "old@email.com", "new": "new@email.com"}]
        )
        rewriter.rewrite_authors.return_value = None
        yield mock


@pytest.fixture
def mock_typer_confirm():
    """Provide a mock typer.confirm function that always returns True."""
    with patch("typer.confirm") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_console():
    """Provide a mock console instance for testing."""
    with patch("git_surgeon.cli.console") as mock:
        mock.print.return_value = None
        mock.status.return_value.__enter__.return_value = Mock()
        yield mock


def test_remove_command(mock_repo, mock_file_purger, mock_typer_confirm, mock_console):
    """Test the remove command with basic arguments."""
    result = runner.invoke(app, ["remove", "**/.env"])
    assert result.exit_code == 0
    mock_file_purger.execute.assert_called_once()


def test_remove_command_with_options(
    mock_repo, mock_file_purger, mock_typer_confirm, mock_console
):
    """Test the remove command with all options."""
    result = runner.invoke(
        app,
        [
            "remove",
            "**/.env",
            "--dry-run",
            "--no-backup",
            "--branches",
            "main,dev",
            "--preserve-recent",
        ],
    )
    assert result.exit_code == 0


def test_truncate_command(
    mock_repo, mock_history_truncator, mock_typer_confirm, mock_console
):
    """Test the truncate command with basic arguments."""
    result = runner.invoke(app, ["truncate", "--before", "2023-01-01"])
    assert result.exit_code == 0
    mock_history_truncator.truncate_before.assert_called_once_with(
        "2023-01-01", squash=False
    )


def test_truncate_command_with_options(
    mock_repo, mock_history_truncator, mock_typer_confirm, mock_console
):
    """Test the truncate command with all options."""
    result = runner.invoke(
        app,
        [
            "truncate",
            "--before",
            "2023-01-01",
            "--after",
            "2022-01-01",
            "--keep-recent",
            "5",
            "--squash",
            "--dry-run",
            "--no-backup",
        ],
    )
    assert result.exit_code == 0


def test_clean_command(mock_repo, mock_repo_cleanup, mock_typer_confirm, mock_console):
    """Test the clean command with basic arguments."""
    result = runner.invoke(app, ["clean", "--size-threshold", "1MB"])
    assert result.exit_code == 0
    mock_repo_cleanup.clean_large_files.assert_called_once_with("1MB", patterns=None)


def test_clean_command_with_options(
    mock_repo, mock_repo_cleanup, mock_typer_confirm, mock_console
):
    """Test the clean command with all options."""
    result = runner.invoke(
        app,
        [
            "clean",
            "--size-threshold",
            "1MB",
            "--patterns",
            "*.bin,*.exe",
            "--sensitive-data",
            "--dry-run",
            "--no-backup",
        ],
    )
    assert result.exit_code == 0


def test_rewrite_authors_command(
    mock_repo, mock_author_rewriter, mock_typer_confirm, mock_console
):
    """Test the rewrite-authors command with basic arguments."""
    result = runner.invoke(
        app,
        [
            "rewrite-authors",
            "--old",
            "old@email.com",
            "--new",
            "new@email.com",
        ],
    )
    assert result.exit_code == 0
    mock_author_rewriter.assert_called_once()
    mock_author_rewriter.return_value.rewrite_authors.assert_called_once()


def test_rewrite_authors_with_options(
    mock_repo, mock_author_rewriter, mock_typer_confirm, mock_console
):
    """Test the rewrite-authors command with all options."""
    result = runner.invoke(
        app,
        [
            "rewrite-authors",
            "--map",
            "authors.json",
            "--update-committer",
            "--dry-run",
            "--no-backup",
        ],
    )
    assert result.exit_code == 0
    mock_author_rewriter.assert_called_once()
    mock_author_rewriter.load_mappings.assert_called_once_with(
        ANY
    )  # Accept any Path object


def test_invalid_repo_path(mock_repo):
    """Test behavior with an invalid repository path."""
    mock_repo.validate_state.side_effect = ValueError("Not a git repository")
    result = runner.invoke(app, ["remove", "**/.env", "--repo-path", "/invalid/path"])
    assert result.exit_code == 1
    assert "Not a git repository" in result.stdout


def test_error_during_operation(
    mock_repo, mock_file_purger, mock_typer_confirm, mock_console
):
    """Test error handling during operation execution."""
    error_msg = "Operation failed"
    mock_repo.validate_state.side_effect = Exception(error_msg)
    result = runner.invoke(app, ["remove", "**/.env"])
    assert result.exit_code == 1
    mock_console.print.assert_any_call(f"[red]Error:[/red] {error_msg}")
