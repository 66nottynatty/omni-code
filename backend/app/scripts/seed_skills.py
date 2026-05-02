"""
Script to seed the skills library with markdown files.
Run with: python -m app.scripts.seed_skills
"""
import os
from pathlib import Path
from app.database.session import SessionLocal
from app.core.embedding import get_embedding_model
from app.database.models import Skill
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills_library"

SKILL_CATEGORIES = {
    "python_expert": "Python",
    "react_specialist": "Frontend",
    "fastapi_best_practices": "Backend",
    "sql_optimization": "Database",
    "tdd_master": "Testing",
    "security_auditor": "Security",
    "refactoring_master": "Engineering",
    "api_designer": "API",
    "devops_cicd": "DevOps",
    "documentation_specialist": "Documentation",
    "git_workflow": "Engineering",
    "clean_architecture": "Engineering",
    "performance_tuning": "Performance",
}

SKILL_DESCRIPTIONS = {
    "python_expert": "Expert guidance on Python development, best practices, patterns, and performance optimization.",
    "react_specialist": "Specialized knowledge in React component architecture, state management, and performance optimization.",
    "fastapi_best_practices": "Best practices for building RESTful APIs with FastAPI, including validation, authentication, and async patterns.",
    "sql_optimization": "Advanced SQL query optimization, indexing strategies, and database performance tuning techniques.",
    "tdd_master": "Test-driven development methodology, testing patterns, and creating maintainable test suites.",
    "security_auditor": "Security best practices, vulnerability prevention, authentication, and data protection patterns.",
    "refactoring_master": "Code refactoring techniques, patterns for improving code quality and maintainability.",
    "api_designer": "RESTful API design principles, versioning strategies, documentation, and best practices.",
    "devops_cicd": "CI/CD pipeline design, Docker best practices, Kubernetes deployment, and monitoring.",
    "documentation_specialist": "Technical documentation best practices, README writing, and docstring conventions.",
    "git_workflow": "Git workflow strategies, branching models, history rewriting, and collaborative workflows.",
    "clean_architecture": "Clean Architecture principles, domain-driven design, and layered architecture patterns.",
    "performance_tuning": "Performance optimization techniques, profiling tools, caching strategies, and monitoring.",
}


def get_skill_files() -> list[tuple[str, Path]]:
    """Get all markdown files from the skills library."""
    files = []
    if SKILLS_DIR.exists():
        for file_path in SKILLS_DIR.glob("*.md"):
            name = file_path.stem
            if name in SKILL_CATEGORIES:
                files.append((name, file_path))
    return files


def extract_title(content: str) -> str:
    """Extract title from markdown content."""
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def seed_skills(recreate: bool = False):
    """Seed the database with skills from markdown files."""
    db = SessionLocal()
    embedding_model = get_embedding_model()
    
    try:
        existing_skills = {s.name: s for s in db.query(Skill).filter(Skill.is_global == True).all()}
        
        skill_files = get_skill_files()
        logger.info(f"Found {len(skill_files)} skill files")
        
        for name, file_path in skill_files:
            content = file_path.read_text(encoding='utf-8')
            title = extract_title(content) or name.replace("_", " ").title()
            description = SKILL_DESCRIPTIONS.get(name, "")
            category = SKILL_CATEGORIES.get(name, "General")
            
            # Generate embedding
            try:
                embedding_text = f"{title} {description} {content[:1000]}"
                embedding = embedding_model.embed_query(embedding_text)
            except Exception as e:
                logger.warning(f"Failed to create embedding for {name}: {e}")
                embedding = None
            
            existing = existing_skills.get(name)
            
            if existing:
                if recreate:
                    logger.info(f"Updating skill: {name}")
                    existing.description = description
                    existing.content = content
                    existing.category = category
                    existing.embedding = embedding
                    db.commit()
                else:
                    logger.info(f"Skipping existing skill: {name}")
            else:
                logger.info(f"Creating skill: {name}")
                skill = Skill(
                    name=name,
                    description=description,
                    content=content,
                    category=category,
                    is_global=True,
                    embedding=embedding
                )
                db.add(skill)
                db.commit()
                logger.info(f"Created skill: {name} (ID: {skill.id})")
        
        logger.info("Skills seeded successfully!")
        
    except Exception as e:
        logger.error(f"Error seeding skills: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed skills from markdown files")
    parser.add_argument("--recreate", action="store_true", help="Recreate existing skills")
    args = parser.parse_args()
    
    seed_skills(recreate=args.recreate)
