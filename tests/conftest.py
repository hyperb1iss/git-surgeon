"""Test fixtures and configuration for git-surgeon tests."""

import pytest
from git import Repo


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path)

    # Configure git locally for this repo only
    with repo.config_writer() as git_config:
        git_config.set_value('user', 'name', 'Test User')
        git_config.set_value('user', 'email', 'test@example.com')

    # Create some test files and commits
    test_file = repo_path / "test.txt"
    test_file.write_text("Initial content")

    repo.index.add(["test.txt"])
    repo.index.commit("Initial commit")

    return repo_path
