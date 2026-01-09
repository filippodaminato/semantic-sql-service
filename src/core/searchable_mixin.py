import hashlib
from typing import List, Optional, Dict, Any, Literal

from sqlalchemy import Column, String, event, select, func, text, inspect, and_
from sqlalchemy.orm import Mapped, mapped_column, Session, declarative_mixin
from sqlalchemy.dialects.postgresql import TSVECTOR
from pgvector.sqlalchemy import Vector

# Simulazione o import reale del tuo generator
# Import embedding service
from ..services.embedding_service import embedding_service 

# Tipi di configurazione supportati
SearchMode = Literal["hybrid", "fts_only", "vector_only"]

@declarative_mixin
class SearchableMixin:
    """
    Mixin professionale per gestire:
    1. Auto-Embedding intelligente con Hash Check (caching).
    2. Ricerca unificata (RRF o FTS puro).
    """

    # --- Configurazione (Override nel modello figlio) ---
    _search_mode: SearchMode = "hybrid" 

    # --- Colonne (Nullable: usate solo se la modalità lo richiede) ---
    embedding = Column(Vector(1536), nullable=True)
    
    # Hash per evitare chiamate API inutili (es. SHA256 hex)
    embedding_hash = Column(String(64), nullable=True)

    # Nota: 'search_vector' (TSVECTOR) deve essere definito nel modello figlio 
    # tramite Computed(), poiché dipende dalle colonne specifiche del modello.

    # --- Metodi Astratti ---
    def get_search_content(self) -> str:
        """Il testo su cui basare sia l'embedding che l'hash."""
        raise NotImplementedError("Il modello deve implementare get_search_content()")

    # --- Logica Core: Hashing & Embedding ---
    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def update_embedding_if_needed(self):
        """
        Logica intelligente: rigenera il vettore solo se:
        1. La modalità prevede vettori.
        2. Il contenuto è cambiato (hash mismatch).
        """
        # Se siamo in modalità solo FTS, puliamo e usciamo
        if self._search_mode == "fts_only":
            self.embedding = None
            self.embedding_hash = None
            return

        content = self.get_search_content()
        if not content:
            self.embedding = None
            self.embedding_hash = None
            return

        new_hash = self._compute_hash(content)

        # CHECK CRITICO: Se l'hash è uguale, non fare nulla (risparmia $$ e tempo)
        if self.embedding_hash == new_hash and self.embedding is not None:
            return  # Skip!

        # Se siamo qui, dobbiamo rigenerare
        # print(f"Refreshing embedding for {self.__class__.__name__}...")
        vector = embedding_service.generate_embedding(content)
        
        self.embedding = vector
        self.embedding_hash = new_hash

    # --- Helper Filtri ---
    @classmethod
    def _apply_filters(cls, stmt, filters: Dict[str, Any]):
        if not filters: return stmt
        
        mapper = inspect(cls)
        conditions = []
        for attr, value in filters.items():
            if attr in mapper.columns: # Sicurezza: ignora filtri non validi
                col = getattr(cls, attr)
                conditions.append(col == value)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    # --- Motore di Ricerca Unificato ---
    @classmethod
    def search(
        cls, 
        session: Session, 
        query: str, 
        filters: Dict[str, Any] = None, 
        limit: int = 10,
        k: int = 60,
        base_stmt = None
    ) -> List[Dict[str, Any]]:
        """
        API Unica: Gestisce internamente se fare RRF o solo FTS.
        """
        if filters is None: filters = {}
        
        # --- CASO A: FTS ONLY (Relazionale Puro) ---
        if cls._search_mode == "fts_only":
            # Usiamo websearch_to_tsquery per supportare operatori (es. "sales -marketing")
            ts_query = func.websearch_to_tsquery('english', query)
            
            # Select con Ranking FTS
            # Base stmt override check
            stmt = base_stmt if base_stmt is not None else select(cls)
            stmt = stmt.add_columns(func.ts_rank_cd(cls.search_vector, ts_query).label("rank"))
            
            stmt = stmt.where(cls.search_vector.op('@@')(ts_query))
            stmt = cls._apply_filters(stmt, filters)
            stmt = stmt.order_by(text("rank DESC")).limit(limit)
            
            results = session.execute(stmt).all()
            
            # Normalizziamo output identico a RRF
            # Note: result rows might be different if base_stmt has joins? 
            # Usually select(cls) returns (instance,). add_columns adds to referencing.
            # safe unpacking:
            return [
                {"score": row.rank, "entity": row[0]} 
                for row in results
            ]

        # --- CASO B: HYBRID (RRF) ---
        elif cls._search_mode == "hybrid":
            # 1. Vector Search
            vector = embedding_service.generate_embedding(query)
            
            vec_stmt = base_stmt if base_stmt is not None else select(cls)
            vec_stmt = vec_stmt.order_by(cls.embedding.l2_distance(vector))
            vec_stmt = cls._apply_filters(vec_stmt, filters)
            vec_res = session.execute(vec_stmt.limit(limit * 2)).scalars().all()

            # 2. FTS Search
            fts_stmt = base_stmt if base_stmt is not None else select(cls)
            fts_stmt = fts_stmt.where(
                cls.search_vector.op('@@')(func.websearch_to_tsquery('english', query))
            )
            fts_stmt = cls._apply_filters(fts_stmt, filters)
            fts_res = session.execute(fts_stmt.limit(limit * 2)).scalars().all()

            # 3. Fusione RRF
            scores = {}
            obj_map = {}
            
            def calculate_rrf(results):
                for rank, obj in enumerate(results):
                    scores[obj.id] = scores.get(obj.id, 0) + (1.0 / (k + rank + 1))
                    obj_map[obj.id] = obj

            calculate_rrf(vec_res)
            calculate_rrf(fts_res)

            final_results = sorted(
                [{"score": s, "entity": obj_map[id]} for id, s in scores.items()],
                key=lambda x: x['score'], reverse=True
            )
            return final_results[:limit]
            
        else:
            raise NotImplementedError(f"Mode {cls._search_mode} not implemented")

# --- Event Listeners Globali ---
@event.listens_for(SearchableMixin, 'before_insert', propagate=True)
@event.listens_for(SearchableMixin, 'before_update', propagate=True)
def receive_before_save(mapper, connection, target):
    # Triggera l'aggiornamento automatico (con controllo hash)
    target.update_embedding_if_needed()