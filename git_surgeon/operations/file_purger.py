"""File purging operations for removing files from git history."""

import fnmatch
from pathlib import Path
from typing import Callable, Optional

from git_filter_repo import Blob, Commit, FastExportParser  # type: ignore

from git_surgeon.core import GitRepo
from git_surgeon.utils.git_filter import run_git_filter


class FilePurger:
    """Handles removal of files from repository history."""

    def __init__(self, repo: GitRepo, pattern: str):
        self.repo = repo
        self.pattern = pattern
        self._matches: set[Path] = set()
        self._affected_commits: Optional[set[str]] = None

    @property
    def affected_commits(self) -> set[str]:
        """Get the set of commit hashes that will be affected by the purge operation."""
        if self._affected_commits is None:
            self._affected_commits = set()
            matches = self.find_matches()
            if matches:
                # Get all commits that modified any of the matched files
                for match in matches:
                    rel_path = str(match.relative_to(self.repo.path))
                    commits = self.repo.repo.git.log(
                        "--all", "--format=%H", "--", rel_path
                    ).splitlines()
                    self._affected_commits.update(commits)
        return self._affected_commits

    def find_matches(self) -> set[Path]:
        """Find all files in the repository that match the pattern."""
        if not self._matches:
            result = self.repo.repo.git.ls_files().splitlines()

            # Convert ** pattern to fnmatch pattern
            patterns = self._get_patterns()

            # Match files against all patterns
            for file in result:
                # Normalize path separators
                file = file.replace("\\", "/")
                for pattern in patterns:
                    if fnmatch.fnmatch(file, pattern):
                        self._matches.add(self.repo.path / file)
                        break

        return self._matches

    def _get_patterns(self) -> list[str]:
        """Convert ** pattern to fnmatch patterns."""
        if "**" in self.pattern and self.pattern.startswith("**/"):
            # For **/.env, convert to */.env and .env to match both root and nested files
            return [self.pattern[3:], "*/" + self.pattern[3:]]
        return [self.pattern]

    def calculate_size_impact(self) -> int:
        """Calculate total size of files to be removed."""
        total_size = 0
        for file in self.find_matches():
            if file.exists():
                total_size += file.stat().st_size
        return total_size

    def _get_relative_matches(self) -> set[bytes]:
        """Get relative paths of matches as bytes."""
        matches = self.find_matches()
        return {
            str(m.relative_to(self.repo.path)).replace("\\", "/").encode()
            for m in matches
        }

    def _cleanup_repo(self) -> None:
        """Clean up repository after filtering."""
        if not self.repo.repo.bare:
            self.repo.repo.git.reset("--hard")
            self.repo.repo.git.clean("-fd")  # Clean up untracked files
            self.repo.repo.git.reflog("expire", "--expire=now", "--all")
        self.repo.gc()

    def _handle_branches(self, branches: Optional[list[str]]) -> Optional[str]:
        """Handle branch filtering.

        Returns:
            The name of the original branch if it was changed, None otherwise.
        """
        if not branches:
            return None

        original_branch = self.repo.repo.active_branch.name
        self.repo.repo.git.checkout(branches[0])
        for branch in branches[1:]:
            self.repo.repo.git.checkout(branch)
        return original_branch

    def _find_recent_commits(self, matches: set[Path]) -> list[str]:
        """Find the most recent commits that modified the matched files."""
        recent_commits = []
        for match in matches:
            rel_path = str(match.relative_to(self.repo.path))
            commits = self.repo.repo.git.log(
                "-n", "1", "--format=%H", "--", rel_path
            ).splitlines()
            recent_commits.extend(commits)
        return recent_commits

    def _create_preserve_branch(self, recent_commits: list[str]) -> Optional[str]:
        """Create a branch to preserve recent changes if needed.

        Returns:
            The name of the preserve branch if created, None otherwise.
        """
        if not recent_commits:
            return None

        preserve_branch = "preserved-files"
        self.repo.repo.git.branch(preserve_branch)
        return preserve_branch

    def _create_callbacks(
        self,
        relative_matches: set[bytes],
        preserve_recent: bool,
        preserve_branch: Optional[str],
        recent_commits: list[str],
    ) -> tuple[Callable[[Blob], None], Callable[[Commit, object], None]]:
        """Create the blob and commit callbacks for git-filter-repo."""

        def blob_callback(blob: Blob) -> None:
            """Process each blob to check if it should be removed."""
            if hasattr(blob, "filename"):
                # Normalize path separators
                filename = blob.filename.replace(b"\\", b"/")
                if filename in relative_matches:
                    blob.skip()

        def commit_callback(commit: Commit, _metadata: object) -> None:
            """Process each commit to handle file changes."""
            # Skip if this is a preserved commit
            if preserve_recent and preserve_branch and commit.id in recent_commits:
                return

            # Filter out file changes for skipped blobs and matching paths
            new_changes = []
            for change in commit.file_changes:
                # Normalize path separators
                filename = change.filename.replace(b"\\", b"/")
                if filename in relative_matches:
                    continue
                if hasattr(change, "blob_id") and change.blob_id is None:
                    continue
                new_changes.append(change)
            commit.file_changes = new_changes

            # Skip empty commits
            if not commit.file_changes:
                commit.skip()

        return blob_callback, commit_callback

    def execute(
        self, *, branches: Optional[list[str]] = None, preserve_recent: bool = False
    ) -> None:
        """Execute the purge operation.

        Args:
            branches: Optional list of branches to process. If None, all branches are processed.
            preserve_recent: If True, preserves recent history.
        """
        matches = self.find_matches()
        if not matches:
            return

        relative_matches = self._get_relative_matches()
        original_branch = self._handle_branches(branches)

        # Handle preserve_recent flag
        recent_commits = []
        preserve_branch = None
        if preserve_recent:
            recent_commits = self._find_recent_commits(matches)
            preserve_branch = self._create_preserve_branch(recent_commits)

        # Create and run the filter
        blob_callback, commit_callback = self._create_callbacks(
            relative_matches, preserve_recent, preserve_branch, recent_commits
        )
        parser = FastExportParser(
            blob_callback=blob_callback, commit_callback=commit_callback
        )
        run_git_filter(self.repo.path, parser)

        # Restore original branch if needed
        if original_branch:
            self.repo.repo.git.checkout(original_branch)

        # Clean up repository
        self._cleanup_repo()
