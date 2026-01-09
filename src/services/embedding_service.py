"""Service for generating embeddings using OpenAI"""
from typing import List
import numpy as np
from openai import OpenAI
import hashlib
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("embedding_service")


class EmbeddingService:
    """Service for generating embeddings"""
    
    def __init__(self):
        # Initialize OpenAI client
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required but not set in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = settings.openai_model
        self.dimensions = settings.embedding_dimensions
    
    def calculate_hash(self, text: str) -> str:
        """
        Calculate SHA-256 hash of the text to track changes
        
        Args:
            text: Text to hash
            
        Returns:
            Hex string of hash
        """
        if not text:
            return None
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimensions
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip()
            )
            logger.info(f"Generated embedding for text of length {len(text)}")
            return response.data[0].embedding
        except Exception as e:
            # Log error and return zero vector as fallback
            logger.error(f"Error generating embedding: {str(e)}")
            # In production, you might want to raise or use a fallback strategy
            # print(f"Error generating embedding: {e}")
            return [0.0] * self.dimensions
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch operation)
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter out empty texts
        non_empty_texts = [t.strip() for t in texts if t and t.strip()]
        if not non_empty_texts:
            return [[0.0] * self.dimensions] * len(texts)
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=non_empty_texts
            )
            logger.info(f"Generated batch embeddings: {len(non_empty_texts)} items")
            embeddings = {item.index: item.embedding for item in response.data}
            
            # Map back to original list, handling empty texts
            result = []
            text_idx = 0
            for original_text in texts:
                if original_text and original_text.strip():
                    result.append(embeddings.get(text_idx, [0.0] * self.dimensions))
                    text_idx += 1
                else:
                    result.append([0.0] * self.dimensions)
            
            return result
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            return [[0.0] * self.dimensions] * len(texts)


# Global instance
embedding_service = EmbeddingService()
