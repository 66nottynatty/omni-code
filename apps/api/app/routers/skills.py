from fastapi import APIRouter
from typing import List, Dict

router = APIRouter(prefix="/skills", tags=["skills"])

@router.get("/")
async def list_skills():
    return [
        {"id": "s1", "name": "web-search", "category": "intelligence"},
        {"id": "s2", "name": "filesystem", "category": "tools"}
    ]

@router.get("/categories")
async def get_categories():
    return ["intelligence", "tools", "browsing", "coding"]
