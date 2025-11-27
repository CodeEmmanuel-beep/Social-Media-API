from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    DateTime,
    String,
    Float,
    ForeignKey,
    UniqueConstraint,
    Enum as SQLEnum,
    Date,
    Table,
)
from enum import Enum
from app.core.declarative import Base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta


def current_utc_time():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String)
    username = Column(String)
    password = Column(String)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    age = Column(Integer)
    nationality = Column(String)
    phone_number = Column(String)
    address = Column(String)
    profile_picture = Column(String, nullable=True)

    blogs = relationship("Blog", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    reacts = relationship("React", back_populates="user")
    shares = relationship("Share", back_populates="user")
    messages = relationship("Messaging", back_populates="user")
    group_admins = relationship("GroupAdmin", back_populates="user")
    members = relationship("Member", back_populates="user")


class Messaging(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    receiver = Column(String)
    username = Column(String)
    message = Column(String, nullable=True)
    pics = Column(String, nullable=True)
    delivered = Column(Boolean, default=False)
    time_of_chat = Column(DateTime(timezone=True), default=current_utc_time)
    user = relationship("User", back_populates="messages")


class GroupAdmin(Base):
    __tablename__ = "group_admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    role = Column(String, default="admin")

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="unique_group_admin"),
    )

    user = relationship("User", back_populates="group_admins")
    group = relationship("Group", back_populates="admins")


class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="unique_member_constraint"),
    )

    user = relationship("User", back_populates="members")
    group = relationship("Group", back_populates="members")
    group_tasks = relationship(
        "GroupTask", secondary=group_task_members, back_populates="members"
    )


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

    contributions = relationship("Contribute", back_populates="group")
    admins = relationship("GroupAdmin", back_populates="group")
    members = relationship("Member", back_populates="group")
    group_tasks = relationship("GroupTask", back_populates="group")


class Blog(Base):
    __tablename__ = "blogs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(String)
    comments_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    reacts_count = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"))
    time_of_post = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    comments = relationship("Comment", back_populates="blog")
    user = relationship("User", back_populates="blogs")
    react = relationship("React", back_populates="blog")
    shares = relationship("Share", back_populates="blog")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    like = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    blog_id = Column(Integer, ForeignKey("blogs.id"))
    reacts_count = Column(Integer, default=0)
    time_of_post = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    blog = relationship("Blog", back_populates="comments")
    user = relationship("User", back_populates="comments")
    react = relationship("React", back_populates="comment")


class ReactionType(str, Enum):
    like = "like"
    love = "love"
    angry = "angry"
    laugh = "laugh"
    wow = "wow"
    sad = "sad"


class React(Base):
    __tablename__ = "reacts"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(ReactionType), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    blog_id = Column(Integer, ForeignKey("blogs.id"))
    comment_id = Column(Integer, ForeignKey("comments.id"))
    time_of_reaction = Column(DateTime(timezone=True), default=current_utc_time)
    __table_args__ = (
        UniqueConstraint("user_id", "blog_id", name="unique_blog_react"),
        UniqueConstraint("user_id", "comment_id", name="unique_comment_react"),
    )
    comment = relationship("Comment", back_populates="react")
    blog = relationship("Blog", back_populates="react")
    user = relationship("User", back_populates="reacts")


class ShareType(str, Enum):
    love = "love"
    angry = "angry"
    laugh = "laugh"
    wow = "wow"
    sad = "sad"


class Share(Base):
    __tablename__ = "shares"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    blog_id = Column(Integer, ForeignKey("blogs.id"))
    content = Column(String)
    type = Column(SQLEnum(ShareType), nullable=True)
    time_of_share = Column(DateTime(timezone=True), default=current_utc_time)

    user = relationship("User", back_populates="shares")
    blog = relationship("Blog", back_populates="shares")
