"""Configuration settings and defaults for git-surgeon."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    large_file_threshold: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        gt=0,
        description="Size threshold in bytes for large files",
    )

    # Patterns for sensitive data
    sensitive_patterns: list[str] = Field(
        default_factory=lambda: [
            r"password",
            r"secret",
            r"key",
            r"token",
            r"credential",
        ]
    )

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
    }

    @field_validator("backup_dir")
    @classmethod
    def validate_backup_dir(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate backup directory path."""
        if v is not None and not isinstance(v, Path):
            raise ValueError("backup_dir must be a Path object")
        return v
