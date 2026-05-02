from github import Github
from app.core.embedding import get_embedding_model
from app.database.models import CodeChunk
from app.database.session import SessionLocal
import asyncio
import structlog
from datetime import datetime

logger = structlog.get_logger()

class CodebaseIndexer:
  
  def __init__(self, db, github_token: str):
    self.db = db
    self.g = Github(github_token)
    self.embedder = get_embedding_model()
  
  async def index_repo(
    self,
    workspace_id: int,
    owner: str,
    repo: str,
    branch: str = "main"
  ):
    """
    Full repo indexing pipeline:
    1. Fetch all files from GitHub tree API
    2. Filter to code files only
    3. Chunk each file by function/class
    4. Generate embeddings
    5. Store in CodeChunk table
    6. Clear old chunks for this workspace first
    """
    repo_obj = self.g.get_repo(f"{owner}/{repo}")
    
    # Delete existing chunks
    self.db.query(CodeChunk).filter(
      CodeChunk.workspace_id == workspace_id
    ).delete()
    self.db.commit()
    
    # Get full file tree
    tree = repo_obj.get_git_tree(branch, 
                                  recursive=True)
    
    CODE_EXTENSIONS = {
      '.py', '.ts', '.tsx', '.js', '.jsx',
      '.go', '.rs', '.java', '.cpp', '.c',
      '.cs', '.rb', '.php', '.swift', '.kt'
    }
    
    code_files = [
      item for item in tree.tree
      if item.type == "blob" and
      any(item.path.endswith(ext) 
          for ext in CODE_EXTENSIONS) and
      item.size < 100000  # skip huge files
    ]
    
    # Process in batches of 10
    for i in range(0, len(code_files), 10):
      batch = code_files[i:i+10]
      await self._process_batch(
        workspace_id, repo_obj, batch, branch)
    
    return len(code_files)
  
  async def _process_batch(
    self, workspace_id, repo_obj, files, branch
  ):
    texts = []
    metas = []
    
    for file_item in files:
      try:
        content = repo_obj.get_contents(
          file_item.path, ref=branch
        ).decoded_content.decode('utf-8', 
                                  errors='ignore')
        
        chunks = self._chunk_file(
          content, file_item.path)
        
        for chunk in chunks:
          texts.append(chunk['content'])
          metas.append({
            'file_path': file_item.path,
            'chunk': chunk
          })
      except:
        continue
    
    if not texts:
      return
    
    embeddings = self.embedder.embed_documents(
      texts)
    
    for meta, embedding in zip(metas, embeddings):
      chunk = CodeChunk(
        workspace_id=workspace_id,
        file_path=meta['file_path'],
        content=meta['chunk']['content'],
        embedding=embedding
      )
      self.db.add(chunk)
    
    self.db.commit()
  
  def _chunk_file(
    self, content: str, file_path: str
  ) -> list:
    """
    Chunk file by logical units.
    For now use sliding window of 50 lines
    with 10 line overlap.
    Later upgrade to AST-based chunking.
    """
    lines = content.split('\n')
    chunks = []
    window = 50
    overlap = 10
    
    for i in range(0, len(lines), 
                   window - overlap):
      chunk_lines = lines[i:i+window]
      chunk_content = '\n'.join(chunk_lines)
      if chunk_content.strip():
        chunks.append({
          'content': chunk_content,
          'start_line': i + 1,
          'end_line': min(i + window, 
                         len(lines))
        })
    
    return chunks
