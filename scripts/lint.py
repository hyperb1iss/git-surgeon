#!/usr/bin/env python3

"""Lint script for the Git-surgeon project."""

import subprocess
import sys


def run_lint():
    """Run linting checks on the project using pylint, mypy, and ruff."""
    print("Running linting checks...")

    pylint_result = subprocess.run(
        ["pylint", "git_surgeon", "tests", "scripts"],
        capture_output=True,
        text=True,
        check=False,
    )
    mypy_result = subprocess.run(
        ["mypy", "git_surgeon"], capture_output=True, text=True, check=False
    )
    ruff_result = subprocess.run(
        ["ruff", "check", "git_surgeon", "tests", "scripts"],
        capture_output=True,
        text=True,
        check=False,
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

    if ruff_result.returncode != 0:
        print("Ruff issues found:")
        print(ruff_result.stdout)
    else:
        print("Ruff checks passed.")

    if (
        pylint_result.returncode != 0
        or mypy_result.returncode != 0
        or ruff_result.returncode != 0
    ):
        sys.exit(1)

    print("All linting checks passed!")
    sys.exit(0)


if __name__ == "__main__":
    run_lint()
