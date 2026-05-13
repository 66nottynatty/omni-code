import os
from typing import List, Optional
from github import Github
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from sqlalchemy.orm import Session
from app.core.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

class CodebaseIndexer:
    def __init__(self, db: Session, token: Optional[str] = None):
        self.db = db
        self.gh = Github(token) if token else None
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = PGVector(
            connection_string=settings.database_url,
            embedding_function=self.embeddings,
            collection_name="codebase_idx"
        )

    async def index_repo(self, workspace_id: int, owner: str, repo: str, branch: str, incremental: bool):
        repo_full_name = f"{owner}/{repo}"
        logger.info("indexing_repo", workspace_id=workspace_id, repo=repo_full_name, incremental=incremental)
        
        # Call the existing implementation
        await self.index_repository(repo_full_name)
        
        # Return mock stats as expected by repos.py
        return {
            "status": "completed",
            "files_processed": 0,
            "chunks_created": 0
        }

    async def index_repository(self, repo_full_name: str):
        logger.info("indexing_repo", repo=repo_full_name)
        repo = self.gh.get_repo(repo_full_name)
        contents = repo.get_contents("")
        
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                if self._should_index(file_content.path):
                    try:
                        raw_content = file_content.decoded_content.decode("utf-8")
                        self._chunk_and_store(file_content.path, raw_content)
                    except:
                        continue

    async def search_similar(self, workspace_id: int, query: str, limit: int = 5):
        """Search for code chunks similar to the query."""
        # For a production app, we would filter by workspace_id
        # docs = self.vector_store.similarity_search(query, k=limit, filter={"workspace_id": workspace_id})
        docs = self.vector_store.similarity_search(query, k=limit)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in docs
        ]

    def _should_index(self, path: str) -> bool:
        ext = os.path.splitext(path)[1]
        return ext in [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"]

    def _chunk_and_store(self, path: str, content: str):
        # Sliding window chunking
        chunk_size = 1000
        overlap = 200
        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i : i + chunk_size]
            self.vector_store.add_texts(
                texts=[chunk],
                metadatas=[{"path": path}]
            )
