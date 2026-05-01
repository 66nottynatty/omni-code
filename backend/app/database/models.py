from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    github_id = Column(String, unique=True)
    username = Column(String)
    email = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True)
    owner = Column(String)
    repo = Column(String)
    branch = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Thread(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    title = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"))
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CodeChunk(Base):
    __tablename__ = "code_chunks"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    file_path = Column(String)
    content = Column(Text)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class WorkspaceMemory(Base):
    __tablename__ = "workspace_memories"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    key = Column(String)
    value = Column(Text)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ActionHistory(Base):
    __tablename__ = "action_history"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"))
    action_type = Column(String) # read, write, shell, search
    file_path = Column(String, nullable=True)
    content_before = Column(Text, nullable=True)
    content_after = Column(Text, nullable=True)
    command = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PendingChange(Base):
    __tablename__ = "pending_changes"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"))
    file_path = Column(String)
    diff = Column(Text)
    status = Column(String, default="pending") # pending, accepted, rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ModelSelection(Base):
    __tablename__ = "model_selections"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String)
    model_name = Column(String)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class AgentLog(Base):
    __tablename__ = "agent_logs"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"))
    content = Column(Text)
    type = Column(String) # info, command, result, error
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class BackgroundTask(Base):
    __tablename__ = "background_tasks"
    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"))
    status = Column(String, default="pending") # pending, running, completed, failed, blocked
    task_type = Column(String) # agent_run, repo_index, etc.
    payload = Column(JSON)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class TaskLog(Base):
    __tablename__ = "task_logs"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("background_tasks.id"))
    content = Column(Text)
    level = Column(String) # info, warning, error
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class BlockerNotification(Base):
    __tablename__ = "blocker_notifications"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("background_tasks.id"))
    reason = Column(Text)
    resolved = Column(Boolean, default=False)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
