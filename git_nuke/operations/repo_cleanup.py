"""Repository cleanup operations including large file removal and sensitive data cleaning."""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from git_nuke.core import GitRepo


class RepoCleanup:
    """Handles various repository cleanup operations."""

    def __init__(self, repo: GitRepo):
        self.repo = repo

    def _parse_size(self, size_spec: str) -> int:
        """Convert size specification (e.g., '10MB') to bytes."""
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
        }

        match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B)$', size_spec.upper())
        if not match:
            raise ValueError(f"Invalid size specification: {size_spec}")

        value, unit = match.groups()
        return int(float(value) * units[unit])

    def _find_large_files(self, size_threshold: int) -> dict[str, int]:
        """Find all files larger than threshold in history."""
        # Use git rev-list to find large files
        result = subprocess.run([
            'git', 'rev-list', '--objects', '--all'
        ], cwd=self.repo.path, capture_output=True, text=True, check=True)

        large_files = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue

            obj_hash, *path_parts = parts

            # Get object size
            size_result = subprocess.run([
                'git', 'cat-file', '-s', obj_hash
            ], cwd=self.repo.path, capture_output=True, text=True, check=True)

            size = int(size_result.stdout.strip())
            if size > size_threshold:
                path = ' '.join(path_parts)
                large_files[path] = size

        return large_files

    def clean_large_files(
        self,
        size_threshold: str,
        patterns: Optional[list[str]] = None
    ) -> None:
        """Remove files larger than threshold."""
        threshold_bytes = self._parse_size(size_threshold)
        large_files = self._find_large_files(threshold_bytes)

        if patterns:
            # Filter by patterns
            large_files = {
                path: size
                for path, size in large_files.items()
                if any(re.match(pattern, path) for pattern in patterns)
            }

        if not large_files:
            return

        # Use git filter-repo to remove the files
        filter_script = Path(self.repo.path) / 'filter.py'
        filter_script.write_text(f'''
import sys
import json

large_files = {json.dumps(list(large_files.keys()))}

def handle_blob(blob):
    if blob.path.decode() in large_files:
        blob.skip()
        return True
    return False
''')

        try:
            subprocess.run([
                'git-filter-repo',
                '--force',
                '--blob-callback', str(filter_script)
            ], cwd=self.repo.path, check=True, capture_output=True)

            # Clean up any remaining files in working directory
            for file in large_files:
                file_path = self.repo.path / file
                if file_path.exists():
                    file_path.unlink()
        finally:
            filter_script.unlink()

    def clean_sensitive_data(
        self,
        patterns: list[str]
    ) -> None:
        """Remove sensitive data matching patterns."""
        # Create a filter script for git-filter-repo
        filter_script = Path(self.repo.path) / 'filter.py'
        filter_script.write_text(f'''
import re
import sys

patterns = {patterns!r}
compiled_patterns = [re.compile(p) for p in patterns]

def handle_blob(blob):
    data = blob.data.decode('utf-8', errors='ignore')
    for pattern in compiled_patterns:
        if pattern.search(data):
            # Replace sensitive data with placeholder
            data = pattern.sub('[REDACTED]', data)
            blob.data = data.encode('utf-8')
''')

        subprocess.run([
            'git-filter-repo',
            '--force',
            '--python', str(filter_script)
        ], cwd=self.repo.path, check=True)

        filter_script.unlink()
