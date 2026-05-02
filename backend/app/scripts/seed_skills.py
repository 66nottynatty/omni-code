"""
Script to seed the skills library with markdown files.
Supports structured directory hierarchy and metadata extraction.
Run with: python -m app.scripts.seed_skills
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from app.database.session import SessionLocal
from app.core.embedding import get_embedding_model
from app.database.models import Skill
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills"

def parse_skill_file(file_path: Path) -> Dict[str, Any]:
    """Parse a skill markdown file with frontmatter."""
    content = file_path.read_text(encoding='utf-8')
    
    # Simple frontmatter parser
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return {
                    "metadata": metadata,
                    "content": body
                }
            except Exception as e:
                logger.error(f"Error parsing frontmatter in {file_path}: {e}")
    
    # Fallback if no frontmatter
    return {
        "metadata": {
            "name": file_path.stem.replace("_", " ").title(),
            "description": "",
            "type": "general",
            "category": "General",
            "compatibilities": []
        },
        "content": content
    }

def extract_warp_config(content: str) -> Optional[Dict[str, str]]:
    """Extract Warp configuration from markdown comments."""
    import re
    warp_pattern = re.compile(r'<!-- warp-start\n(.*?)\nwarp-end -->', re.DOTALL)
    match = warp_pattern.search(content)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except Exception as e:
            logger.error(f"Error parsing Warp config: {e}")
    return None

def seed_skills(recreate: bool = False):
    """Seed the database with skills from the structured directory."""
    db = SessionLocal()
    embedding_model = get_embedding_model()
    
    try:
        # Get existing skills to avoid duplicates or update
        existing_skills = {s.name: s for s in db.query(Skill).filter(Skill.is_global == True).all()}
        
        # Walk through skills directory
        skill_files = []
        for root, dirs, files in os.walk(SKILLS_DIR):
            if "compat" in root:
                continue
            for file in files:
                if file.endswith(".md"):
                    skill_files.append(Path(root) / file)
        
        logger.info(f"Found {len(skill_files)} skill files")
        
        for file_path in skill_files:
            parsed = parse_skill_file(file_path)
            metadata = parsed["metadata"]
            content = parsed["content"]
            
            name = metadata.get("name")
            description = metadata.get("description", "")
            category = metadata.get("category", "General")
            skill_type = metadata.get("type", "general")
            compatibilities = metadata.get("compatibilities", [])
            
            logger.info(f"Processing skill: {name} ({skill_type})")
            
            # Generate embedding
            try:
                embedding_text = f"{name} {description} {content[:1000]}"
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
                    existing.skill_type = skill_type
                    existing.compatibilities = compatibilities
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
                    skill_type=skill_type,
                    compatibilities=compatibilities,
                    is_global=True,
                    embedding=embedding
                )
                db.add(skill)
                db.commit()
                logger.info(f"Created skill: {name} (ID: {skill.id})")
            
            # Handle Warp compatibility symlinks
            warp_config = extract_warp_config(content)
            if warp_config:
                warp_dir = SKILLS_DIR / "compat" / "warp"
                warp_file = warp_dir / f"{file_path.stem}.yaml"
                with open(warp_file, "w") as f:
                    yaml.dump(warp_config, f)
                logger.info(f"Created Warp config: {warp_file}")

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
