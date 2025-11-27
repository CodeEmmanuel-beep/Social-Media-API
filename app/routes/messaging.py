from app.models import (
    Chat,
    StandardResponse,
    PaginatedResponse,
)
from app.model_sql import Messaging, User
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from datetime import timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db_session import get_db
from app.auth.verify_jwt import verify_token
from app.log.logger import get_loggers
from sqlalchemy import select, or_, func
import os, shutil, uuid
from werkzeug.utils import secure_filename

router = APIRouter(prefix="/message", tags=["Chat_up"])
logger = get_loggers("chat")


@router.post("/send")
async def text_him(
    message: str | None = None,
    receiver: str | None = None,
    pics: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    user_id = payload.get("user_id")
    username = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=403, detail="not a valid user")
    try:
        stmt = select(User).where(User.username == receiver)
        receive = (await db.execute(stmt)).scalar_one_or_none()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    if not receive:
        raise HTTPException(status_code=404, detail="user not found")
    if pics is not None:
        filename = f"{uuid.uuid4()}_{secure_filename(pics.filename)}"
        file_path = os.path.join("images", filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(pics.file, buffer)
        file_url = f"/images/{filename}"
        pics = file_url
    else:
        pics = None
    if not message and not pics:
        raise HTTPException(status_code=404, detail="can not send empty messages")
    sender = username
    new_message = Messaging(
        user_id=user_id,
        receiver=receiver,
        pics=pics,
        username=sender,
        message=message,
        time_of_chat=datetime.now(timezone.utc),
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    return {"success": f"message successfully sent to {receiver}"}


@router.get(
    "/view",
    response_model=StandardResponse,
    response_model_exclude_none=True,
)
async def view_messages(
    page: int = Query(1, ge=1),
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=403, detail="not a valid user")
    offset = (page - 1) * limit
    conversation_key = func.concat(
        func.least(Messaging.username, Messaging.receiver),
        ":",
        func.greatest(Messaging.username, Messaging.receiver),
    )
    sub = (
        select(conversation_key.label("conversation_id"))
        .where(or_(Messaging.username == username, Messaging.receiver == username))
        .distinct()
        .order_by(conversation_key)
    )
    total = (
        await db.execute(select(func.count()).select_from(sub.subquery()))
    ).scalar()
    ids = (await db.execute(sub.offset(offset).limit(limit))).scalars().all()
    stmt = (
        select(Messaging, conversation_key.label("conversation_id"))
        .where(conversation_key.in_(ids))
        .order_by(Messaging.time_of_chat.desc())
    )
    view = (await db.execute(stmt)).all()
    conversations = {}
    for msg, conv_id in view:
        conversations.setdefault(conv_id, []).append(Chat.model_validate(msg))
    data = {
        "conversations": conversations,
        "pagination": PaginatedResponse(page=page, limit=limit, total=total),
    }

    return StandardResponse(status="success", message="your messages", data=data)


@router.get(
    "/view_one",
    response_model=StandardResponse,
    response_model_exclude_none=True,
)
async def view_messages(
    receiver: str | None = None,
    page: int = Query(5, ge=1),
    limit: int = Query(1, le=100),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_token),
):
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=403, detail="not a valid user")
    offset = (page - 1) * limit
    conversation_key = func.concat(
        func.least(Messaging.username, Messaging.receiver),
        ":",
        func.greatest(Messaging.username, Messaging.receiver),
    )
    stmt = (
        select(Messaging, conversation_key.label("conversation_id"))
        .where(
            or_(
                ((Messaging.username == username) & (Messaging.receiver == receiver)),
                ((Messaging.username == receiver) & (Messaging.receiver == username)),
            )
        )
        .order_by(Messaging.time_of_chat.desc())
    )
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar()
    view = (await db.execute(stmt.offset(offset).limit(limit))).all()
    for msg, _ in view:
        if msg.receiver == username:
            msg.delivered = True
    await db.commit()
    conversations = {}
    for msg, conv_id in view:
        conversations.setdefault(conv_id, []).append(Chat.model_validate(msg))
    data = {
        "conversations": conversations,
        "pagination": PaginatedResponse(page=page, limit=limit, total=total),
    }

    return StandardResponse(status="success", message="your messages", data=data)
