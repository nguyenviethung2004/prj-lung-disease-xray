from pydantic import BaseModel
from typing import Optional, List

class InferenceResponse(BaseModel):
    success: bool
    message: str
    label: Optional[str] = None
    confidence: Optional[float] = None
    analysis_type: Optional[str] = None
    processing_time: Optional[float] = None
    result_image: Optional[str] = None
    original_image: Optional[str] = None
    prediction_id: Optional[int] = None
    image_id: Optional[int] = None
    boxes: Optional[List] = []