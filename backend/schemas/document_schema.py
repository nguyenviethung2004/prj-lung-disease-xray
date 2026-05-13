from pydantic import BaseModel, Field
from typing import Optional
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

class DocumentUpdateSchema(BaseModel):
    Description: Optional[str] = None
    FileName: Optional[str] = None
