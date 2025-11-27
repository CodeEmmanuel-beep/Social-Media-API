from sqlalchemy.ext.asyncio import AsyncSession
from app.model_sql import Blog, Share, ShareType
from app.log.logger import get_loggers
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import timezone, datetime
from app.core.db_session import get_db
from app.auth.verify_jwt import verify_token
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models import PaginatedResponse, Sharer, StandardResponse, PaginatedMetadata

router = APIRouter(prefix="/sharing", tags=["Share"])
logger = get_loggers("share")


@router.post("/share")
async def sharing(
    blog_id: int,
    content: str,
    react_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    if not user_id:
        logger.warning("Forbidden: user_id missing in payload")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    share_emu = None
    if react_type:
        try:
            share_emu = ShareType(react_type)
            logger.info("Share type parsed: %s", share_emu)
        except ValueError:
            logger.error("Invalid share type: %s", react_type)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="input a valid reaction"
            )
    blog = await db.get(Blog, blog_id)
    if not blog:
        logger.error("Blog not found. blog_id: %s", blog_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    new_share = Share(
        user_id=user_id,
        type=share_emu,
        content=content,
        blog_id=blog_id,
        time_of_share=datetime.now(timezone.utc),
    )
    blog.share_count = (blog.share_count or 0) + 1
    db.add(new_share)
    await db.commit()
    await db.refresh(new_share)
    logger.info("New share created. share_id: %s, user_id: %s", new_share.id, user_id)
    return "blog shared"


@router.get(
    "/view_shares",
    response_model=StandardResponse[PaginatedMetadata[Sharer]],
    response_model_exclude_none=True,
)
async def views(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=100),
    session: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    offset = (page - 1) * limit
    stmt = select(Share).options(selectinload(Share.blog).selectinload(Blog.comments))

    result = (await session.execute(stmt.offset(offset).limit(limit))).scalars().all()
    if not result:
        return StandardResponse(status="success", message="No shares found")
    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar() or 0
    data = PaginatedMetadata[Sharer](
        items=[Sharer.model_validate(item) for item in result],
        pagination=PaginatedResponse(page=page, limit=limit, total=total),
    )
    return StandardResponse(status="success", message="your shared blogs", data=data)


@router.get("/view_a_particular_share", response_model=StandardResponse)
async def view(
    share_id: int,
    session: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    stmt = (
        select(Share)
        .where(Share.id == share_id)
        .options(selectinload(Share.blog).selectinload(Blog.comments))
    )
    result = (await session.execute(stmt)).scalar_one_or_none()
    if not result:
        return StandardResponse(status="error", message="invalid share_id")
    data = Sharer.model_validate(result)
    return StandardResponse(status="success", message="your shared blogs", data=data)


@router.delete("/erase", response_model=StandardResponse)
async def delete_one(
    share_id: int,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    username = payload.get("sub")
    if not user_id:
        logger.warning("Unauthorized delete attempt detected (no user_id in payload)")
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    stmt = select(Share).where(Share.user_id == user_id, Share.id == share_id)
    data = (await db.execute(stmt)).scalar_one_or_none()
    if not data:
        return {"status": "no data", "message": "invalid field"}
    sharer = await db.get(Blog, data.blog_id)
    sharer.share_count = max((sharer.share_count or 1) - 1, 0)
    await db.delete(data)
    await db.commit()
    logger.info("delete_one endpoint completed successfully")
    return {
        "status": "success",
        "message": "section successfully deleted",
        "data": {
            "id": data.id,
            "user": username,
        },
    }
