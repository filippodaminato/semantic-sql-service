"""
Embedding Service for generating vector embeddings using OpenAI.

This service provides functionality to convert text into dense vector embeddings
that can be used for semantic search. Embeddings capture semantic meaning,
allowing similarity searches that go beyond keyword matching.

The service uses OpenAI's embedding models (default: text-embedding-3-small)
which provide 1536-dimensional vectors optimized for semantic similarity.

Key Features:
- Single text embedding generation
- Batch embedding generation for efficiency
- Hash calculation for content change detection
- Error handling with fallback to zero vectors
"""

from typing import List
from openai import OpenAI
import hashlib
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("embedding_service")


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI API.
    
    This service encapsulates all OpenAI embedding operations, providing
    a clean interface for the rest of the application. It handles:
    - API client initialization
    - Single and batch embedding generation
    - Error handling and fallback strategies
    - Hash calculation for caching
    
    Attributes:
        client: OpenAI API client instance
        model: OpenAI model name (e.g., "text-embedding-3-small")
        dimensions: Vector dimensions (1536 for text-embedding-3-small)
    
    Example:
        ```python
        service = EmbeddingService()
        embedding = service.generate_embedding("Sales transactions")
        # Returns: [0.123, -0.456, 0.789, ...] (1536 dimensions)
        ```
    """
    
    def __init__(self):
        """
        Initialize the embedding service with OpenAI configuration.
        
        Raises:
            ValueError: If OPENAI_API_KEY is not set in environment variables
        """
        # Initialize OpenAI client with API key from settings
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required but not set in environment variables. "
                "Please set it in your .env file or environment."
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model = settings.openai_model
        self.dimensions = settings.embedding_dimensions
        
        logger.info(f"EmbeddingService initialized with model: {self.model} ({self.dimensions} dimensions)")
    
    def calculate_hash(self, text: str) -> str:
        """
        Calculate SHA-256 hash of text content for change detection.
        
        This hash is used to detect when text content has changed, allowing
        the system to skip expensive embedding regeneration when content
        is unchanged (see SearchableMixin.update_embedding_if_needed).
        
        Args:
            text: Text content to hash
        
        Returns:
            str: 64-character hexadecimal SHA-256 hash, or None if text is empty
        
        Example:
            >>> service.calculate_hash("Sales transactions")
            'a8f5f167f44f4964e6c998dee827110c...'
        """
        if not text:
            return None
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text string.
        
        This method calls the OpenAI API to convert text into a dense vector
        representation. The vector captures semantic meaning, allowing
        similarity searches that understand context and synonyms.
        
        Error Handling:
            - Empty text: Returns zero vector (all zeros)
            - API errors: Logs error and returns zero vector as fallback
            - Network errors: Returns zero vector (prevents application crash)
        
        Args:
            text: Text string to embed. Will be stripped of leading/trailing whitespace.
        
        Returns:
            List[float]: Embedding vector with dimensions matching self.dimensions
                       (default: 1536 for text-embedding-3-small)
                       Returns zero vector on error or empty input
        
        Raises:
            Note: This method does not raise exceptions. Errors are logged and
            a zero vector is returned as a fallback to prevent application crashes.
        
        Example:
            >>> service.generate_embedding("Sales transactions")
            [0.123, -0.456, 0.789, ...]  # 1536 dimensions
        
        Note:
            In production, you may want to:
            - Raise exceptions for critical errors
            - Implement retry logic with exponential backoff
            - Use a fallback embedding model
            - Track error rates for monitoring
        """
        # Handle empty or whitespace-only text
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, returning zero vector")
            return [0.0] * self.dimensions
        
        try:
            # Call OpenAI API to generate embedding
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip()
            )
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return response.data[0].embedding
        except Exception as e:
            # Log error for monitoring and debugging
            logger.error(f"Error generating embedding: {str(e)}")
            # Return zero vector as fallback to prevent application crash
            # In production, consider:
            # - Raising exception for critical errors
            # - Implementing retry logic
            # - Using fallback embedding service
            return [0.0] * self.dimensions
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call (batch operation).
        
        Batch operations are more efficient than individual calls because:
        - Single API request instead of multiple
        - Lower latency (one network round-trip)
        - Better rate limit utilization
        - Cost-effective for bulk operations
        
        The method preserves the order of input texts and handles empty texts
        by returning zero vectors in their positions.
        
        Args:
            texts: List of text strings to embed. Can contain empty strings.
        
        Returns:
            List[List[float]]: List of embedding vectors, one per input text.
                              Empty texts result in zero vectors.
                              Order matches input list.
        
        Example:
            >>> texts = ["Sales", "", "Transactions"]
            >>> embeddings = service.generate_embeddings_batch(texts)
            >>> len(embeddings)  # 3 embeddings
            3
            >>> embeddings[1]  # Zero vector for empty text
            [0.0, 0.0, 0.0, ...]
        
        Note:
            - Empty texts are filtered before API call but zero vectors
              are inserted back at their original positions
            - Maximum batch size depends on OpenAI API limits
            - Errors result in all-zero vectors for all texts
        """
        if not texts:
            return []
        
        # Filter out empty texts for API call
        # We'll map results back to original positions later
        non_empty_texts = [t.strip() for t in texts if t and t.strip()]
        if not non_empty_texts:
            # All texts are empty: return zero vectors for all
            return [[0.0] * self.dimensions] * len(texts)
        
        try:
            # Call OpenAI API with batch of texts
            response = self.client.embeddings.create(
                model=self.model,
                input=non_empty_texts
            )
            logger.info(f"Generated batch embeddings: {len(non_empty_texts)} items")
            
            # Create index mapping for efficient lookup
            embeddings = {item.index: item.embedding for item in response.data}
            
            # Map results back to original list positions
            # This preserves order and handles empty texts correctly
            result = []
            text_idx = 0
            for original_text in texts:
                if original_text and original_text.strip():
                    # Get embedding from API response
                    result.append(embeddings.get(text_idx, [0.0] * self.dimensions))
                    text_idx += 1
                else:
                    # Empty text: insert zero vector
                    result.append([0.0] * self.dimensions)
            
            return result
        except Exception as e:
            # Log error and return zero vectors for all texts
            logger.error(f"Error generating batch embeddings: {str(e)}")
            return [[0.0] * self.dimensions] * len(texts)


# Global instance
embedding_service = EmbeddingService()
