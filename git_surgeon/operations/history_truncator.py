"""History truncation operations for managing git repository history."""

from contextlib import suppress
from datetime import datetime
from typing import Union

import git

from git_surgeon.core import GitRepo


def ensure_str(s: Union[str, bytes]) -> str:
    """Convert bytes to string if needed, using UTF-8 encoding.

    Args:
        s: Input that may be either string or bytes

    Returns:
        String representation of the input, decoded from UTF-8 if necessary
    """
    return s.decode("utf-8", errors="replace") if isinstance(s, bytes) else s


class HistoryTruncator:
    """Handles truncation of repository history."""

    def __init__(self, repo: GitRepo):
        self.repo = repo

    def _parse_point(self, point: Union[str, datetime]) -> str:
        """Convert a point specification to a commit hash."""
        if isinstance(point, datetime):
            # Find the most recent commit before this date
            commits = self.repo.repo.iter_commits(until=point.isoformat())
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

    def _squash_history(self, commit_hash: str) -> str:
        """Squash all history up to the specified commit.

        Args:
            commit_hash: Hash of the commit to squash up to

        Returns:
            Hash of the squashed commit
        """
        # Create new orphan branch starting fresh
        self.repo.repo.git.checkout("--orphan", "temp_branch")
        self.repo.repo.git.reset("--hard")

        # Get the tree state at the target commit
        self.repo.repo.git.checkout(commit_hash, "--", ".")
        self.repo.repo.git.add(".")

        # Create the squashed commit with all history up to this point
        message = f"Squashed history before {commit_hash}"
        # Add the commit messages from all squashed commits to preserve history info
        squashed_commits = list(self.repo.repo.iter_commits(commit_hash))
        if squashed_commits:
            message += "\n\nSquashed commits:\n"
            for commit in reversed(squashed_commits):
                commit_hexsha = ensure_str(commit.hexsha)
                commit_summary = ensure_str(commit.summary)
                message += f"\n{commit_hexsha[:8]} {commit_summary}"

        self.repo.repo.git.commit("--allow-empty", "-m", message)
        return self.repo.repo.head.commit.hexsha

    def _rebase_later_commits(
        self, base_hash: str, commit_hash: str, branch_name: str
    ) -> None:
        """Rebase commits after the specified point onto a new base.

        Args:
            base_hash: Hash of the commit to rebase onto
            commit_hash: Hash of the commit to rebase from
            branch_name: Name of the current branch
        """
        # Create a temporary branch for the later commits
        self.repo.repo.git.branch("temp_commits", branch_name)

        try:
            # Rebase all later commits onto our squashed base
            self.repo.repo.git.rebase(
                "--rebase-merges",
                "--onto",
                base_hash,
                commit_hash,
                "temp_commits",
            )

            # Update the original branch to point to the rebased history
            self.repo.repo.git.checkout(branch_name)
            self.repo.repo.git.reset("--hard", "temp_commits")

        except git.GitCommandError as err:
            # Clean up and abort on failure
            with suppress(git.GitCommandError):
                self.repo.repo.git.rebase("--abort")

            self.repo.repo.git.checkout(branch_name)

            # Clean up temporary branches
            with suppress(git.GitCommandError):
                self.repo.repo.git.branch("-D", "temp_branch")

            with suppress(git.GitCommandError):
                self.repo.repo.git.branch("-D", "temp_commits")

            raise ValueError(f"Failed to rebase later commits: {err}") from err
        finally:
            # Clean up temporary branches
            with suppress(git.GitCommandError):
                self.repo.repo.git.branch("-D", "temp_commits")

    def truncate_before(
        self, point: Union[str, datetime], squash: bool = False
    ) -> None:
        """Truncate history before specified point.

        Args:
            point: Commit hash, ref, or datetime to truncate before
            squash: If True, squashes all history up to and including the specified point
                   into a single commit, while preserving all later commits
        """
        commit_hash = self._parse_point(point)
        branch_name = self.repo.current_branch

        if squash:
            # Get all commits after the specified point
            later_commits = list(
                self.repo.repo.iter_commits(
                    f"{commit_hash}..{branch_name}",
                    reverse=True,  # Start with oldest commits
                )
            )

            base_hash = self._squash_history(commit_hash)

            if later_commits:
                self._rebase_later_commits(base_hash, commit_hash, branch_name)
            else:
                # No later commits, just update the branch to our squashed commit
                self.repo.repo.git.checkout(branch_name)
                self.repo.repo.git.reset("--hard", base_hash)

            # Clean up temporary branch
            with suppress(git.GitCommandError):
                self.repo.repo.git.branch("-D", "temp_branch")
        else:
            # Create a new branch at the target commit
            self.repo.repo.git.checkout(commit_hash)

            # Create a new branch at this point
            self.repo.repo.git.checkout("-b", "temp_branch")

            # Rebase the remaining commits onto the new branch
            try:
                self.repo.repo.git.rebase(
                    "--onto", "temp_branch", commit_hash, branch_name
                )
            except git.GitCommandError as err:
                self.repo.repo.git.rebase("--abort")
                self.repo.repo.git.checkout(branch_name)
                self.repo.repo.git.branch("-D", "temp_branch")
                raise ValueError("Failed to rebase commits") from err

            # Switch back to original branch and update it
            self.repo.repo.git.checkout(branch_name)
            self.repo.repo.git.reset("--hard", "temp_branch")
            self.repo.repo.git.branch("-D", "temp_branch")

    def truncate_after(
        self,
        point: Union[str, datetime],
        squash: bool = False,
    ) -> None:
        """Truncate history after specified point.

        Args:
            point: Commit hash, ref, or datetime to truncate after
            squash: If True, squashes remaining commits into one.
        """
        commit_hash = self._parse_point(point)
        branch_name = self.repo.current_branch

        if squash:
            # Get all commits up to the specified point
            commits = list(self.repo.repo.iter_commits(f"{commit_hash}"))
            if len(commits) <= 1:
                # Nothing to squash
                self.repo.repo.git.reset("--hard", commit_hash)
                return

            # Create new orphan branch
            self.repo.repo.git.checkout("--orphan", "temp_branch")
            self.repo.repo.git.reset("--hard")

            # Get tree state at the target commit
            self.repo.repo.git.checkout(commit_hash, "--", ".")
            self.repo.repo.git.add(".")

            # Create squashed commit with history information
            message = "Squashed commits up to this point\n\nSquashed commits:\n"
            for commit in reversed(commits):
                commit_hexsha = ensure_str(commit.hexsha)
                commit_summary = ensure_str(commit.summary)
                message += f"\n{commit_hexsha[:8]} {commit_summary}"

            self.repo.repo.git.commit("-m", message)

            # Update the original branch
            self.repo.repo.git.checkout(branch_name)
            self.repo.repo.git.reset("--hard", "temp_branch")

            # Clean up temporary branch
            with suppress(git.GitCommandError):
                self.repo.repo.git.branch("-D", "temp_branch")
        else:
            # Simply reset to the specified point
            self.repo.repo.git.reset("--hard", commit_hash)

    def _cherry_pick_commits(self, commits: list) -> None:
        """Cherry pick the given commits onto the current branch."""
        branch_name = self.repo.current_branch

        for commit in commits[
            :-1
        ]:  # Skip the oldest commit since we already have its state
            try:
                commit_hexsha = ensure_str(commit.hexsha)
                print(f"Cherry-picking {commit_hexsha}")
                try:
                    self.repo.repo.git.cherry_pick(commit.hexsha)
                except git.GitCommandError as e:
                    # Check if this is an empty cherry-pick
                    if "nothing to commit" in str(
                        e
                    ) and "previous cherry-pick is now empty" in str(e):
                        # Empty cherry-pick is okay, commit it
                        self.repo.repo.git.commit("--allow-empty", "-C", commit.hexsha)
                    else:
                        raise
            except git.GitCommandError as err:
                commit_hexsha = ensure_str(commit.hexsha)
                print(f"Failed to cherry-pick {commit_hexsha}: {err!s}")
                self.repo.repo.git.cherry_pick("--abort")
                self.repo.repo.git.checkout(branch_name)
                with suppress(git.GitCommandError):
                    self.repo.repo.git.branch("-D", "temp_branch")
                raise ValueError(
                    f"Failed to cherry-pick commit {commit_hexsha}"
                ) from err

    def keep_recent(self, count: int, squash: bool = False) -> None:
        """Keep only N most recent commits.

        Args:
            count: Number of recent commits to keep
            squash: If True, squashes all but the most recent commits into one
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
        oldest_commit_hexsha = ensure_str(oldest_commit.hexsha)
        print(f"Oldest commit to keep: {oldest_commit_hexsha}")

        if squash and count > 1:
            # Create a new orphan branch and set up initial state
            self.repo.repo.git.checkout("--orphan", "temp_branch")
            self.repo.repo.git.reset("--hard")

            # Get the tree state at the oldest commit
            self.repo.repo.git.checkout(oldest_commit.hexsha, "--", ".")
            self.repo.repo.git.add(".")

            # Create squashed commit with history information
            message = "Squashed older commits\n\nSquashed commits:\n"
            for commit in reversed(commits[1:]):  # Skip the most recent commit
                commit_hexsha = ensure_str(commit.hexsha)
                commit_summary = ensure_str(commit.summary)
                message += f"\n{commit_hexsha[:8]} {commit_summary}"

            self.repo.repo.git.commit("-m", message)

            # Cherry-pick the most recent commit
            most_recent = commits[0]
            try:
                self.repo.repo.git.cherry_pick(most_recent.hexsha)
            except git.GitCommandError as err:
                if "nothing to commit" in str(err):
                    self.repo.repo.git.commit("--allow-empty", "-C", most_recent.hexsha)
                else:
                    raise ValueError(
                        f"Failed to cherry-pick commit {most_recent.hexsha}"
                    ) from err

            # Switch back and clean up
            self.repo.repo.git.checkout(branch_name)
            self.repo.repo.git.reset("--hard", "temp_branch")

            with suppress(git.GitCommandError):
                self.repo.repo.git.branch("-D", "temp_branch")
        else:
            # Original non-squash implementation
            self.repo.repo.git.checkout("--orphan", "temp_branch")
            self.repo.repo.git.reset("--hard")
            self.repo.repo.git.checkout(oldest_commit.hexsha, "--", ".")
            self.repo.repo.git.add(".")
            self.repo.repo.git.commit(
                "-m", f"Initial state from {oldest_commit.hexsha}", "--allow-empty"
            )

            # Cherry-pick the remaining commits
            if len(commits) > 1:
                self._cherry_pick_commits(commits)

            # Switch back and clean up
            self.repo.repo.git.checkout(branch_name)
            self.repo.repo.git.reset("--hard", "temp_branch")

            with suppress(git.GitCommandError):
                self.repo.repo.git.branch("-D", "temp_branch")

        # Verify the commit count
        final_count = len(list(self.repo.repo.iter_commits()))
        print(f"Final commit count: {final_count}")
