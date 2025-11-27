from sqlalchemy.ext.asyncio import AsyncSession
from app.model_sql import React, Blog, Comment, ReactionType
from app.log.logger import get_loggers
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timezone, datetime
from app.core.db_session import get_db
from app.auth.verify_jwt import verify_token
from sqlalchemy import select
from app.models import StandardResponse

router = APIRouter(prefix="/react", tags=["Reactions"])
logger = get_loggers("react")


@router.post("/react")
async def react_type(
    reaction_type: str,
    blog: str | None = None,
    comment: str | None = None,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    if not user_id:
        logger.warning("Unauthorized reaction attempt")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        reaction_enum = ReactionType(reaction_type)
    except ValueError:
        logger.warning(f"Invalid reaction type '{reaction_type}' by user {user_id}")
        raise HTTPException(status_code=400, detail="invalid reaction type")
    if (blog is None and comment is None) or (blog is not None and comment is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="must input one reaction"
        )
    if blog:
        target = await db.get(Blog, blog)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="must react on existing blog(s)",
            )
    if comment:
        target = await db.get(Comment, comment)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="must react on existing comment(s)",
            )
    stmt = select(React).where(React.user_id == user_id)
    if blog:
        stmt = stmt.where(React.blog_id == blog)
    if comment:
        stmt = stmt.where(React.comment_id == comment)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        existing.type = reaction_enum
        existing.time_of_reaction = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        logger.info(f"User {user_id} updated reaction {existing.id}")
        return {"message": "Reaction updated", "reaction": existing.type}

    new_react = React(
        user_id=user_id,
        type=reaction_enum,
        blog_id=blog,
        comment_id=comment,
        time_of_reaction=datetime.now(timezone.utc),
    )
    if blog:
        target.reacts_count = (target.reacts_count or 0) + 1
    if comment:
        target.reacts_count = (target.reacts_count or 0) + 1
    db.add(new_react)
    await db.commit()
    await db.refresh(new_react)
    logger.info(f"User {user_id} added new reaction {new_react.id}")
    return {"message": "Reaction added", "reaction": new_react.id}


@router.delete("/erase", response_model=StandardResponse)
async def delete_one(
    react_id: int,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    username = payload.get("sub")
    if not user_id:
        logger.warning("Unauthorized delete attempt detected (no user_id in payload)")
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    stmt = select(React).where(React.user_id == user_id, React.id == react_id)
    data = (await db.execute(stmt)).scalar_one_or_none()
    if not data:
        return {"status": "no data", "message": "invalid field"}
    react = await db.get(Blog, data.blog_id)
    if not react:
        return "invalid"
    react.reacts_count = max((react.reacts_count or 1) - 1, 0)
    await db.delete(data)
    await db.commit()
    logger.info("delete_one endpoint completed successfully")
    return {"status": "success", "message": "react successfully deleted"}
