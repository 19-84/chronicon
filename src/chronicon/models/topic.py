# ABOUTME: Topic data model for Chronicon
# ABOUTME: Represents a forum topic (thread) with metadata

"""Topic model for Discourse topics."""

from dataclasses import dataclass, field
from datetime import datetime


class ValidationError(Exception):
    """Raised when model validation fails."""

    pass


@dataclass
class Topic:
    """Represents a Discourse topic (thread)."""

    # Core fields (required)
    id: int
    title: str
    slug: str
    created_at: datetime
    posts_count: int
    views: int

    # Core fields (optional)
    category_id: int | None = None
    user_id: int | None = None
    updated_at: datetime | None = None

    # Content & Discovery
    tags: list[str] = field(default_factory=list)
    excerpt: str | None = None
    image_url: str | None = None
    fancy_title: str | None = None

    # Engagement Metrics
    like_count: int = 0
    reply_count: int = 0
    highest_post_number: int = 0
    participant_count: int = 0
    word_count: int = 0

    # Status & Classification
    pinned: bool = False
    pinned_globally: bool = False
    closed: bool = False
    archived: bool = False

    # Context & Metadata
    featured_link: str | None = None
    has_accepted_answer: bool = False
    has_summary: bool = False
    visible: bool = True
    last_posted_at: datetime | None = None
    thumbnails: dict | None = None
    bookmarked: bool = False

    def __post_init__(self):
        """Convert string dates to datetime and validate data."""
        # Convert string dates to datetime if needed
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(
                self.created_at.replace("Z", "+00:00")
            )
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(
                self.updated_at.replace("Z", "+00:00")
            )
        if isinstance(self.last_posted_at, str):
            self.last_posted_at = datetime.fromisoformat(
                self.last_posted_at.replace("Z", "+00:00")
            )
        self.validate()

    def validate(self):
        """
        Validate topic data.

        Raises:
            ValidationError: If validation fails
        """
        # Validate required fields are not None
        if self.id is None:
            raise ValidationError("Topic id cannot be None")
        if self.title is None:
            raise ValidationError("Topic title cannot be None")
        if self.slug is None:
            raise ValidationError("Topic slug cannot be None")
        if self.created_at is None:
            raise ValidationError("Topic created_at cannot be None")
        if self.posts_count is None:
            raise ValidationError("Topic posts_count cannot be None")
        if self.views is None:
            raise ValidationError("Topic views cannot be None")

        # Validate types
        if not isinstance(self.id, int):
            raise ValidationError(f"Topic id must be int, got {type(self.id).__name__}")
        if not isinstance(self.title, str):
            raise ValidationError(
                f"Topic title must be str, got {type(self.title).__name__}"
            )
        if not isinstance(self.slug, str):
            raise ValidationError(
                f"Topic slug must be str, got {type(self.slug).__name__}"
            )
        if self.category_id is not None and not isinstance(self.category_id, int):
            raise ValidationError(
                "Topic category_id must be int or None, got "
                f"{type(self.category_id).__name__}"
            )
        if self.user_id is not None and not isinstance(self.user_id, int):
            raise ValidationError(
                f"Topic user_id must be int or None, got {type(self.user_id).__name__}"
            )
        if not isinstance(self.created_at, datetime):
            raise ValidationError(
                "Topic created_at must be datetime, got "
                f"{type(self.created_at).__name__}"
            )
        if self.updated_at is not None and not isinstance(self.updated_at, datetime):
            raise ValidationError(
                "Topic updated_at must be datetime or None, got "
                f"{type(self.updated_at).__name__}"
            )
        if not isinstance(self.posts_count, int):
            raise ValidationError(
                f"Topic posts_count must be int, got {type(self.posts_count).__name__}"
            )
        if not isinstance(self.views, int):
            raise ValidationError(
                f"Topic views must be int, got {type(self.views).__name__}"
            )

        # Validate constraints
        if self.id <= 0:
            raise ValidationError(f"Topic id must be positive, got {self.id}")
        if self.category_id is not None and self.category_id <= 0:
            raise ValidationError(
                f"Topic category_id must be positive, got {self.category_id}"
            )
        if self.user_id is not None and self.user_id <= 0:
            raise ValidationError(f"Topic user_id must be positive, got {self.user_id}")
        if self.posts_count < 0:
            raise ValidationError(
                f"Topic posts_count must be non-negative, got {self.posts_count}"
            )
        if self.views < 0:
            raise ValidationError(f"Topic views must be non-negative, got {self.views}")

        # Validate string constraints
        if len(self.title.strip()) == 0:
            raise ValidationError("Topic title cannot be empty")
        if len(self.slug.strip()) == 0:
            raise ValidationError("Topic slug cannot be empty")

        # Validate temporal consistency
        if self.updated_at is not None and self.updated_at < self.created_at:
            raise ValidationError(
                f"Topic updated_at ({self.updated_at}) cannot be before "
                f"created_at ({self.created_at})"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "Topic":
        """
        Create a Topic instance from a dictionary (API response).

        Args:
            data: Dictionary containing topic data

        Returns:
            Topic instance

        Raises:
            ValidationError: If required fields are missing or validation fails
            KeyError: If required keys are missing from data
            ValueError: If date parsing fails
        """
        try:
            updated_at = data.get("updated_at")
            last_posted_at = data.get("last_posted_at")

            return cls(
                # Core fields
                id=data["id"],
                title=data["title"],
                slug=data["slug"],
                category_id=data.get("category_id"),
                user_id=data.get("user_id"),
                created_at=datetime.fromisoformat(
                    data["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if updated_at
                else None,
                posts_count=data.get("posts_count", 0),
                views=data.get("views", 0),
                # Content & Discovery - extract tag names if tags are dicts
                tags=[
                    t["name"] if isinstance(t, dict) else t
                    for t in data.get("tags", [])
                ],
                excerpt=data.get("excerpt"),
                image_url=data.get("image_url"),
                fancy_title=data.get("fancy_title"),
                # Engagement Metrics
                like_count=data.get("like_count", 0),
                reply_count=data.get("reply_count", 0),
                highest_post_number=data.get("highest_post_number", 0),
                participant_count=data.get("participant_count", 0),
                word_count=data.get("word_count", 0),
                # Status & Classification
                pinned=data.get("pinned", False),
                pinned_globally=data.get("pinned_globally", False),
                closed=data.get("closed", False),
                archived=data.get("archived", False),
                # Context & Metadata
                featured_link=data.get("featured_link"),
                has_accepted_answer=data.get("has_accepted_answer", False),
                has_summary=data.get("has_summary", False),
                visible=data.get("visible", True),
                last_posted_at=datetime.fromisoformat(
                    last_posted_at.replace("Z", "+00:00")
                )
                if last_posted_at
                else None,
                thumbnails=data.get("thumbnails"),
                bookmarked=data.get("bookmarked", False),
            )
        except KeyError as e:
            raise ValidationError(f"Missing required field in topic data: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid data format in topic: {e}") from e

    def to_dict(self) -> dict:
        """Convert Topic to dictionary."""
        return {
            # Core fields
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "category_id": self.category_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "posts_count": self.posts_count,
            "views": self.views,
            # Content & Discovery
            "tags": self.tags,
            "excerpt": self.excerpt,
            "image_url": self.image_url,
            "fancy_title": self.fancy_title,
            # Engagement Metrics
            "like_count": self.like_count,
            "reply_count": self.reply_count,
            "highest_post_number": self.highest_post_number,
            "participant_count": self.participant_count,
            "word_count": self.word_count,
            # Status & Classification
            "pinned": self.pinned,
            "pinned_globally": self.pinned_globally,
            "closed": self.closed,
            "archived": self.archived,
            # Context & Metadata
            "featured_link": self.featured_link,
            "has_accepted_answer": self.has_accepted_answer,
            "has_summary": self.has_summary,
            "visible": self.visible,
            "last_posted_at": self.last_posted_at.isoformat()
            if self.last_posted_at
            else None,
            "thumbnails": self.thumbnails,
            "bookmarked": self.bookmarked,
        }

    def to_db_row(self) -> tuple:
        """
        Convert Topic to database row tuple.

        Returns:
            Tuple of all topic fields in database column order
        """
        import json

        return (
            # Core fields
            self.id,
            self.title,
            self.slug,
            self.category_id,
            self.user_id,
            self.created_at.isoformat(),
            self.updated_at.isoformat() if self.updated_at else None,
            self.posts_count,
            self.views,
            # Content & Discovery
            json.dumps(self.tags) if self.tags else None,
            self.excerpt,
            self.image_url,
            self.fancy_title,
            # Engagement Metrics
            self.like_count,
            self.reply_count,
            self.highest_post_number,
            self.participant_count,
            self.word_count,
            # Status & Classification (bool -> int for SQLite)
            1 if self.pinned else 0,
            1 if self.pinned_globally else 0,
            1 if self.closed else 0,
            1 if self.archived else 0,
            # Context & Metadata
            self.featured_link,
            1 if self.has_accepted_answer else 0,
            1 if self.has_summary else 0,
            1 if self.visible else 0,
            self.last_posted_at.isoformat() if self.last_posted_at else None,
            json.dumps(self.thumbnails) if self.thumbnails else None,
            1 if self.bookmarked else 0,
        )
