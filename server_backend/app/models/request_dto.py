from pydantic import BaseModel
from typing import Optional

class AnalyzeRequestDTO(BaseModel):
    page_url: str
    raw_title: Optional[str] = None
    raw_price: Optional[float] = None
    is_price_masked: bool = False
    image_data: Optional[str] = None
    platform: Optional[str] = "generic"