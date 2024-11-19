"""History truncation operations for managing git repository history."""

from contextlib import suppress
from datetime import datetime
from typing import Union

import git

from git_nuke.core import GitRepo


class HistoryTruncator:
    """Handles truncation of repository history."""

    def __init__(self, repo: GitRepo):
        self.repo = repo

    def _parse_point(self, point: Union[str, datetime]) -> str:
        """Convert a point specification to a commit hash."""
        if isinstance(point, datetime):
            # Find the most recent commit before this date
            commits = self.repo.repo.iter_commits(
                until=point.isoformat()
            )
            try:
                return next(commits).hexsha
            except StopIteration as err:
                raise ValueError(f"No commits found before {point}") from err

        # Try to resolve as commit hash or ref
        try:
            return self.repo.repo.rev_parse(point).hexsha
        except Exception as err:
            raise ValueError(f"Invalid commit specification: {point}") from err

    def _get_commit_count(self) -> int:
        """Get total number of commits in repository."""
        return len(list(self.repo.repo.iter_commits()))

    def truncate_before(
        self,
        point: Union[str, datetime],
        squash: bool = False  # TODO: Implement squash functionality
    ) -> None:
        """Truncate history before specified point.
        
        Args:
            point: Commit hash, ref, or datetime to truncate before
            squash: If True, squashes remaining commits into one. Currently not implemented.
        """
        commit_hash = self._parse_point(point)
        branch_name = self.repo.current_branch

        if squash:
            # Create a new orphan branch with current state
            self.repo.repo.git.checkout('--orphan', 'temp_branch')
            self.repo.repo.git.add('.')
            self.repo.repo.git.commit('-m', f'Squashed history before {commit_hash}')

            # Force current branch to this new history
            self.repo.repo.git.branch('-D', branch_name)
            self.repo.repo.git.branch('-m', branch_name)
        else:
            # Create a new branch at the target commit
            self.repo.repo.git.checkout(commit_hash)

            # Create a new branch at this point
            self.repo.repo.git.checkout('-b', 'temp_branch')

            # Rebase the remaining commits onto the new branch
            try:
                self.repo.repo.git.rebase('--onto', 'temp_branch', commit_hash, branch_name)
            except git.GitCommandError as err:
                self.repo.repo.git.rebase('--abort')
                self.repo.repo.git.checkout(branch_name)
                self.repo.repo.git.branch('-D', 'temp_branch')
                raise ValueError("Failed to rebase commits") from err

            # Switch back to original branch and update it
            self.repo.repo.git.checkout(branch_name)
            self.repo.repo.git.reset('--hard', 'temp_branch')
            self.repo.repo.git.branch('-D', 'temp_branch')

    def truncate_after(
        self,
        point: Union[str, datetime],
        squash: bool = False  # TODO: Implement squash functionality
    ) -> None:
        """Truncate history after specified point.
        
        Args:
            point: Commit hash, ref, or datetime to truncate after
            squash: If True, squashes remaining commits into one. Currently not implemented.
        """
        commit_hash = self._parse_point(point)

        # Simply reset to the specified point
        self.repo.repo.git.reset('--hard', commit_hash)

    def _cherry_pick_commits(self, commits: list) -> None:
        """Cherry pick the given commits onto the current branch."""
        branch_name = self.repo.current_branch

        for commit in commits[:-1]:  # Skip the oldest commit since we already have its state
            try:
                print(f"Cherry-picking {commit.hexsha}")
                try:
                    self.repo.repo.git.cherry_pick(commit.hexsha)
                except git.GitCommandError as e:
                    # Check if this is an empty cherry-pick
                    if ("nothing to commit" in str(e) and
                            "previous cherry-pick is now empty" in str(e)):
                        # Empty cherry-pick is okay, commit it
                        self.repo.repo.git.commit('--allow-empty', '-C', commit.hexsha)
                    else:
                        raise
            except git.GitCommandError as err:
                print(f"Failed to cherry-pick {commit.hexsha}: {err!s}")
                self.repo.repo.git.cherry_pick('--abort')
                self.repo.repo.git.checkout(branch_name)
                with suppress(git.GitCommandError):
                    self.repo.repo.git.branch('-D', 'temp_branch')
                raise ValueError(f"Failed to cherry-pick commit {commit.hexsha}") from err

    def keep_recent(
        self,
        count: int,
        squash: bool = False
    ) -> None:
        """Keep only N most recent commits.
        
        Args:
            count: Number of recent commits to keep
            squash: If True, squashes kept commits into one
        """
        if count <= 0:
            raise ValueError("Count must be positive")

        total_commits = self._get_commit_count()
        if count >= total_commits:
            return  # Nothing to do

        # Get the most recent commits
        commits = list(self.repo.repo.iter_commits(max_count=count))
        if not commits:
            return

        # Get the oldest commit we want to keep
        oldest_commit = commits[-1]
        branch_name = self.repo.current_branch

        print(f"Current branch: {branch_name}")
        print(f"Total commits: {total_commits}")
        print(f"Keeping {count} commits")
        print(f"Oldest commit to keep: {oldest_commit.hexsha}")

        # Create a new orphan branch and set up initial state
        self.repo.repo.git.checkout('--orphan', 'temp_branch')
        self.repo.repo.git.reset('--hard')
        self.repo.repo.git.checkout(oldest_commit.hexsha, '--', '.')
        self.repo.repo.git.add('.')
        self.repo.repo.git.commit(
            '-m', 
            f'Initial state from {oldest_commit.hexsha}', 
            '--allow-empty'
        )

        # Cherry-pick the remaining commits
        if len(commits) > 1:
            self._cherry_pick_commits(commits)

        # Switch back and clean up
        self.repo.repo.git.checkout(branch_name)
        self.repo.repo.git.reset('--hard', 'temp_branch')

        with suppress(git.GitCommandError):
            self.repo.repo.git.branch('-D', 'temp_branch')

        # Verify the commit count
        final_count = len(list(self.repo.repo.iter_commits()))
        print(f"Final commit count: {final_count}")
