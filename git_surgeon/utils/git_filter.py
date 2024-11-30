"""Utility module for git filtering operations."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from git_filter_repo import FastExportParser  # type: ignore

logger = logging.getLogger(__name__)


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
    try:
        # Run git fast-export and pipe through the parser
        logger.debug("Running git fast-export...")
        fast_export = subprocess.Popen(
            ["git", "fast-export", "--all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=repo_path,
        )

        if fast_export.stdout is None:
            raise RuntimeError("Failed to get stdout from git fast-export")

        if temp_file:
            # Use temporary file as intermediate storage
            logger.debug("Writing filtered history to temporary file: %s", temp_file)
            with open(temp_file, "wb") as output_stream:
                parser.run(fast_export.stdout, output_stream)

            # Run git fast-import with the temporary file
            try:
                logger.debug("Running git fast-import...")
                result = subprocess.run(  # noqa: UP022
                    ["git", "fast-import", "--force"],
                    input=temp_file.read_bytes(),
                    cwd=repo_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                if result.stderr:
                    logger.warning(
                        "git fast-import warnings: %s", result.stderr.decode()
                    )
            except subprocess.CalledProcessError as err:
                raise RuntimeError(
                    f"git-filter-repo failed: {err.stderr.decode()}"
                ) from err
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file)
                    logger.debug("Cleaned up temporary file: %s", temp_file)
                except OSError as err:
                    logger.warning("Failed to clean up temporary file: %s", err)
        else:
            # Direct pipe between fast-export and fast-import
            logger.debug("Using direct pipe between fast-export and fast-import")
            fast_import = subprocess.Popen(
                ["git", "fast-import", "--force"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=repo_path,
            )

            if fast_import.stdin is None:
                raise RuntimeError("Failed to get stdin for git fast-import")

            parser.run(fast_export.stdout, fast_import.stdin)

            # Clean up
            fast_export.stdout.close()
            fast_import.stdin.close()
            fast_export.wait()
            fast_import.wait()

            if fast_import.returncode != 0:
                stderr = fast_import.stderr
                if stderr is not None:
                    error_msg = stderr.read().decode()
                    raise RuntimeError(f"git-filter-repo failed: {error_msg}")
                raise RuntimeError("git-filter-repo failed with unknown error")

    except Exception as e:
        logger.error("Failed to rewrite git history: %s", e)
        raise
