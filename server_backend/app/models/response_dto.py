from pydantic import BaseModel
from typing import List
from app.models.entity import CanonicalEntity, DealCandidate

class AnalyzeResponseDTO(BaseModel):
    canonical_entity: CanonicalEntity
    deals: List[DealCandidate] = []
    ai_verdict: str