#!/usr/bin/env python3

"""Lint script for the Git-Nuke project."""

import subprocess
import sys


def run_lint():
    """Run linting checks on the project using pylint and mypy."""
    print("Running linting checks...")

    pylint_result = subprocess.run(
        ["pylint", "git_nuke", "tests", "scripts"],
        capture_output=True,
        text=True,
        check=False,
    )
    mypy_result = subprocess.run(
        ["mypy", "git_nuke"], capture_output=True, text=True, check=False
    )

    if pylint_result.returncode != 0:
        print("Pylint issues found:")
        print(pylint_result.stdout)
    else:
        print("Pylint checks passed.")

    if mypy_result.returncode != 0:
        print("Mypy issues found:")
        print(mypy_result.stdout)
    else:
        print("Mypy checks passed.")

    if pylint_result.returncode != 0 or mypy_result.returncode != 0:
        sys.exit(1)

    print("All linting checks passed!")
    sys.exit(0)


if __name__ == "__main__":
    run_lint()
