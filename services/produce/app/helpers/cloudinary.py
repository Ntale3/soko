import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB   = 5


async def upload_listing_image(
    file: UploadFile,
    listing_id: str,
    order: int
) -> dict:
    """
    Uploads image to Cloudinary.
    Returns dict with { url, public_id }.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename} must be jpeg, png or webp"
        )

    contents = await file.read()

    if len(contents) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename} exceeds {MAX_SIZE_MB}MB limit"
        )

    try:
        result = cloudinary.uploader.upload(
            contents,
            folder=f"soko/listings/{listing_id}",
            public_id=f"image_{order}",
            overwrite=True,
            transformation=[
                {
                    "width":        1200,
                    "height":       900,
                    "crop":         "limit",
                    "quality":      "auto:good",
                    "fetch_format": "auto",
                }
            ],
            eager=[
                {
                    "width":        400,
                    "height":       300,
                    "crop":         "fill",
                    "gravity":      "auto",
                    "quality":      "auto",
                    "fetch_format": "auto",
                }
            ],
            eager_async=True,
        )
        return {
            "url":       result["secure_url"],
            "public_id": result["public_id"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")


def delete_cloudinary_image(public_id: str):
    """Deletes a single image from Cloudinary by public_id."""
    try:
        cloudinary.uploader.destroy(public_id, invalidate=True)
    except Exception:
        pass   # don't block DB operations if Cloudinary fails