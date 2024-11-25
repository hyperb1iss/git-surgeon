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
            branches: Optional list of branches to process. Currently not implemented.
            preserve_recent: If True, preserves files in recent commits. Currently not implemented.
        """
        # Create a filter script for git-filter-repo
        filter_script = Path(self.repo.path) / 'filter.py'
        filter_script.write_text(f'''
import sys
import re

pattern = r"{self.pattern}"

def handle_blob(blob):
    if re.match(pattern, blob.path.decode()):
        blob.skip()
''')

        try:
            subprocess.run([
                'git-filter-repo',
                '--force',
                '--blob-callback', str(filter_script)
            ], cwd=self.repo.path, check=True, capture_output=True)
        finally:
            filter_script.unlink()
