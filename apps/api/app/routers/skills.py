from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database.session import get_db
from ..database.models import Skill
from ..schemas.skill import SkillCreate, SkillUpdate, SkillResponse, SkillSearchRequest, SkillSearchResponse, SkillCategory
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/skills", tags=["skills"])

@router.get("", response_model=List[SkillResponse])
async def list_skills(workspace_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Skill)
    if workspace_id:
        query = query.filter((Skill.workspace_id == workspace_id) | (Skill.is_global == True))
    else:
        query = query.filter(Skill.is_global == True)
    return query.all()

@router.get("/categories")
async def get_categories():
    return [c.value for c in SkillCategory]

@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(Skill).get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill

@router.post("", response_model=SkillResponse)
async def create_skill(skill_in: SkillCreate, db: Session = Depends(get_db)):
    skill = Skill(**skill_in.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill

@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: int, skill_in: SkillUpdate, db: Session = Depends(get_db)):
    skill = db.query(Skill).get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    update_data = skill_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(skill, field, value)
        
    db.commit()
    db.refresh(skill)
    return skill

@router.delete("/{skill_id}")
async def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(Skill).get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(skill)
    db.commit()
    return {"status": "success"}

@router.post("/search", response_model=SkillSearchResponse)
async def search_skills(search: SkillSearchRequest, db: Session = Depends(get_db)):
    # Simple name-based search for now, could use pgvector if implemented in Skill model
    skills = db.query(Skill).filter(
        Skill.name.ilike(f"%{search.query}%")
    ).limit(search.limit).all()
    return {"skills": skills, "query": search.query}
