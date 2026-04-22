"""
TEN FILE: backend/schemas/scan.py

CONG DUNG:
  - Dinh nghia Pydantic schemas cho scan requests/responses
  - Xac thuc va serialize du lieu
  - Dinh nghia cau truc request tu frontend
  - Dinh nghia cau truc response tra lai frontend

CAC SCHEMAS:
  * ScanRequest: Yeu cau quet (input dau vao)
    - text: URL hoac text can quet
    - input_type: "url" hoac "text" hoac "auto"
  
  * ScanResponse: Phan hoi quet (output)
    - request_id: ID duy nhat cho yeu cau
    - input: Du lieu da quet (after cleaning)
    - input_type: Loai input
    - result: Ket qua phat hien
      - label: "phishing" hoac "legitimate"
      - probabilities: {legitimate: 0.2, phishing: 0.8}
    - heuristics_reason: Quy tac duoc kich hoat
    - advanced_explanation: Top features va giai thich

USAGE:
  from backend.schemas.scan import ScanRequest, ScanResponse
  
  # Frontend gui request
  request = ScanRequest(text="https://...", input_type="auto")
  
  # Backend gui response
  response = ScanResponse(
      request_id="xyz123",
      input="https://example.com",
      result={"label": "phishing", "probabilities": {...}}
  )

VALIDATION:
  - URL phai co http:// hoac https://
  - Text phai 5-5000 ky tu
  - input_type phai la url hoac text
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class ScanResultEnum(str, Enum):
    """Enum for scan result types"""
    PHISHING = "PHISHING"
    LEGITIMATE = "LEGITIMATE"
    SUSPICIOUS = "SUSPICIOUS"


class ScanRequest(BaseModel):
    """
    Schema for scan request (POST /api/scan)
    """
    text: str = Field(..., min_length=1, max_length=2048, description="URL or text to scan")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "https://example.com"
            }
        }


class ScanResponse(BaseModel):
    """
    Schema for returning scan result
    """
    id: int
    user_id: int
    input_text: str
    result: ScanResultEnum
    probability: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    heuristic_result: Optional[str] = None
    ml_result: Optional[str] = None
    explanation: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "input_text": "https://example.com",
                "result": "PHISHING",
                "probability": 0.95,
                "heuristic_result": "PHISHING",
                "ml_result": "PHISHING",
                "explanation": "Similar to known phishing domain",
                "created_at": "2026-04-16T10:30:00"
            }
        }


class ScanHistoryResponse(BaseModel):
    """
    Schema for returning paginated scan history
    """
    total: int = Field(..., description="Total number of scans")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    scans: list[ScanResponse]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "page": 1,
                "page_size": 10,
                "scans": []
            }
        }
