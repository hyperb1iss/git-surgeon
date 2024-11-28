"""Utility module for git filtering operations."""

import subprocess
from pathlib import Path
from typing import Optional

from git_filter_repo import FastExportParser  # type: ignore


def run_git_filter(
    repo_path: Path,
    parser: FastExportParser,
    temp_file: Optional[Path] = None,
) -> None:
    """
    Run git-filter-repo operations using fast-export and fast-import.

    Args:
        repo_path: Path to the git repository
        parser: Configured FastExportParser instance with callbacks
        temp_file: Optional path to temporary file for storing filtered history

    Raises:
        RuntimeError: If git fast-import fails
    """
    # Run git fast-export and pipe through the parser
    with subprocess.Popen(
        ["git", "fast-export", "--all"],
        stdout=subprocess.PIPE,
        cwd=repo_path,
    ) as fast_export:
        assert fast_export.stdout is not None  # for mypy

        if temp_file:
            # Use temporary file as intermediate storage
            with open(temp_file, "wb") as output_stream:
                parser.run(fast_export.stdout, output_stream)

            # Run git fast-import with the temporary file
            try:
                subprocess.run(
                    ["git", "fast-import", "--force"],
                    input=temp_file.read_bytes(),
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except subprocess.CalledProcessError as err:
                raise RuntimeError(f"git-filter-repo failed: {err.stderr}") from err
        else:
            # Direct pipe between fast-export and fast-import
            with subprocess.Popen(
                ["git", "fast-import", "--force"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                cwd=repo_path,
            ) as fast_import:
                assert fast_import.stdin is not None  # for mypy
                parser.run(fast_export.stdout, fast_import.stdin)

                # Clean up
                fast_export.stdout.close()
                fast_import.stdin.close()
                fast_export.wait()
                fast_import.wait()
