"""Module for rewriting git author and committer information in repository history."""

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from git_surgeon.core import GitRepo


@dataclass
class AuthorMapping:
    """Data class representing a mapping between old and new author information."""

    old: str  # Format: "Name <email>"
    new: str  # Format: "Name <email>"


class AuthorRewriter:
    """Handles rewriting of author and committer information in git history."""

    def __init__(self, repo: GitRepo):
        self.repo = repo

    def _parse_author_string(self, author_string: str) -> tuple[str, str]:
        """Parse an author string into name and email components.

        Args:
            author_string: String in format "Name <email>"

        Returns:
            Tuple of (name, email)

        Raises:
            ValueError: If string format is invalid
        """
        try:
            name = author_string.split(" <")[0]
            email = author_string.split("<")[1].rstrip(">")
            return name, email
        except IndexError as err:
            raise ValueError(
                "Invalid author string format. Expected 'Name <email>'"
            ) from err

    def rewrite_authors(
        self, mappings: Union[Path, list[AuthorMapping]], update_committer: bool = False
    ) -> None:
        """
        Rewrite author information in the git history using git-filter-repo.

        Args:
            mappings: Either a Path to a JSON file containing the mappings,
                     or a list of AuthorMapping objects
            update_committer: If True, also update committer information
        """
        if isinstance(mappings, Path):
            try:
                with open(mappings, encoding="utf-8") as f:
                    mapping_data = json.load(f)
                mappings = [AuthorMapping(**m) for m in mapping_data]
            except (json.JSONDecodeError, KeyError) as err:
                raise ValueError("Invalid mapping file format") from err

        # Create a temporary mailmap file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".mailmap", delete=False
        ) as f:
            for mapping in mappings:
                new_name, new_email = self._parse_author_string(mapping.new)
                old_name, old_email = self._parse_author_string(mapping.old)
                f.write(f"{new_name} <{new_email}> {old_name} <{old_email}>\n")
            mailmap_path = f.name

        try:
            # Run git-filter-repo with the mailmap
            cmd = ["git-filter-repo", "--mailmap", mailmap_path]
            if update_committer:
                cmd.append("--force")

            subprocess.run(
                cmd,
                cwd=self.repo.path,
                capture_output=True,
                text=True,
                check=True,  # Add check=True to raise CalledProcessError if command fails
            )

        except subprocess.CalledProcessError as err:
            raise RuntimeError(f"git-filter-repo failed: {err.stderr}") from err
        finally:
            # Clean up the temporary mailmap file
            Path(mailmap_path).unlink()

        # No need to manually delete branches - git-filter-repo handles this

    @staticmethod
    def load_mappings(mapping_file: Path) -> list[AuthorMapping]:
        """Load author mappings from a JSON file.

        The JSON file should contain an array of objects with 'old' and 'new' fields,
        each containing author information in the format 'Name <email>'.

        Example JSON:
        [
            {
                "old": "Old Name <old@email.com>",
                "new": "New Name <new@email.com>"
            }
        ]
        """
        if not mapping_file.exists():
            raise FileNotFoundError(f"Mapping file not found: {mapping_file}")

        with mapping_file.open() as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Mapping file must contain a JSON array")

        return [AuthorMapping(old=item["old"], new=item["new"]) for item in data]
