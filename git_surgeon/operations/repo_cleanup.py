"""Repository cleanup operations including large file removal and sensitive data cleaning."""

import re
import subprocess
from typing import Optional

from git_filter_repo import Blob, Commit, FastExportParser  # type: ignore

from git_surgeon.core import GitRepo


class RepoCleanup:
    """Handles various repository cleanup operations."""

    def __init__(self, repo: GitRepo):
        self.repo = repo

    def _parse_size(self, size_spec: str) -> int:
        """Convert size specification (e.g., '10MB') to bytes."""
        units = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 * 1024,
            "GB": 1024 * 1024 * 1024,
        }

        match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?B)$", size_spec.upper())
        if not match:
            raise ValueError(f"Invalid size specification: {size_spec}")

        value, unit = match.groups()
        return int(float(value) * units[unit])

    def clean_large_files(
        self, size_threshold: str, patterns: Optional[list[str]] = None
    ) -> None:
        """Remove files larger than threshold."""
        threshold_bytes = self._parse_size(size_threshold)

        def blob_callback(blob: Blob) -> None:
            """Process each blob to check size and patterns."""
            if len(blob.data) > threshold_bytes:
                if patterns:
                    # Only filter if filename matches one of the patterns
                    filename = blob.filename if hasattr(blob, "filename") else ""
                    if not any(re.match(pattern, filename) for pattern in patterns):
                        return
                blob.skip()

        def commit_callback(commit: Commit, _metadata: object) -> None:
            """Process each commit to update filenames."""
            # Filter out file changes for skipped blobs
            commit.file_changes = [
                change
                for change in commit.file_changes
                if not (hasattr(change, "blob_id") and change.blob_id is None)
            ]

        # Create parser with callbacks
        parser = FastExportParser(
            blob_callback=blob_callback, commit_callback=commit_callback
        )

        # Run the filtering
        self._run_filter_repo(parser)

    def clean_sensitive_data(self, patterns: list[str]) -> None:
        """Remove sensitive data matching patterns."""
        compiled_patterns = [re.compile(p) for p in patterns]

        def blob_callback(blob: Blob) -> None:
            """Process each blob to check for sensitive data."""
            data = blob.data.decode("utf-8", errors="ignore")
            for pattern in compiled_patterns:
                if pattern.search(data):
                    # Replace sensitive data with placeholder
                    data = pattern.sub("[REDACTED]", data)
                    blob.data = data.encode("utf-8")

        # Create parser with callbacks
        parser = FastExportParser(blob_callback=blob_callback)

        # Run the filtering
        self._run_filter_repo(parser)

    def _run_filter_repo(self, parser: FastExportParser) -> None:
        """Run git-filter-repo with the given parser."""
        # Set up fast-export process
        export_cmd = ["git", "fast-export", "--all"]
        import_cmd = ["git", "fast-import", "--force"]

        with subprocess.Popen(
            export_cmd, cwd=self.repo.path, stdout=subprocess.PIPE
        ) as export_proc:
            assert export_proc.stdout is not None  # for mypy

            with subprocess.Popen(
                import_cmd,
                cwd=self.repo.path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            ) as import_proc:
                assert import_proc.stdin is not None  # for mypy

                # Run the parser
                parser.run(export_proc.stdout, import_proc.stdin)

                # Clean up
                export_proc.stdout.close()
                import_proc.stdin.close()
                export_proc.wait()
                import_proc.wait()

        # Reset the working directory to match the new HEAD
        if not self.repo.repo.bare:
            self.repo.repo.git.reset("--hard")

        # Run garbage collection
        self.repo.repo.git.gc("--prune=now")
