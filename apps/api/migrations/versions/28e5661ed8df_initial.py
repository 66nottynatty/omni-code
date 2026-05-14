"""initial

Revision ID: 28e5661ed8df
Revises: 
Create Date: 2024-05-14 03:48:52.942801

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '28e5661ed8df'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Enable Vector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_id', sa.String(), nullable=True),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_github_id'), 'users', ['github_id'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)

    # Workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner', sa.String(), nullable=True),
        sa.Column('repo', sa.String(), nullable=True),
        sa.Column('branch', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_owner'), 'workspaces', ['owner'], unique=False)
    op.create_index(op.f('ix_workspaces_repo'), 'workspaces', ['repo'], unique=False)
    op.create_index('ix_workspaces_owner_repo', 'workspaces', ['owner', 'repo'], unique=False)

    # Threads table
    op.create_table(
        'threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_threads_workspace_id'), 'threads', ['workspace_id'], unique=False)

    # Messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_thread_id'), 'messages', ['thread_id'], unique=False)
    op.create_index('ix_messages_thread_created', 'messages', ['thread_id', 'created_at'], unique=False)

    # Code Chunks table
    op.create_table(
        'code_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('chunk_type', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('imports', sa.JSON(), nullable=True),
        sa.Column('start_line', sa.Integer(), nullable=True),
        sa.Column('end_line', sa.Integer(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_code_chunks_file_path'), 'code_chunks', ['file_path'], unique=False)
    op.create_index(op.f('ix_code_chunks_name'), 'code_chunks', ['name'], unique=False)
    op.create_index(op.f('ix_code_chunks_workspace_id'), 'code_chunks', ['workspace_id'], unique=False)
    op.create_index('ix_code_chunks_workspace_chunk_type', 'code_chunks', ['workspace_id', 'chunk_type'], unique=False)
    op.create_index('ix_code_chunks_workspace_file', 'code_chunks', ['workspace_id', 'file_path'], unique=False)

    # Workspace Memories
    op.create_table(
        'workspace_memories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('key', sa.String(), nullable=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspace_memories_key'), 'workspace_memories', ['key'], unique=False)
    op.create_index(op.f('ix_workspace_memories_workspace_id'), 'workspace_memories', ['workspace_id'], unique=False)
    op.create_index('ix_workspace_memories_workspace_key', 'workspace_memories', ['workspace_id', 'key'], unique=False)

    # Action History
    op.create_table(
        'action_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('content_before', sa.Text(), nullable=True),
        sa.Column('content_after', sa.Text(), nullable=True),
        sa.Column('command', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_action_history_action_type'), 'action_history', ['action_type'], unique=False)
    op.create_index(op.f('ix_action_history_thread_id'), 'action_history', ['thread_id'], unique=False)
    op.create_index('ix_action_history_thread_created', 'action_history', ['thread_id', 'created_at'], unique=False)

    # Pending Changes
    op.create_table(
        'pending_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('original_content', sa.Text(), nullable=True),
        sa.Column('new_content', sa.Text(), nullable=True),
        sa.Column('diff', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_changes_file_path'), 'pending_changes', ['file_path'], unique=False)
    op.create_index(op.f('ix_pending_changes_status'), 'pending_changes', ['status'], unique=False)
    op.create_index(op.f('ix_pending_changes_thread_id'), 'pending_changes', ['thread_id'], unique=False)
    op.create_index('ix_pending_changes_thread_status', 'pending_changes', ['thread_id', 'status'], unique=False)

    # Model Selections
    op.create_table(
        'model_selections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_selections_model_name'), 'model_selections', ['model_name'], unique=False)
    op.create_index(op.f('ix_model_selections_provider'), 'model_selections', ['provider'], unique=False)
    op.create_index(op.f('ix_model_selections_user_id'), 'model_selections', ['user_id'], unique=False)
    op.create_index('ix_model_selections_user_provider', 'model_selections', ['user_id', 'provider'], unique=False)

    # Agent Logs
    op.create_table(
        'agent_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_logs_thread_id'), 'agent_logs', ['thread_id'], unique=False)
    op.create_index(op.f('ix_agent_logs_type'), 'agent_logs', ['type'], unique=False)
    op.create_index('ix_agent_logs_thread_created', 'agent_logs', ['thread_id', 'created_at'], unique=False)

    # Background Tasks
    op.create_table(
        'background_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('task_type', sa.String(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_background_tasks_status'), 'background_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_background_tasks_task_type'), 'background_tasks', ['task_type'], unique=False)
    op.create_index(op.f('ix_background_tasks_workspace_id'), 'background_tasks', ['workspace_id'], unique=False)
    op.create_index('ix_background_tasks_created_status', 'background_tasks', ['created_at', 'status'], unique=False)
    op.create_index('ix_background_tasks_workspace_status', 'background_tasks', ['workspace_id', 'status'], unique=False)

    # Task Logs
    op.create_table(
        'task_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('level', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['background_tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_logs_level'), 'task_logs', ['level'], unique=False)
    op.create_index(op.f('ix_task_logs_task_id'), 'task_logs', ['task_id'], unique=False)
    op.create_index('ix_task_logs_task_created', 'task_logs', ['task_id', 'created_at'], unique=False)

    # Blocker Notifications
    op.create_table(
        'blocker_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['background_tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_blocker_notifications_resolved'), 'blocker_notifications', ['resolved'], unique=False)
    op.create_index(op.f('ix_blocker_notifications_task_id'), 'blocker_notifications', ['task_id'], unique=False)
    op.create_index('ix_blocker_notifications_task_resolved', 'blocker_notifications', ['task_id', 'resolved'], unique=False)

    # Skills
    op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('is_global', sa.Boolean(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('skill_type', sa.String(), nullable=True),
        sa.Column('compatibilities', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_category'), 'skills', ['category'], unique=False)
    op.create_index(op.f('ix_skills_is_global'), 'skills', ['is_global'], unique=False)
    op.create_index(op.f('ix_skills_name'), 'skills', ['name'], unique=False)
    op.create_index(op.f('ix_skills_skill_type'), 'skills', ['skill_type'], unique=False)
    op.create_index(op.f('ix_skills_workspace_id'), 'skills', ['workspace_id'], unique=False)
    op.create_index('ix_skills_name_workspace', 'skills', ['name', 'workspace_id'], unique=False)
    op.create_index('ix_skills_workspace_global', 'skills', ['workspace_id', 'is_global'], unique=False)

    # Task Graphs
    op.create_table(
        'task_graphs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_graphs_status'), 'task_graphs', ['status'], unique=False)
    op.create_index(op.f('ix_task_graphs_workspace_id'), 'task_graphs', ['workspace_id'], unique=False)

    # Sub Tasks
    op.create_table(
        'sub_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('graph_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agent_type', sa.String(), nullable=True),
        sa.Column('model_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('dependencies', sa.JSON(), nullable=True),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('cost', sa.JSON(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['graph_id'], ['task_graphs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sub_tasks_graph_id'), 'sub_tasks', ['graph_id'], unique=False)
    op.create_index(op.f('ix_sub_tasks_status'), 'sub_tasks', ['status'], unique=False)

    # Task Checkpoints
    op.create_table(
        'task_checkpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('graph_id', sa.String(), nullable=True),
        sa.Column('checkpoint_number', sa.Integer(), nullable=True),
        sa.Column('state_snapshot', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['graph_id'], ['task_graphs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_checkpoints_graph_id'), 'task_checkpoints', ['graph_id'], unique=False)

    # Agent Sessions
    op.create_table(
        'agent_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_type', sa.String(), nullable=True),
        sa.Column('task_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_sessions_status'), 'agent_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_agent_sessions_task_id'), 'agent_sessions', ['task_id'], unique=False)

    # Model Feedback
    op.create_table(
        'model_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('latency', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('access_token_encrypted', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_feedback_model_id'), 'model_feedback', ['model_id'], unique=False)

    # Preview Sessions
    op.create_table(
        'preview_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_preview_sessions_workspace_id'), 'preview_sessions', ['workspace_id'], unique=False)

def downgrade() -> None:
    op.drop_table('preview_sessions')
    op.drop_table('model_feedback')
    op.drop_table('agent_sessions')
    op.drop_table('task_checkpoints')
    op.drop_table('sub_tasks')
    op.drop_table('task_graphs')
    op.drop_table('skills')
    op.drop_table('blocker_notifications')
    op.drop_table('task_logs')
    op.drop_table('background_tasks')
    op.drop_table('agent_logs')
    op.drop_table('model_selections')
    op.drop_table('pending_changes')
    op.drop_table('action_history')
    op.drop_table('workspace_memories')
    op.drop_table('code_chunks')
    op.drop_table('messages')
    op.drop_table('threads')
    op.drop_table('workspaces')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector')
