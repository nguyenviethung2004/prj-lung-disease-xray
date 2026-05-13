from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ImageAnalysisResultSchema(BaseModel):
    label: str
    confidence: float
    # GradCAM, Detection boxes, or Segmentation masks might be returned as URLs or base64
    analysis_image_url: Optional[str] = None 
    detections: Optional[List[Dict[str, Any]]] = None

class ImageUploadResultSchema(BaseModel):
    success: bool
    document_id: int
    file_url: str
    filename: str
    analysis: Optional[ImageAnalysisResultSchema] = None
    message: Optional[str] = None
    error: Optional[str] = None

class ImageUploadResponseSchema(BaseModel):
    success: bool
    conversation_id: int
    results: List[ImageUploadResultSchema]
