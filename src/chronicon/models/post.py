# ABOUTME: Post data model for Chronicon
# ABOUTME: Represents a single forum post with metadata and content

"""Post model for Discourse posts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


class ValidationError(Exception):
    """Raised when model validation fails."""

    pass


def _parse_datetime(value: Any) -> datetime:
    """Parse a datetime from a string or return as-is if already datetime."""
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


@dataclass
class Post:
    """Represents a single Discourse post."""

    id: int
    topic_id: int
    user_id: int | None
    post_number: int
    created_at: datetime
    updated_at: datetime
    cooked: str | None  # HTML content (can be None for deleted posts)
    raw: str | None  # Markdown content (can be None for deleted posts)
    username: str

    def __post_init__(self):
        """Convert string dates to datetime and validate data."""
        # Convert string dates to datetime if needed
        # (dataclass accepts str at runtime, __post_init__ normalizes to datetime)
        self.created_at = _parse_datetime(self.created_at)
        self.updated_at = _parse_datetime(self.updated_at)
        self.validate()

    def validate(self):
        """
        Validate post data.

        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields are not None
        if self.id is None:
            raise ValidationError("Post id cannot be None")
        if self.topic_id is None:
            raise ValidationError("Post topic_id cannot be None")
        if self.post_number is None:
            raise ValidationError("Post post_number cannot be None")
        if self.created_at is None:
            raise ValidationError("Post created_at cannot be None")
        if self.updated_at is None:
            raise ValidationError("Post updated_at cannot be None")

        # Validate types
        if not isinstance(self.id, int):
            raise ValidationError(f"Post id must be int, got {type(self.id).__name__}")
        if not isinstance(self.topic_id, int):
            raise ValidationError(
                f"Post topic_id must be int, got {type(self.topic_id).__name__}"
            )
        if self.user_id is not None and not isinstance(self.user_id, int):
            raise ValidationError(
                f"Post user_id must be int or None, got {type(self.user_id).__name__}"
            )
        if not isinstance(self.post_number, int):
            raise ValidationError(
                f"Post post_number must be int, got {type(self.post_number).__name__}"
            )
        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                f"Post created_at must be datetime, got "
                f"{type(self.created_at).__name__}"
            )
        if not isinstance(self.updated_at, datetime):
            raise ValidationError(
                f"Post updated_at must be datetime, got "
                f"{type(self.updated_at).__name__}"
            )
        if self.cooked is not None and not isinstance(self.cooked, str):
            raise ValidationError(
                f"Post cooked must be str or None, got {type(self.cooked).__name__}"
            )
        if self.raw is not None and not isinstance(self.raw, str):
            raise ValidationError(
                f"Post raw must be str or None, got {type(self.raw).__name__}"
            )
        if not isinstance(self.username, str):
            raise ValidationError(
                f"Post username must be str, got {type(self.username).__name__}"
            )

        # Validate constraints
        if self.id <= 0:
            raise ValidationError(f"Post id must be positive, got {self.id}")
        if self.topic_id <= 0:
            raise ValidationError(
                f"Post topic_id must be positive, got {self.topic_id}"
            )
        # Allow -1 for system/deleted users
        if self.user_id is not None and (self.user_id == 0 or self.user_id < -1):
            raise ValidationError(
                f"Post user_id must be positive or -1 (system user), got {self.user_id}"
            )
        if self.post_number <= 0:
            raise ValidationError(
                f"Post post_number must be positive, got {self.post_number}"
            )

        # Validate temporal consistency
        if self.updated_at < self.created_at:
            raise ValidationError(
                f"Post updated_at ({self.updated_at}) cannot be before "
                f"created_at ({self.created_at})"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "Post":
        """
        Create a Post instance from a dictionary (API response).

        Args:
            data: Dictionary containing post data

        Returns:
            Post instance

        Raises:
            ValidationError: If required fields are missing or validation fails
            KeyError: If required keys are missing from data
            ValueError: If date parsing fails
        """
        try:
            return cls(
                id=data["id"],
                topic_id=data["topic_id"],
                user_id=data.get("user_id"),
                post_number=data["post_number"],
                created_at=datetime.fromisoformat(
                    data["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    data["updated_at"].replace("Z", "+00:00")
                ),
                cooked=data.get("cooked"),  # Can be None for deleted posts
                raw=data.get("raw"),  # Can be None for deleted posts
                username=data.get("username", ""),
            )
        except KeyError as e:
            raise ValidationError(f"Missing required field in post data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid data format in post: {e}") from e

    def to_dict(self) -> dict:
        """Convert Post to dictionary."""
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "user_id": self.user_id,
            "post_number": self.post_number,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "cooked": self.cooked,
            "raw": self.raw,
            "username": self.username,
        }

    def to_db_row(self) -> tuple:
        """Convert Post to database row tuple."""
        return (
            self.id,
            self.topic_id,
            self.user_id,
            self.post_number,
            self.created_at.isoformat(),
            self.updated_at.isoformat(),
            self.cooked,
            self.raw,
            self.username,
        )
