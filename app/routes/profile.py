from app.model_sql import (
    Blog,
    User,
    Comment,
    Share,
)
from app.models import (
    Blogger,
    UserResponse,
    Commenter,
    Sharer,
    UserRes,
)
import uuid, os, shutil
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Form,
    File,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db_session import get_db
from app.auth.verify_jwt import verify_token
from app.models import PaginatedMetadata, PaginatedResponse, UserRes
from sqlalchemy import select, func, or_
from app.log.logger import get_loggers
import redis
import json, os
from werkzeug.utils import secure_filename
from sqlalchemy.orm import selectinload
import tracemalloc

tracemalloc.start()


router = APIRouter(prefix="/info", tags=["Profile"])
logger = get_loggers("profile")
redis_client = redis.Redis(host="localhost", port="6379", db=0)


def caching(key: str):
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None


def cached(key: str, value: dict, ttl=6):
    redis_client.set(key, json.dumps(value), ex=ttl)


async def helper_f(
    db: AsyncSession, model, schema, user_id: int, page: int, limit: int
):
    offset = (page - 1) * limit
    total_s = select(func.count()).select_from(model).where(model.user_id == user_id)
    total = (await db.execute(total_s)).scalar() or 0
    stmt = select(model).where(model.user_id == user_id).offset(offset).limit(limit)
    result = (await db.execute(stmt)).scalars().all()
    items = [schema.model_validate(item) for item in result]
    return PaginatedMetadata[schema](
        items=items, pagination=PaginatedResponse(page=page, limit=limit, total=total)
    )


@router.get(
    "/profile",
)
async def view(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    username = payload.get("sub")
    if not user_id:
        logger.warning("User ID missing in token payload")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    cache_key = f"profile:{user_id}:{page}:{limit}"
    cache_d = caching(cache_key)
    if cache_d:
        return {"source": "cached", "data": cache_d}
    stmt = select(User).where(User.username == username)
    user = (await db.execute(stmt)).scalar_one_or_none()
    logger.debug("Fetched user records: %s", user)
    users = UserResponse.model_validate(user)
    counter = await helper_f(db, Comment, Commenter, user_id, page, limit)
    offset = (page - 1) * limit
    stmt = select(Blog).options(selectinload(Blog.comments))

    result = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    if not result:
        return {"No blogs found"}
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar() or 0
    blogs = PaginatedMetadata[Blogger](
        items=[Blogger.model_validate(item) for item in result],
        pagination=PaginatedResponse(page=page, limit=limit, total=total),
    )
    stmt = select(Share).options(selectinload(Share.blog).selectinload(Blog.comments))
    result = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    if not result:
        return {"No shares found"}
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar() or 0
    shar = PaginatedMetadata[Sharer](
        items=[Sharer.model_validate(item) for item in result],
        pagination=PaginatedResponse(page=page, limit=limit, total=total),
    )
    logger.debug("Returning user response: %s", users)
    response = {
        "user": users,
        "blogs": blogs,
        "comments": counter,
        "shares": shar,
    }
    cached(cache_key, response, ttl=600)
    return {"source": "database", "data": response}


@router.get(
    "/search",
)
async def other_users(
    name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    offset = (page - 1) * limit
    username = payload.get("sub")
    if username is None:
        logger.warning("Unauthorized access attempt without username in token")
        raise HTTPException(status_code=403, detail="not a user")
    cached_key = f"profile: {name}:{page}:{limit}"
    cache_d = caching(cached_key)
    if cache_d:
        return {"source": "cache", "data": cache_d}
    if name is not None:
        stmt = select(User).where(
            or_(User.name.ilike(f"%{name}%"), User.username.ilike(f"%{name}%"))
        )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar() or 0
        search = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
        if not search:
            raise HTTPException(status_code=404, detail="user not found")
        logger.info("Found user with id=%s", name)
        found = PaginatedMetadata[UserRes](
            items=[UserRes.model_validate(item) for item in search],
            pagination=PaginatedResponse(page=page, limit=limit, total=total),
        )

        stmt = (
            select(User, Blog)
            .options(selectinload(Blog.comments))
            .join(Blog, User.id == Blog.user_id)
            .where(User.username == username, User.is_active == True)
        )
        total = (
            await db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar() or 0
        logger.info("Blogs found for user %s: %s", username, total)
        stmt = stmt.order_by(Blog.time_of_post.desc())
        blog = (await db.execute(stmt.offset(offset).limit(limit))).all()
        blog_data = PaginatedMetadata[Blogger](
            items=[Blogger.model_validate(item) for _, item in blog],
            pagination=PaginatedResponse(page=page, limit=limit, total=total),
        )
    else:
        raise HTTPException(status_code=404, detail="enter a valid name")
    stmt = (
        select(User, Comment)
        .join(Comment, User.id == Comment.user_id)
        .where(User.username == username)
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar() or 0
    logger.info("Comments found for user %s: %s", username, total)
    stmt = stmt.order_by(Comment.time_of_post.desc())
    com = (await db.execute(stmt.offset(offset).limit(limit))).all()
    comment_data = PaginatedMetadata[Commenter](
        items=[Commenter.model_validate(item) for _, item in com],
        pagination=PaginatedResponse(page=page, limit=limit, total=total),
    )
    stmt = (
        select(User, Share)
        .join(Share, User.id == Share.user_id)
        .where(User.id == username)
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar() or 0
    logger.info("Shares found for user %s: %s", username, total)
    share_d = (await db.execute(stmt.offset(offset).limit(limit))).all()
    share_data = PaginatedMetadata[Sharer](
        pagination=PaginatedResponse(page=page, limit=limit, total=total),
    )
    logger.info("Returning search results for user_id=%s", username)
    response = {
        "user": found,
        "blogs": blog_data,
        "user_comments": comment_data,
        "user_shares": share_data,
    }
    cached(cached_key, response, ttl=600)
    return {"source": "databse", "data": response}


@router.put("/edit_p")
async def profile(
    profile_picture: UploadFile | None = File(None),
    name: str | None = Form(None),
    nationality: str | None = Form(None),
    address: str | None = Form(None),
    age: int | None = Form(None),
    phone_number: float | None = Form(None),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Forbidden access")
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if profile_picture is not None:
        filename = f"{uuid.uuid4()}_{secure_filename(profile_picture.filename)}"
        file_path = os.path.join("images", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(profile_picture.file, buffer)
        file_url = f"/images/{filename}"
        user.profile_picture = file_url
    else:
        user.profile_picture = None
    if nationality is not None:
        user.nationality = nationality
    if name is not None:
        user.name = name
    if address is not None:
        user.address = address
    if age is not None:
        user.age = age
    if phone_number is not None:
        user.phone_number = phone_number
    await db.commit()
    await db.refresh(user)
    return {"message": "profile updated successfully"}
