import math
from datetime import datetime
from typing import Optional, List

from app.models.blog import Post, Comment
from app.schemas.schemas import PostOut, PostSectionOut, CommentOut


def make_initials(name: str) -> str:
    parts = name.strip().split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else name[:2].upper()


def generate_slug(title: str, author_id: str) -> str:
    base   = title.lower().strip().replace(" ", "-")
    base   = "".join(c for c in base if c.isalnum() or c == "-")
    suffix = str(author_id).replace("-", "")[:6]
    return f"{base}-{suffix}"


def estimate_read_time(sections: List) -> str:
    """Estimates read time based on word count across text sections."""
    words = sum(
        len(s.content.split())
        for s in sections
        if s.type in ("paragraph", "heading", "quote")
    )
    minutes = max(1, math.ceil(words / 200))
    return f"{minutes} min read"


def build_post_out(
    post:      Post,
    viewer_id: Optional[str] = None,
    with_body: bool          = False,
) -> PostOut:
    is_liked = None
    if viewer_id:
        is_liked = any(
            str(like.user_id) == viewer_id
            for like in post.post_likes
        )

    body = None
    if with_body:
        body = [
            PostSectionOut(
                type=s.type.value,
                content=s.content,
                caption=s.caption,
                attribution=s.attribution,
            )
            for s in post.sections
        ]

    return PostOut(
        id=str(post.id),
        slug=post.slug,
        image=post.image or "",
        category=post.category.value,
        title=post.title,
        excerpt=post.excerpt,
        author=post.author_name,
        authorInitials=post.author_initials,
        authorBio=post.author_bio,
        readTime=post.read_time or "1 min read",
        publishedAt=post.published_at.isoformat() if post.published_at else "",
        likes=post.likes,
        comments=post.comments,
        isLikedByMe=is_liked,
        tags=post.tags.split(",") if post.tags else [],
        body=body,
    )


def build_comment_out(
    comment:   Comment,
    viewer_id: Optional[str] = None,
) -> CommentOut:
    is_liked = False
    if viewer_id:
        is_liked = any(
            str(like.user_id) == viewer_id
            for like in comment.comment_likes
        )

    return CommentOut(
        id=str(comment.id),
        postId=str(comment.post_id),
        author=comment.author_name,
        authorInitials=comment.author_initials,
        body=comment.body,
        likes=comment.likes,
        isLikedByMe=is_liked,
        createdAt=comment.created_at.isoformat(),
    )