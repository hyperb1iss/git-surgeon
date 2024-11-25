"""Configuration settings and defaults for git-surgeon."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Configuration settings for git-surgeon operations."""

    # Default backup settings
    create_backup: bool = True
    backup_dir: Optional[Path] = None

    # Safety settings
    force: bool = False
    dry_run: bool = False

    # Operation settings
    preserve_recent: bool = False
    selected_branches: list[str] = Field(default_factory=list)

    # Size thresholds (in bytes)
    large_file_threshold: int = 50 * 1024 * 1024  # 50MB

    # Patterns for sensitive data
    sensitive_patterns: list[str] = Field(
        default_factory=lambda: [
            r"password",
            r"secret",
            r"key",
            r"token",
            r"credential"
        ]
    )

    class Config:
        """Pydantic configuration class."""
        arbitrary_types_allowed = True
