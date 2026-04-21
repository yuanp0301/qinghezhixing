import asyncio
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.oss import storage
from app.schemas.content import ContentDetail
from app.services import contents as cs
from app.services.audit import write_audit
from app.services.upload_validation import (
    UploadValidationError,
    validate_html_upload,
)

settings = get_settings()
router = APIRouter(prefix="/api/contents", tags=["contents"])


def _build_object_key(now: datetime) -> str:
    return f"contents/{now:%Y}/{now:%m}/{uuid.uuid4().hex}.html"


@router.post(
    "",
    response_model=ContentDetail,
    status_code=201,
    dependencies=[Depends(require_role("creator", "admin"))],
)
async def upload_content(
    title: str = Form(min_length=1, max_length=100),
    description: str | None = Form(default=None, max_length=500),
    tags: list[str] = Form(default=[]),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContentDetail:
    if len(tags) > 10:
        raise HTTPException(422, "too many tags (max 10)")

    try:
        info = validate_html_upload(
            filename=file.filename or "",
            content_type=file.content_type or "",
            stream=file.file,
            max_bytes=settings.upload_max_bytes,
        )
    except UploadValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    object_key = _build_object_key(datetime.utcnow())
    file.file.seek(0)
    try:
        await asyncio.to_thread(
            storage.put_object, object_key, file.file, "text/html"
        )
    except Exception as e:
        raise HTTPException(502, f"upload to storage failed: {e}") from e

    try:
        c = await cs.create_content(
            db,
            uploader_id=user.id,
            title=title,
            description=description,
            oss_bucket=settings.oss_bucket,
            oss_object_key=object_key,
            original_filename=file.filename or "untitled.html",
            content_type="text/html",
            size_bytes=info.size,
            sha256=info.sha256,
            tag_names=tags,
        )
        await write_audit(
            db, actor_id=user.id, action="content.create",
            target_type="content", target_id=c.id,
            detail={"size": info.size, "sha256": info.sha256},
        )
        await db.commit()
    except Exception:
        await asyncio.to_thread(storage.delete_object, object_key)
        raise

    # Reload with tags eagerly loaded (post-commit attributes are expired).
    c = await cs.get_active(db, c.id)
    summary = await cs.to_summary_dict(db, c)
    return ContentDetail(
        **summary,
        description=c.description,
        original_filename=c.original_filename,
        content_type=c.content_type,
        sha256=c.sha256,
        visibility=c.visibility,
        status=c.status,
    )
