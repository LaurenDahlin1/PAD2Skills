"""Configuration management for PAD2Skills project."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class PathsConfig(BaseModel):
    """Paths to data directories."""

    raw_pdfs: Path = Field(..., description="Directory containing raw PDF files")
    markdown: Path = Field(..., description="Directory for converted markdown files")

    @field_validator("raw_pdfs", "markdown", mode="before")
    @classmethod
    def convert_to_path(cls, v):
        """Convert string paths to Path objects."""
        return Path(v)


class Config(BaseModel):
    """Main configuration for PAD2Skills project."""

    paths: PathsConfig


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load and validate configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to configs/base.yaml

    Returns:
        Validated Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValidationError: If config structure is invalid
    """
    if config_path is None:
        # Default to configs/base.yaml relative to project root
        project_root = Path(__file__).parent.parent
        config_path = project_root / "configs" / "base.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config_dict = yaml.safe_load(f)

    return Config(**config_dict)
