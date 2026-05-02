from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    github_id = Column(String, unique=True, index=True)
    username = Column(String, index=True)
    email = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    model_selections = relationship("ModelSelection", back_populates="user")


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True)
    owner = Column(String, index=True)
    repo = Column(String, index=True)
    branch = Column(String, default="main")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    threads = relationship("Thread", back_populates="workspace")
    code_chunks = relationship("CodeChunk", back_populates="workspace")
    workspace_memories = relationship("WorkspaceMemory", back_populates="workspace")
    background_tasks = relationship("BackgroundTask", back_populates="workspace")
    skills = relationship("Skill", back_populates="workspace")

    __table_args__ = (
        Index("ix_workspaces_owner_repo", "owner", "repo"),
    )


class Thread(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), index=True)
    title = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    workspace = relationship("Workspace", back_populates="threads")
    messages = relationship("Message", back_populates="thread")
    action_history = relationship("ActionHistory", back_populates="thread")
    pending_changes = relationship("PendingChange", back_populates="thread")
    agent_logs = relationship("AgentLog", back_populates="thread")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), index=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    thread = relationship("Thread", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_thread_created", "thread_id", "created_at"),
    )


class CodeChunk(Base):
    __tablename__ = "code_chunks"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), index=True)
    file_path = Column(String, index=True)
    content = Column(Text)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    workspace = relationship("Workspace", back_populates="code_chunks")


class WorkspaceMemory(Base):
    __tablename__ = "workspace_memories"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), index=True)
    key = Column(String, index=True)
    value = Column(Text)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    workspace = relationship("Workspace", back_populates="workspace_memories")

    __table_args__ = (
        Index("ix_workspace_memories_workspace_key", "workspace_id", "key"),
    )


class ActionHistory(Base):
    __tablename__ = "action_history"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), index=True)
    action_type = Column(String, index=True)
    file_path = Column(String, nullable=True)
    content_before = Column(Text, nullable=True)
    content_after = Column(Text, nullable=True)
    command = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    thread = relationship("Thread", back_populates="action_history")

    __table_args__ = (
        Index("ix_action_history_thread_created", "thread_id", "created_at"),
    )


class PendingChange(Base):
    __tablename__ = "pending_changes"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), index=True)
    file_path = Column(String, index=True)
    diff = Column(Text)
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    thread = relationship("Thread", back_populates="pending_changes")

    __table_args__ = (
        Index("ix_pending_changes_thread_status", "thread_id", "status"),
    )


class ModelSelection(Base):
    __tablename__ = "model_selections"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    provider = Column(String, index=True)
    model_name = Column(String, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="model_selections")

    __table_args__ = (
        Index("ix_model_selections_user_provider", "user_id", "provider"),
    )


class AgentLog(Base):
    __tablename__ = "agent_logs"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), index=True)
    content = Column(Text)
    type = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    thread = relationship("Thread", back_populates="agent_logs")

    __table_args__ = (
        Index("ix_agent_logs_thread_created", "thread_id", "created_at"),
    )


class BackgroundTask(Base):
    __tablename__ = "background_tasks"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), index=True)
    status = Column(String, default="pending", index=True)
    task_type = Column(String, index=True)
    payload = Column(JSON)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    workspace = relationship("Workspace", back_populates="background_tasks")
    task_logs = relationship("TaskLog", back_populates="task")
    blocker_notifications = relationship("BlockerNotification", back_populates="task")

    __table_args__ = (
        Index("ix_background_tasks_workspace_status", "workspace_id", "status"),
        Index("ix_background_tasks_created_status", "created_at", "status"),
    )


class TaskLog(Base):
    __tablename__ = "task_logs"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("background_tasks.id"), index=True)
    content = Column(Text)
    level = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("BackgroundTask", back_populates="task_logs")

    __table_args__ = (
        Index("ix_task_logs_task_created", "task_id", "created_at"),
    )


class BlockerNotification(Base):
    __tablename__ = "blocker_notifications"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("background_tasks.id"), index=True)
    reason = Column(Text)
    resolved = Column(Boolean, default=False, index=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("BackgroundTask", back_populates="blocker_notifications")

    __table_args__ = (
        Index("ix_blocker_notifications_task_resolved", "task_id", "resolved"),
    )


class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(Text)
    content = Column(Text)
    embedding = Column(Vector(1536))
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    is_global = Column(Boolean, default=False, index=True)
    category = Column(String, index=True)
    skill_type = Column(String, default="general", index=True)  # workflow, integration, general
    compatibilities = Column(JSON, default=list)  # ["warp", "github", "etc"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    workspace = relationship("Workspace", back_populates="skills")

    __table_args__ = (
        Index("ix_skills_workspace_global", "workspace_id", "is_global"),
        Index("ix_skills_name_workspace", "name", "workspace_id"),
    )