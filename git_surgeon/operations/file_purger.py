"""File purging operations for removing files from git history."""

import subprocess
from pathlib import Path
from typing import Optional

from git import Commit

from git_surgeon.core import GitRepo


class FilePurger:
    """Handles removal of files from repository history."""

    def __init__(self, repo: GitRepo, pattern: str):
        self.repo = repo
        self.pattern = pattern
        self._matches: Optional[list[Path]] = None
        self._affected_commits: Optional[set[Commit]] = None

    def find_matches(self) -> list[Path]:
        """Find all files matching pattern in repository history."""
        if self._matches is None:
            # Use git ls-files to find matches in current state
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.repo.path,
                capture_output=True,
                text=True,
                check=True
            )

            all_files = result.stdout.splitlines()
            matches = []

            # Convert pattern to glob pattern
            for file in all_files:
                file_path = Path(self.repo.path) / file
                if file_path.match(self.pattern):
                    matches.append(file_path)

            self._matches = matches

        return self._matches

    @property
    def affected_commits(self) -> set[Commit]:
        """Get all commits that would be modified."""
        if self._affected_commits is None:
            matches = self.find_matches()
            commits = set()

            for match in matches:
                # Get all commits that modified this file
                rel_path = match.relative_to(self.repo.path)
                for commit in self.repo.repo.iter_commits(paths=str(rel_path)):
                    commits.add(commit)

            self._affected_commits = commits

        return self._affected_commits

    def calculate_size_impact(self) -> int:
        """Calculate total size of files to be removed."""
        return sum(match.stat().st_size for match in self.find_matches())

    def execute(
        self,
        branches: Optional[list[str]] = None,
        preserve_recent: bool = False
    ) -> None:
        """Execute the purge operation.
        
        Args:
            branches: Optional list of branches to process. If None, processes all branches.
            preserve_recent: If True, preserves files in the most recent commit.
        """
        matches = self.find_matches()
        if not matches:
            return

        # Get relative paths for all matches
        rel_paths = [str(match.relative_to(self.repo.path)) for match in matches]
        paths_arg = ' '.join(f'"{path}"' for path in rel_paths)

        try:
            # Ensure we're on a clean state
            subprocess.run(
                ['git', 'stash', '--include-untracked'],
                cwd=self.repo.path,
                check=True,
                capture_output=True,
                text=True
            )

            # First remove from the index
            subprocess.run(
                ['git', 'rm', '-rf', '--cached', '--ignore-unmatch'] + rel_paths,
                cwd=self.repo.path,
                check=True,
                capture_output=True,
                text=True
            )

            # Commit the removal
            subprocess.run(
                ['git', 'commit', '--allow-empty', '-m', 'Remove sensitive files'],
                cwd=self.repo.path,
                check=True,
                capture_output=True,
                text=True
            )

            # Then filter the branch history
            filter_cmd = f'git rm -rf --cached --ignore-unmatch {paths_arg}'
            filter_branch_cmd = [
                'git', 'filter-branch', '--force',
                '--index-filter', filter_cmd,
                '--prune-empty', '--tag-name-filter', 'cat',
                '--', '--all'
            ]

            if preserve_recent:
                # If preserving recent, only filter commits before HEAD
                filter_branch_cmd.extend(['HEAD^..'])
            
            if branches:
                # If specific branches are specified, only filter those
                filter_branch_cmd[filter_branch_cmd.index('--all')] = ' '.join(branches)

            subprocess.run(
                filter_branch_cmd,
                cwd=self.repo.path,
                check=True,
                capture_output=True,
                text=True
            )

            # Remove the original refs to allow garbage collection
            subprocess.run(
                ['git', 'for-each-ref', '--format=%(refname)', 'refs/original/'],
                cwd=self.repo.path,
                check=True,
                capture_output=True,
                text=True
            ).stdout.splitlines()

            for ref in subprocess.run(
                ['git', 'for-each-ref', '--format=%(refname)', 'refs/original/'],
                cwd=self.repo.path,
                check=True,
                capture_output=True,
                text=True
            ).stdout.splitlines():
                subprocess.run(
                    ['git', 'update-ref', '-d', ref],
                    cwd=self.repo.path,
                    check=True,
                    capture_output=True,
                    text=True
                )

            # Reset the working directory to match the new HEAD
            subprocess.run(
                ['git', 'reset', '--hard'],
                cwd=self.repo.path,
                check=True,
                capture_output=True
            )

            # Clean up untracked files
            subprocess.run(
                ['git', 'clean', '-fd'],
                cwd=self.repo.path,
                check=True,
                capture_output=True
            )

            # Clean up repository and remove old objects
            subprocess.run(
                ['git', 'reflog', 'expire', '--expire=now', '--all'],
                cwd=self.repo.path,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ['git', 'gc', '--prune=now', '--aggressive'],
                cwd=self.repo.path,
                check=True,
                capture_output=True
            )

            # Try to restore stashed changes if any
            subprocess.run(
                ['git', 'stash', 'pop'],
                cwd=self.repo.path,
                check=False,  # Don't fail if there was nothing to pop
                capture_output=True,
                text=True
            )

        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {e.stderr}"
            raise RuntimeError(error_msg) from e
