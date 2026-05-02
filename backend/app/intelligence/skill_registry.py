"""
Skill Registry - Context-aware skill retrieval and injection for agent prompts.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.models import Skill
from app.database.session import SessionLocal
from app.core.embedding import get_embedding_model
import logging

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Registry for managing and retrieving skills based on context."""

    def __init__(self, db: Session):
        self.db = db
        self._embedding_model = None

    @property
    def embedding_model(self):
        """Lazy-load embedding model."""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model

    def get_skill_by_name(self, name: str, workspace_id: Optional[int] = None) -> Optional[Skill]:
        """Get a skill by name, optionally scoped to a workspace."""
        query = self.db.query(Skill).filter(Skill.name == name)
        
        if workspace_id:
            query = query.filter(
                (Skill.workspace_id == workspace_id) | (Skill.is_global == True)
            )
        else:
            query = query.filter(Skill.is_global == True)
        
        return query.first()

    def get_skill_by_id(self, skill_id: int) -> Optional[Skill]:
        """Get a skill by ID."""
        return self.db.query(Skill).filter(Skill.id == skill_id).first()

    def find_relevant_skills(
        self,
        query: str,
        workspace_id: Optional[int] = None,
        limit: int = 3,
        include_workspace_only: bool = False
    ) -> list[Skill]:
        """
        Find skills relevant to a query using semantic search.
        
        Args:
            query: The query text to match against skills
            workspace_id: Optional workspace ID to scope results
            limit: Maximum number of skills to return
            include_workspace_only: If True, only return workspace-specific skills
            
        Returns:
            List of relevant skills sorted by relevance
        """
        try:
            query_embedding = self.embedding_model.embed_query(query)
        except Exception as e:
            logger.warning(f"Failed to create embedding for query: {e}")
            return []

        base_query = self.db.query(Skill)

        if workspace_id:
            if include_workspace_only:
                base_query = base_query.filter(Skill.workspace_id == workspace_id)
            else:
                base_query = base_query.filter(
                    (Skill.workspace_id == workspace_id) | (Skill.is_global == True)
                )
        else:
            base_query = base_query.filter(Skill.is_global == True)

        results = base_query.order_by(
            Skill.embedding.cosine_distance(query_embedding)
        ).limit(limit).all()

        return results

    def get_skills_for_task(
        self,
        task_description: str,
        workspace_id: Optional[int] = None
    ) -> list[str]:
        """
        Get skill content summaries relevant to a task.
        
        Returns skill content summaries formatted for prompt injection.
        Each summary is truncated to avoid excessive token usage.
        """
        skills = self.find_relevant_skills(task_description, workspace_id, limit=3)
        
        if not skills:
            return []
        
        summaries = []
        for skill in skills:
            truncated_content = self._truncate_for_prompt(skill.content)
            summaries.append(
                f"## {skill.name}\n\n"
                f"{skill.description}\n\n"
                f"{truncated_content}"
            )
        
        return summaries

    def _truncate_for_prompt(self, content: str, max_chars: int = 4000) -> str:
        """Truncate skill content for prompt injection."""
        if len(content) <= max_chars:
            return content
        
        return content[:max_chars] + "\n\n[Content truncated - use read_skill tool for full content]"

    def create_skill(
        self,
        name: str,
        description: str,
        content: str,
        category: str = "general",
        workspace_id: Optional[int] = None,
        is_global: bool = False
    ) -> Skill:
        """Create a new skill with embedding."""
        try:
            embedding = self.embedding_model.embed_query(f"{name} {description} {content[:500]}")
        except Exception as e:
            logger.warning(f"Failed to create embedding: {e}")
            embedding = None

        skill = Skill(
            name=name,
            description=description,
            content=content,
            category=category,
            workspace_id=workspace_id,
            is_global=is_global,
            embedding=embedding
        )
        
        self.db.add(skill)
        self.db.commit()
        self.db.refresh(skill)
        
        return skill

    def update_skill(
        self,
        skill_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[Skill]:
        """Update an existing skill."""
        skill = self.get_skill_by_id(skill_id)
        if not skill:
            return None
        
        if name is not None:
            skill.name = name
        if description is not None:
            skill.description = description
        if content is not None:
            skill.content = content
        if category is not None:
            skill.category = category
        
        # Regenerate embedding if content changed
        if name is not None or description is not None or content is not None:
            try:
                skill.embedding = self.embedding_model.embed_query(
                    f"{skill.name} {skill.description} {skill.content[:500]}"
                )
            except Exception as e:
                logger.warning(f"Failed to regenerate embedding: {e}")
        
        self.db.commit()
        self.db.refresh(skill)
        
        return skill

    def delete_skill(self, skill_id: int) -> bool:
        """Delete a skill."""
        skill = self.get_skill_by_id(skill_id)
        if not skill:
            return False
        
        self.db.delete(skill)
        self.db.commit()
        
        return True

    def list_skills(
        self,
        workspace_id: Optional[int] = None,
        category: Optional[str] = None,
        include_global: bool = True
    ) -> list[Skill]:
        """List skills with optional filtering."""
        query = self.db.query(Skill)
        
        if workspace_id:
            if include_global:
                query = query.filter(
                    (Skill.workspace_id == workspace_id) | (Skill.is_global == True)
                )
            else:
                query = query.filter(Skill.workspace_id == workspace_id)
        elif not include_global:
            query = query.filter(Skill.workspace_id == None, Skill.is_global == True)
        
        if category:
            query = query.filter(Skill.category == category)
        
        return query.order_by(Skill.name).all()

    def get_skill_categories(self, workspace_id: Optional[int] = None) -> list[str]:
        """Get unique skill categories."""
        query = self.db.query(Skill.category).distinct()
        
        if workspace_id:
            query = query.filter(
                (Skill.workspace_id == workspace_id) | (Skill.is_global == True)
            )
        else:
            query = query.filter(Skill.is_global == True)
        
        return [cat[0] for cat in query.all() if cat[0]]


def get_skill_registry() -> SkillRegistry:
    """Get a SkillRegistry instance with a new database session."""
    db = SessionLocal()
    return SkillRegistry(db)


def inject_skills_into_messages(messages: list, workspace_id: Optional[int] = None) -> list:
    """
    Inject relevant skills into messages at the start.
    
    This function analyzes the last user message and prepends
    relevant skill content as a system message.
    """
    if not messages:
        return messages
    
    # Get the last user message to determine context
    last_user_message = None
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_user_message = msg.content if hasattr(msg, 'content') else str(msg)
            break
        elif isinstance(msg, dict) and msg.get('type') == 'human':
            last_user_message = msg.get('content', '')
            break
    
    if not last_user_message:
        return messages
    
    registry = get_skill_registry()
    try:
        skill_summaries = registry.get_skills_for_task(last_user_message, workspace_id)
        
        if skill_summaries:
            skills_content = "\n\n---\n\n".join(skill_summaries)
            system_message = {
                "type": "system",
                "content": (
                    "## Relevant Skills for This Task\n\n"
                    "The following skills may be helpful for your current task:\n\n"
                    f"{skills_content}\n\n"
                    "You can also use the `read_skill` tool to get full skill details."
                )
            }
            return [system_message] + messages
    finally:
        registry.db.close()
    
    return messages
