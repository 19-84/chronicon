# ABOUTME: Category data model for Chronicon
# ABOUTME: Represents a forum category with styling and hierarchy

"""Category model for Discourse categories."""

import re
from dataclasses import dataclass


class ValidationError(Exception):
    """Raised when model validation fails."""

    pass


@dataclass
class Category:
    """Represents a Discourse category."""

    id: int
    name: str
    slug: str
    color: str
    text_color: str
    description: str | None = None
    parent_category_id: int | None = None
    topic_count: int = 0

    def __post_init__(self):
        """Validate data after initialization."""
        self.validate()

    def validate(self):
        """
        Validate category data.

        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields are not None
        if self.id is None:
            raise ValidationError("Category id cannot be None")
        if self.name is None:
            raise ValidationError("Category name cannot be None")
        if self.slug is None:
            raise ValidationError("Category slug cannot be None")
        if self.color is None:
            raise ValidationError("Category color cannot be None")
        if self.text_color is None:
            raise ValidationError("Category text_color cannot be None")
        if self.topic_count is None:
            raise ValidationError("Category topic_count cannot be None")

        # Validate types
        if not isinstance(self.id, int):
            raise ValidationError(
                f"Category id must be int, got {type(self.id).__name__}"
            )
        if not isinstance(self.name, str):
            raise ValidationError(
                f"Category name must be str, got {type(self.name).__name__}"
            )
        if not isinstance(self.slug, str):
            raise ValidationError(
                f"Category slug must be str, got {type(self.slug).__name__}"
            )
        if not isinstance(self.color, str):
            raise ValidationError(
                f"Category color must be str, got {type(self.color).__name__}"
            )
        if not isinstance(self.text_color, str):
            raise ValidationError(
                f"Category text_color must be str, got {type(self.text_color).__name__}"
            )
        if self.description is not None and not isinstance(self.description, str):
            raise ValidationError(
                "Category description must be str or None, got "
                f"{type(self.description).__name__}"
            )
        if self.parent_category_id is not None and not isinstance(
            self.parent_category_id, int
        ):
            raise ValidationError(
                "Category parent_category_id must be int or None, got "
                f"{type(self.parent_category_id).__name__}"
            )
        if not isinstance(self.topic_count, int):
            raise ValidationError(
                "Category topic_count must be int, got "
                f"{type(self.topic_count).__name__}"
            )

        # Validate constraints
        if self.id <= 0:
            raise ValidationError(f"Category id must be positive, got {self.id}")
        if len(self.name.strip()) == 0:
            raise ValidationError("Category name cannot be empty")
        if len(self.slug.strip()) == 0:
            raise ValidationError("Category slug cannot be empty")
        if self.parent_category_id is not None and self.parent_category_id <= 0:
            raise ValidationError(
                "Category parent_category_id must be positive, got "
                f"{self.parent_category_id}"
            )
        if self.topic_count < 0:
            raise ValidationError(
                f"Category topic_count must be non-negative, got {self.topic_count}"
            )

        # Validate color format (hex color without #)
        # Supports both 3 and 6 digit formats
        hex_pattern = re.compile(r"^[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$")
        if not hex_pattern.match(self.color):
            raise ValidationError(
                "Category color must be 3 or 6-digit hex color (without #), "
                f"got {self.color}"
            )
        if not hex_pattern.match(self.text_color):
            raise ValidationError(
                "Category text_color must be 3 or 6-digit hex color "
                f"(without #), got {self.text_color}"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        """
        Create a Category instance from a dictionary (API response).

        Args:
            data: Dictionary containing category data

        Returns:
            Category instance

        Raises:
            ValidationError: If required fields are missing or validation fails
            KeyError: If required keys are missing from data
        """
        try:
            return cls(
                id=data["id"],
                name=data["name"],
                slug=data["slug"],
                color=data.get("color", "000000"),
                text_color=data.get("text_color", "FFFFFF"),
                description=data.get("description"),
                parent_category_id=data.get("parent_category_id"),
                topic_count=data.get("topic_count", 0),
            )
        except KeyError as e:
            raise ValidationError(
                f"Missing required field in category data: {e}"
            ) from e
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid data format in category: {e}") from e

    def to_dict(self) -> dict:
        """Convert Category to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "color": self.color,
            "text_color": self.text_color,
            "description": self.description,
            "parent_category_id": self.parent_category_id,
            "topic_count": self.topic_count,
        }

    def to_db_row(self) -> tuple:
        """
        Convert Category to database row tuple.

        Returns:
            Tuple of category fields in database column order
        """
        return (
            self.id,
            self.name,
            self.slug,
            self.color,
            self.text_color,
            self.description,
            self.parent_category_id,
            self.topic_count,
        )
