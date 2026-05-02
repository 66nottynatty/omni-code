"""
Embedding utilities for vector search.
"""
from typing import Optional, List
from app.core.config import get_settings
import os

settings = get_settings()


class EmbeddingModel:
    """Wrapper for embedding model (OpenAI or local)."""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        self.model_name = model_name
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=settings.openai_api_key)
            except ImportError:
                logger.warning("OpenAI client not available")
                self._client = None
        return self._client

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if self.client:
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"Failed to create embedding: {e}")
                return self._fallback_embedding(text)
        
        return self._fallback_embedding(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if self.client and len(texts) <= 100:
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=texts
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                logger.error(f"Failed to batch embed: {e}")
        
        return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding as fallback."""
        import hashlib
        import struct
        
        # Use SHA256 to generate deterministic but meaningless vector
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # Convert to 1536-dimensional vector (pad to required size)
        vector = []
        for i in range(1536):
            byte_idx = i % len(hash_bytes)
            value = struct.unpack('d', hash_bytes[byte_idx:byte_idx+2] + b'\x00\x00\x00\x00\x00\x00')[0]
            vector.append((value % 1.0) * 2 - 1)  # Normalize to [-1, 1]
        
        return vector


# Global embedding model instance
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """Get the global embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


import logging
logger = logging.getLogger(__name__)
