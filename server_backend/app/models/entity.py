from pydantic import BaseModel
from typing import Optional, Dict, Any

class CanonicalEntity(BaseModel):
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    key_specs: Dict[str, Any] = {}
    normalized_price: Optional[float] = None

class DealCandidate(BaseModel):
    title: str
    price: float
    url: str
    match_type: str
    composite_score: float