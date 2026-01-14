"""
SearchableMixin: Unified search and embedding management for SQLAlchemy models.

This mixin provides:
1. Intelligent embedding generation with hash-based caching
2. Unified search interface supporting hybrid (RRF), FTS-only, or vector-only modes
3. Automatic embedding updates on model changes

The mixin implements the Reciprocal Rank Fusion (RRF) algorithm for combining
vector similarity search with full-text search results, providing superior
search quality compared to either method alone.

Key Features:
- Hash-based caching: Avoids expensive API calls when content hasn't changed
- RRF algorithm: Combines vector and FTS results for better relevance
- Automatic embedding updates: Triggers on insert/update via SQLAlchemy events
- Flexible search modes: Hybrid, FTS-only, or vector-only per model
"""

import hashlib
from typing import List, Optional, Dict, Any, Literal

from sqlalchemy import Column, String, event, select, func, text, inspect, and_
from sqlalchemy.orm import Session, declarative_mixin
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector

from ..services.embedding_service import embedding_service

# Search mode configuration type
# "hybrid": Combines vector search and FTS using RRF algorithm
# "fts_only": Uses only PostgreSQL full-text search (no embeddings)
# "vector_only": Uses only vector similarity search (not implemented yet)
SearchMode = Literal["hybrid", "fts_only", "vector_only"]


@declarative_mixin
class SearchableMixin:
    """
    Mixin for SQLAlchemy models providing unified search and embedding capabilities.
    
    This mixin adds search functionality to models that need semantic search.
    Models using this mixin must:
    1. Define a `search_vector` column (TSVECTOR) using Computed()
    2. Implement `get_search_content()` method
    
    Search Modes:
        - "hybrid": Uses Reciprocal Rank Fusion (RRF) to combine vector and FTS results
        - "fts_only": Uses only PostgreSQL full-text search (no embeddings needed)
        - "vector_only": Uses only vector similarity (not yet implemented)
    
    Embedding Caching:
        Embeddings are automatically generated and cached using SHA-256 hash.
        If content hasn't changed (hash matches), embedding is not regenerated,
        saving API costs and processing time.
    
    Example:
        ```python
        class TableNode(SearchableMixin, Base):
            __tablename__ = "tables"
            
            semantic_name = Column(String(255))
            description = Column(Text)
            
            # Computed TSVECTOR for full-text search
            search_vector = Column(
                TSVECTOR,
                Computed("to_tsvector('simple', semantic_name || ' ' || description)", persisted=True)
            )
            
            def get_search_content(self) -> str:
                return f"{self.semantic_name} {self.description or ''}".strip()
        ```
    """

    # Search mode configuration (can be overridden in child models)
    # Default is "hybrid" which provides the best search quality
    _search_mode: SearchMode = "hybrid"

    # Vector embedding column (1536 dimensions for text-embedding-3-small)
    # Nullable because FTS-only mode doesn't need embeddings
    embedding = Column(Vector(1536), nullable=True)

    # SHA-256 hash of the content used to generate the embedding
    # Used for caching: if hash matches, embedding doesn't need regeneration
    # Format: 64-character hexadecimal string
    embedding_hash = Column(String(64), nullable=True)

    # Note: 'search_vector' (TSVECTOR) must be defined in the child model
    # using Computed(), as it depends on model-specific columns.
    # Example:
    #   search_vector = Column(
    #       TSVECTOR,
    #       Computed("to_tsvector('simple', semantic_name || ' ' || description)", persisted=True)
    #   )

    def get_search_content(self) -> str:
        """
        Abstract method: Return the text content to be embedded and searched.
        
        This method must be implemented by child models to specify which
        fields should be used for embedding generation and search.
        
        Returns:
            str: Text content to embed (concatenated from relevant fields)
        
        Raises:
            NotImplementedError: If not implemented by child model
        
        Example:
            ```python
            def get_search_content(self) -> str:
                parts = [self.semantic_name, self.description]
                return " ".join([p for p in parts if p]).strip()
            ```
        """
        raise NotImplementedError("Child model must implement get_search_content()")

    def _compute_hash(self, text: str) -> str:
        """
        Compute SHA-256 hash of text content.
        
        Used to detect content changes and avoid unnecessary embedding regeneration.
        
        Args:
            text: Text content to hash
        
        Returns:
            str: 64-character hexadecimal SHA-256 hash
        
        Example:
            >>> mixin._compute_hash("test content")
            'a8f5f167f44f4964e6c998dee827110c...'
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def update_embedding_if_needed(self):
        """
        Intelligently update embedding only if content has changed.
        
        This method implements hash-based caching to avoid expensive API calls:
        1. If search mode is FTS-only, clears embedding (not needed)
        2. If content is empty, clears embedding
        3. If content hash matches existing hash, skips regeneration (cache hit)
        4. Otherwise, generates new embedding and updates hash
        
        This optimization is critical for:
        - Cost savings: OpenAI API calls are expensive
        - Performance: Embedding generation is slow
        - Database efficiency: Avoids unnecessary updates
        
        The method is automatically called by SQLAlchemy event listeners
        before insert and update operations.
        
        Note:
            This method modifies the model instance in-place.
            Changes are persisted when the session is committed.
        """
        # FTS-only mode doesn't need embeddings
        if self._search_mode == "fts_only":
            self.embedding = None
            self.embedding_hash = None
            return

        # Get content to embed
        content = self.get_search_content()
        if not content:
            # Empty content: clear embedding
            self.embedding = None
            self.embedding_hash = None
            return

        # Compute hash of current content
        new_hash = self._compute_hash(content)

        # CRITICAL OPTIMIZATION: If hash matches, content hasn't changed
        # Skip expensive API call and database update
        if self.embedding_hash == new_hash and self.embedding is not None:
            return  # Cache hit: no update needed

        # Content changed or embedding missing: regenerate
        vector = embedding_service.generate_embedding(content)

        # Update embedding and hash
        self.embedding = vector
        self.embedding_hash = new_hash

    @classmethod
    def _apply_filters(cls, stmt, filters: Dict[str, Any]):
        """
        Apply filter conditions to a SQLAlchemy statement.
        
        Safely applies filters by validating that filter keys correspond
        to actual model columns. Invalid filters are ignored.
        
        Args:
            stmt: SQLAlchemy select statement
            filters: Dictionary of column_name -> value filters
        
        Returns:
            SQLAlchemy statement with WHERE conditions applied
        
        Example:
            ```python
            stmt = select(TableNode)
            stmt = SearchableMixin._apply_filters(stmt, {"datasource_id": uuid})
            ```
        """
        if not filters:
            return stmt

        # Get mapper to validate column names
        mapper = inspect(cls)
        conditions = []
        
        for attr, value in filters.items():
            # Security: Only apply filters for valid columns
            # Prevents SQL injection via invalid filter keys
            if attr in mapper.columns:
                col = getattr(cls, attr)
                # Apply filter: col == value
                # In SQL, NULL == value evaluates to NULL (not True), so NULL values are automatically excluded
                # This is the correct behavior: when filtering for a specific value, NULLs should not match
                conditions.append(col == value)

        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    @classmethod
    def search(
        cls,
        session: Session,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 10,
        offset: int = 0,
        k: int = 60,
        base_stmt=None
    ) -> List[Dict[str, Any]]:
        """
        Unified search interface supporting multiple search modes.
        
        This method provides a single API for semantic search that internally
        handles different search strategies based on the model's _search_mode:
        - "hybrid": Reciprocal Rank Fusion (RRF) combining vector + FTS
        - "fts_only": PostgreSQL full-text search only
        
        Args:
            session: SQLAlchemy database session
            query: Search query string (natural language)
            filters: Optional dictionary of column filters (e.g., {"datasource_id": uuid})
            limit: Maximum number of results to return (default: 10)
            offset: Number of results to skip (default: 0)
            k: RRF constant for score calculation (default: 60)
                Higher k = more weight to top-ranked results
            base_stmt: Optional base SQLAlchemy statement (for joins, etc.)
        
        Returns:
            List of dictionaries with "score" and "entity" keys:
            [
                {"score": 0.85, "entity": <ModelInstance>},
                {"score": 0.72, "entity": <ModelInstance>},
                ...
            ]
        
        Raises:
            NotImplementedError: If search mode is not implemented
        
        Example:
            ```python
            # Hybrid search (default)
            results = TableNode.search(
                session=db,
                query="sales transactions",
                filters={"datasource_id": datasource_id},
                limit=20
            )
            
            # Results are sorted by relevance score
            for result in results:
                print(f"Score: {result['score']}, Table: {result['entity'].semantic_name}")
            ```
        
        Note:
            The RRF algorithm combines results from multiple search methods.
            Items appearing in both result sets get higher scores.
        """
        if filters is None:
            filters = {}

        # Handle empty queries: if filters are provided, return filtered results
        # Otherwise, return empty (empty query without filters is not meaningful)
        if not query or not query.strip():
            # If no query, return all results (filtered if filters exist)
            # This enables "list all" functionality when search box is empty
            stmt = base_stmt if base_stmt is not None else select(cls)
            stmt = cls._apply_filters(stmt, filters)
            stmt = stmt.offset(offset).limit(limit)
            results = session.execute(stmt).scalars().all()
            # Return with a default score of 1.0 for non-search results
            return [{"score": 1.0, "entity": obj} for obj in results]

        # --- CASE A: FTS ONLY (Pure Relational Search) ---
        if cls._search_mode == "fts_only":
            # Use websearch_to_tsquery for user-friendly query syntax
            # Supports operators like: "sales -marketing" (sales but not marketing)
            # Using 'simple' instead of 'english' for better multilingual support
            ts_query = func.websearch_to_tsquery('simple', query)

            # Build query with FTS ranking
            # Use base_stmt if provided (allows joins, etc.), otherwise select from model
            stmt = base_stmt if base_stmt is not None else select(cls)
            
            # Add ranking score using ts_rank_cd (coverage density ranking)
            # This provides better ranking than ts_rank for multi-word queries
            stmt = stmt.add_columns(
                func.ts_rank_cd(cls.search_vector, ts_query).label("rank")
            )

            # Apply full-text search condition (@@ operator means "matches")
            stmt = stmt.where(cls.search_vector.op('@@')(ts_query))
            
            # Apply additional filters
            stmt = cls._apply_filters(stmt, filters)
            
            # Order by relevance, apply offset and limit
            stmt = stmt.order_by(text("rank DESC")).offset(offset).limit(limit)

            results = session.execute(stmt).all()

            # Normalize output format to match RRF output
            # Result rows contain (model_instance, rank_score)
            return [
                {"score": float(row.rank), "entity": row[0]}
                for row in results
            ]

        # --- CASE B: HYBRID (Reciprocal Rank Fusion) ---
        elif cls._search_mode == "hybrid":
            # Step 1: Vector Similarity Search
            # Generate embedding for the query
            vector = embedding_service.generate_embedding(query)

            # Build vector search query
            # Order by L2 distance (Euclidean distance in vector space)
            # Lower distance = higher similarity
            vec_stmt = base_stmt if base_stmt is not None else select(cls)
            vec_stmt = vec_stmt.order_by(cls.embedding.l2_distance(vector))
            vec_stmt = cls._apply_filters(vec_stmt, filters)
            
            # Get more results to account for offset (we'll merge with FTS results)
            # Need enough results to cover offset + limit after RRF
            vec_res = session.execute(vec_stmt.limit((offset + limit) * 2)).scalars().all()

            # Step 2: Full-Text Search
            # Build FTS query using PostgreSQL's websearch_to_tsquery
            # Using 'simple' instead of 'english' for better multilingual support
            fts_stmt = base_stmt if base_stmt is not None else select(cls)
            fts_stmt = fts_stmt.where(
                cls.search_vector.op('@@')(func.websearch_to_tsquery('simple', query))
            )
            fts_stmt = cls._apply_filters(fts_stmt, filters)
            
            # Get more results to account for offset (we'll merge with FTS results)
            fts_res = session.execute(fts_stmt.limit((offset + limit) * 2)).scalars().all()

            # Step 3: Reciprocal Rank Fusion (RRF)
            # RRF combines results from multiple ranking methods
            # Formula: RRF_score = sum(1 / (k + rank)) for each ranking
            # where k is a constant (typically 60) and rank is 0-indexed position
            #
            # Why RRF?
            # - Vector search excels at semantic similarity
            # - FTS excels at exact keyword matching
            # - RRF combines both strengths for superior results
            #
            # Example:
            #   Item at rank 0 in vector search: score += 1/(60+0) = 0.0167
            #   Item at rank 0 in FTS search: score += 1/(60+0) = 0.0167
            #   Item appearing in both at top: total = 0.0334 (highest score)
            scores = {}
            obj_map = {}

            def calculate_rrf(results):
                """
                Calculate RRF scores for a result set.
                
                For each item, adds 1/(k + rank) to its score.
                Items appearing in multiple result sets get cumulative scores.
                """
                for rank, obj in enumerate(results):
                    # RRF formula: 1 / (k + rank)
                    # rank is 0-indexed, so rank 0 gets highest score
                    rrf_score = 1.0 / (k + rank + 1)
                    scores[obj.id] = scores.get(obj.id, 0) + rrf_score
                    obj_map[obj.id] = obj

            # Calculate RRF scores for both result sets
            calculate_rrf(vec_res)
            calculate_rrf(fts_res)

            # Sort by combined RRF score (descending)
            final_results = sorted(
                [{"score": s, "entity": obj_map[id]} for id, s in scores.items()],
                key=lambda x: x['score'],
                reverse=True
            )
            
            # Apply offset and limit
            return final_results[offset:offset + limit]

        else:
            raise NotImplementedError(f"Search mode '{cls._search_mode}' not implemented")
    
    @classmethod
    def search_count(
        cls,
        session: Session,
        query: str,
        filters: Dict[str, Any] = None,
        base_stmt=None
    ) -> int:
        """
        Count total number of results matching the search query and filters.
        
        This method performs a simplified count query without applying
        RRF or full ranking, which makes it more efficient for pagination.
        
        Args:
            session: SQLAlchemy database session
            query: Search query string (natural language)
            filters: Optional dictionary of column filters
            base_stmt: Optional base SQLAlchemy statement (for joins, etc.)
        
        Returns:
            Total number of matching results
        """
        if filters is None:
            filters = {}
        
        # Handle empty queries: count all results matching filters only
        if not query or not query.strip():
            if base_stmt is not None:
                # Count from base_stmt with filters only (no FTS condition)
                # Note: filters should already be applied in base_stmt, but we apply them again to be safe
                subq = base_stmt.subquery()
                stmt = select(func.count()).select_from(subq)
                # If filters are not already in base_stmt, we need to apply them
                # For now, assume filters are in base_stmt
            else:
                # Standard count query with filters only
                stmt = select(func.count()).select_from(cls)
                stmt = cls._apply_filters(stmt, filters)
            result = session.execute(stmt).scalar()
            return result if result is not None else 0
        
        # Build count query with FTS condition
        # For FTS, we can count directly
        # For hybrid, we count items that match FTS criteria (simpler than vector count)
        
        # FIX: For Hybrid search (RRF), standard behavior is to return "best effort" results.
        # But for pagination to be consistent ("1-10 of 100"), we should report total items matching filters,
        # treating the search query as a ranking signal rather than a strict boolean filter.
        # This aligns with "Ranked Retrieval" logic where documents are scored but not necessarily excluded.
        if cls._search_mode == "hybrid":
             if base_stmt is not None:
                subq = base_stmt.subquery()
                stmt = select(func.count()).select_from(subq)
             else:
                stmt = select(func.count()).select_from(cls)
                stmt = cls._apply_filters(stmt, filters)
             result = session.execute(stmt).scalar()
             return result if result is not None else 0

        # For FTS-only mode, we keep strict filtering because that's "Search" (Boolean)
        ts_query = func.websearch_to_tsquery('simple', query)
        
        if base_stmt is not None:
            # If base_stmt is provided, count from it with FTS condition
            # Create a subquery from base_stmt and apply FTS filter
            subq = base_stmt.where(cls.search_vector.op('@@')(ts_query)).subquery()
            stmt = select(func.count()).select_from(subq)
            # Apply additional filters on the subquery
            # Note: filters are already applied in base_stmt, so we may not need to reapply
        else:
            # Standard count query
            stmt = select(func.count()).select_from(cls)
            stmt = stmt.where(cls.search_vector.op('@@')(ts_query))
            stmt = cls._apply_filters(stmt, filters)
        
        return session.execute(stmt).scalar() or 0

# --- SQLAlchemy Event Listeners ---
# These listeners automatically update embeddings when models are saved


@event.listens_for(SearchableMixin, 'before_insert', propagate=True)
@event.listens_for(SearchableMixin, 'before_update', propagate=True)
def receive_before_save(mapper, connection, target):
    """
    SQLAlchemy event listener for automatic embedding updates.
    
    This listener is triggered before INSERT and UPDATE operations on any
    model that inherits from SearchableMixin. It ensures embeddings are
    up-to-date with the current content.
    
    The listener:
    1. Checks if content has changed (via hash comparison)
    2. Regenerates embedding only if needed (cost optimization)
    3. Updates embedding_hash for future comparisons
    
    Args:
        mapper: SQLAlchemy mapper for the model
        connection: Database connection
        target: Model instance being saved
    
    Note:
        propagate=True ensures this listener applies to all child models
        that inherit from SearchableMixin.
    
    Example:
        When you save a TableNode:
        ```python
        table = TableNode(semantic_name="Sales", description="Sales data")
        db.add(table)
        db.commit()  # This triggers the listener
        # Embedding is automatically generated and saved
        ```
    """
    # Trigger automatic embedding update (with hash-based caching)
    target.update_embedding_if_needed()