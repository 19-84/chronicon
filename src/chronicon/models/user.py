# ABOUTME: User data model for Chronicon
# ABOUTME: Represents a forum user with profile information

"""User model for Discourse users."""

from dataclasses import dataclass
from datetime import datetime


class ValidationError(Exception):
    """Raised when model validation fails."""

    pass


@dataclass
class User:
    """Represents a Discourse user."""

    id: int
    username: str
    name: str | None
    avatar_template: str
    trust_level: int
    created_at: datetime | None
    local_avatar_path: str | None = None

    def __post_init__(self):
        """Convert string dates to datetime and validate data."""
        # Convert string dates to datetime if needed
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(
                self.created_at.replace("Z", "+00:00")
            )
        self.validate()

    def validate(self):
        """
        Validate user data.

        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields are not None
        if self.id is None:
            raise ValidationError("User id cannot be None")
        if self.username is None:
            raise ValidationError("User username cannot be None")
        if self.avatar_template is None:
            raise ValidationError("User avatar_template cannot be None")
        if self.trust_level is None:
            raise ValidationError("User trust_level cannot be None")

        # Validate types
        if not isinstance(self.id, int):
            raise ValidationError(f"User id must be int, got {type(self.id).__name__}")
        if not isinstance(self.username, str):
            raise ValidationError(
                f"User username must be str, got {type(self.username).__name__}"
            )
        if self.name is not None and not isinstance(self.name, str):
            raise ValidationError(
                f"User name must be str or None, got {type(self.name).__name__}"
            )
        if not isinstance(self.avatar_template, str):
            raise ValidationError(
                f"User avatar_template must be str, got "
                f"{type(self.avatar_template).__name__}"
            )
        if not isinstance(self.trust_level, int):
            raise ValidationError(
                f"User trust_level must be int, got {type(self.trust_level).__name__}"
            )
        if self.created_at is not None and not isinstance(self.created_at, datetime):
            raise ValidationError(
                f"User created_at must be datetime or None, got "
                f"{type(self.created_at).__name__}"
            )
        if self.local_avatar_path is not None and not isinstance(
            self.local_avatar_path, str
        ):
            raise ValidationError(
                f"User local_avatar_path must be str or None, got "
                f"{type(self.local_avatar_path).__name__}"
            )

        # Validate constraints (allow -1 for system/deleted users)
        if self.id == 0 or self.id < -1:
            raise ValidationError(
                f"User id must be positive or -1 (system user), got {self.id}"
            )
        if len(self.username.strip()) == 0:
            raise ValidationError("User username cannot be empty")
        if self.trust_level < 0 or self.trust_level > 4:
            raise ValidationError(
                f"User trust_level must be between 0 and 4, got {self.trust_level}"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """
        Create a User instance from a dictionary (API response).

        Args:
            data: Dictionary containing user data

        Returns:
            User instance

        Raises:
            ValidationError: If required fields are missing or validation fails
            KeyError: If required keys are missing from data
            ValueError: If date parsing fails
        """
        try:
            created_at = data.get("created_at")
            return cls(
                id=data["id"],
                username=data["username"],
                name=data.get("name"),
                avatar_template=data.get("avatar_template", ""),
                trust_level=data.get("trust_level", 0),
                created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_at
                else None,
                local_avatar_path=data.get("local_avatar_path"),
            )
        except KeyError as e:
            raise ValidationError(f"Missing required field in user data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid data format in user: {e}") from e

    def to_dict(self) -> dict:
        """Convert User to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "avatar_template": self.avatar_template,
            "trust_level": self.trust_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "local_avatar_path": self.local_avatar_path,
        }

    def get_avatar_url(self, size: int = 48) -> str:
        """Generate avatar URL for a specific size."""
        if not self.avatar_template:
            return ""
        # Replace {size} placeholder with actual size
        return self.avatar_template.replace("{size}", str(size))
