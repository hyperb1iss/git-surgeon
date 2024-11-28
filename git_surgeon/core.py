"""Core functionality for git-surgeon operations."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import git
from git import Commit
from rich.console import Console

console = Console()


class GitRepo:
    """Wrapper around GitPython repository with additional safety features."""

    def __init__(self, path: Path):
        """Initialize GitRepo with path to repository.

        Args:
            path: Path to git repository

        Raises:
            ValueError: If path is not a git repository
        """
        self.path = path
        try:
            if not path.exists():
                raise ValueError(f"Not a git repository: {path}")
            self.repo = git.Repo(path)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            raise ValueError(f"Not a git repository: {path}") from e

    def create_backup(self) -> Path:
        """Create a backup of the repository.

        Returns:
            Path to backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.path.parent / f"{self.path.name}_backup_{timestamp}"

        console.print(f"Creating backup at: {backup_path}")
        shutil.copytree(self.path, backup_path)

        return backup_path

    def validate_state(self) -> bool:
        """Check if repository is in a valid state for operations.

        Returns:
            True if repository is in valid state

        Raises:
            ValueError: If repository has uncommitted changes
            ValueError: If repository has untracked files
        """
        if self.repo.is_dirty():
            raise ValueError("Repository has uncommitted changes")

        if self.repo.untracked_files:
            raise ValueError("Repository has untracked files")

        # Check if we're in detached HEAD state
        try:
            _ = self.repo.active_branch
        except TypeError as err:
            raise ValueError("Repository is in detached HEAD state") from err

        return True

    @property
    def current_branch(self) -> str:
        """Get current branch name."""
        return self.repo.active_branch.name

    def get_all_commits(self) -> list[Commit]:
        """Get all commits in repository."""
        return list(self.repo.iter_commits("--all"))

    def get_modified_files(self, commit: git.Commit) -> set[str]:
        """Get all files modified in a commit."""
        return (
            {item.a_path for item in commit.diff(commit.parents[0])}
            if commit.parents
            else set()
        )

    def get_file_size(self, path: str, commit: Optional[git.Commit] = None) -> int:
        """Get size of file at specific commit.

        Args:
            path: Path to file relative to repository root
            commit: Commit to check (defaults to HEAD)

        Returns:
            Size of file in bytes
        """
        commit = commit or self.repo.head.commit
        try:
            blob = commit.tree / path
            return blob.size
        except KeyError:
            return 0

    def get_branches(self) -> list[str]:
        """Get list of all branch names."""
        return [b.name for b in self.repo.heads]

    def has_remote(self) -> bool:
        """Check if repository has any remotes configured."""
        return len(self.repo.remotes) > 0

    def check_remote_differences(self) -> bool:
        """Check if there are any differences with remote.

        Returns:
            True if there are differences with remote
        """
        if not self.has_remote():
            return False

        # Fetch from remote to ensure we have latest state
        self.repo.remotes.origin.fetch()

        # Check if current branch has remote counterpart
        try:
            remote_branch = self.repo.active_branch.tracking_branch()
            if remote_branch is None:
                return False

            # Check for differences
            return bool(list(self.repo.iter_commits(f"{remote_branch}..HEAD")))
        except git.GitCommandError:
            return False

    def gc(self) -> None:
        """Run git garbage collection."""
        self.repo.git.gc("--aggressive", "--prune=now")
