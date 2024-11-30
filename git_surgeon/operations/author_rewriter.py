"""Module for rewriting git author and committer information in repository history."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from git_filter_repo import Commit, FastExportParser  # type: ignore

from git_surgeon.core import GitRepo
from git_surgeon.utils.git_filter import run_git_filter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AuthorMapping:
    """Data class representing a mapping between old and new author information."""

    old: str  # Format: "Name <email>"
    new: str  # Format: "Name <email>"


class AuthorRewriter:
    """Handles rewriting of author and committer information in git history."""

    def __init__(self, repo: GitRepo):
        self.repo = repo
        self._changes_made = 0

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
        Rewrite author information in the git history using git-filter-repo internals.

        Args:
            mappings: Either a Path to a JSON file containing the mappings,
                      or a list of AuthorMapping objects
            update_committer: If True, also update committer information

        Raises:
            ValueError: If mapping file format is invalid
            RuntimeError: If git fast-import fails
        """
        if isinstance(mappings, Path):
            try:
                with open(mappings, encoding="utf-8") as f:
                    mapping_data = json.load(f)
                mappings = [AuthorMapping(**m) for m in mapping_data]
            except (json.JSONDecodeError, KeyError) as err:
                raise ValueError("Invalid mapping file format") from err

        # Create a mapping dictionary for quick lookup
        author_map = {
            self._parse_author_string(mapping.old): self._parse_author_string(
                mapping.new
            )
            for mapping in mappings
        }

        logger.info("Author mappings to apply: %s", author_map)

        def commit_callback(commit: Commit, _aux_info: dict) -> None:
            nonlocal author_map
            # Update author information
            author_name, author_email = (
                commit.author_name.decode(),
                commit.author_email.decode(),
            )
            if (author_name, author_email) in author_map:
                new_name, new_email = author_map[(author_name, author_email)]
                logger.debug(
                    "Rewriting author in commit %s: %s <%s> -> %s <%s>",
                    commit.id,
                    author_name,
                    author_email,
                    new_name,
                    new_email,
                )
                commit.author_name = new_name.encode()
                commit.author_email = new_email.encode()
                self._changes_made += 1

            # Optionally update committer information
            if update_committer:
                committer_name, committer_email = (
                    commit.committer_name.decode(),
                    commit.committer_email.decode(),
                )
                if (committer_name, committer_email) in author_map:
                    new_name, new_email = author_map[(committer_name, committer_email)]
                    logger.debug(
                        "Rewriting committer in commit %s: %s <%s> -> %s <%s>",
                        commit.id,
                        committer_name,
                        committer_email,
                        new_name,
                        new_email,
                    )
                    commit.committer_name = new_name.encode()
                    commit.committer_email = new_email.encode()
                    self._changes_made += 1

        # Create output file for fast-import
        output_path = self.repo.path / "filtered_history"

        # Create parser with callback
        parser = FastExportParser(commit_callback=commit_callback)

        # Run the filter operation
        run_git_filter(self.repo.path, parser, temp_file=output_path)

        if self._changes_made == 0:
            logger.warning(
                "No changes were made. Check if the author information matches exactly."
            )
        else:
            logger.info(
                "Successfully processed %d author/committer entries", self._changes_made
            )

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
