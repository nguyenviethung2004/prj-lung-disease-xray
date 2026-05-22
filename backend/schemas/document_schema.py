from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DocumentResponseSchema(BaseModel):
    DocumentID: int
    FileName: str
    FilePath: Optional[str] = None
    FileType: Optional[str] = None
    UploadedBy: Optional[int] = None
    UploadedAt: datetime
    FileSizeMB: Optional[float] = None
    Description: Optional[str] = None
    Status: str
    IsSubmitted: bool
    UploaderName: Optional[str] = None

    class Config:
        from_attributes = True

class DocumentStatsSchema(BaseModel):
    total_count: int
    processed_count: int
    total_storage_mb: float

class DocumentPaginationResponseSchema(BaseModel):
    items: List[DocumentResponseSchema]
    total: int
    page: Optional[int] = None
    limit: Optional[int] = None
    stats: DocumentStatsSchema

class DocumentUpdateSchema(BaseModel):
    Description: Optional[str] = None
    FileName: Optional[str] = None
