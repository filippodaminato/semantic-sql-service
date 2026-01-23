from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class PruneTarget(BaseModel):
    """Identifica un elemento da rimuovere dal contesto."""
    target_type: Literal["table", "column", "metric"] = Field(
        ..., description="Il tipo di elemento da rimuovere."
    )
    name: str = Field(
        ..., description="Il nome esatto dell'elemento (es. 'users', 'users.email')."
    )
    reasoning: str = Field(
        ..., description="Perché questo elemento non è utile per la domanda."
    )

class FetchTarget(BaseModel):
    """Identifica una ricerca mirata da effettuare."""
    search_text: str = Field(
        ..., description="La stringa di ricerca esatta da passare al tool (es. 'Triveneto', 'Meaning of EBITDA')."
    )
    context_slug: Optional[str] = Field(
        None, description="Se la ricerca è legata a una colonna specifica, metti qui il suo slug."
    )

class QueryPlan(BaseModel):
    """Il piano d'azione per raffinare il contesto."""
    status_reasoning: str = Field(
        ..., description="Analisi dello stato attuale del contesto rispetto alla domanda."
    )
    action_type: Literal["PRUNE", "FETCH", "READY"] = Field(
        ..., description="L'azione principale da intraprendere."
    )
    prune_targets: List[PruneTarget] = Field(
        default_factory=list, description="Lista di elementi da rimuovere (solo se action_type='PRUNE')."
    )
    fetch_targets: List[FetchTarget] = Field(
        default_factory=list, description="Lista di ricerche da fare (solo se action_type='FETCH')."
    )

class SearchEvaluation(BaseModel):
    """Decisione su quali risultati di ricerca mantenere."""
    is_irrelevant: bool = Field(
        ..., description="True se TUTTI i risultati trovati sono irrilevanti."
    )
    formatted_note: Optional[str] = Field(
        None, description="Se rilevanti, una nota riassuntiva Markdown da aggiungere al contesto."
    )
    reasoning: str = Field(
        ..., description="Spiegazione della valutazione."
    )
