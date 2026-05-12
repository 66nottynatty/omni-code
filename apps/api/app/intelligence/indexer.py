import os
from typing import List
from github import Github
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from app.core.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

class CodebaseIndexer:
    def __init__(self, token: str):
        self.gh = Github(token)
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = PGVector(
            connection_string=settings.database_url,
            embedding_function=self.embeddings,
            collection_name="codebase_idx"
        )

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
