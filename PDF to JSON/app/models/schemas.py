"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class UploadResponse(BaseModel):
    """Response model for PDF upload"""
    request_id: str = Field(..., description="Unique identifier for the uploaded PDF")
    message: str = Field(..., description="Success message")


class FullTextResponse(BaseModel):
    """Response model for full text extraction"""
    request_id: str = Field(..., description="Request identifier")
    full_text: str = Field(..., description="Complete extracted text from PDF")


class ExtractedData(BaseModel):
    """Model for structured extracted data from PDF"""
    # Plant/Project Information
    Project: Optional[str] = None
    System_power: Optional[float] = Field(None, alias="System power")
    Longitude: Optional[float] = None
    Latitude: Optional[float] = None
    Altitude: Optional[float] = None
    Albedo: Optional[float] = None
    
    # Module Information
    Nb_of_modules: Optional[int] = Field(None, alias="Nb. of modules")
    Pnom_total: Optional[float] = Field(None, alias="Pnom total")
    pv_module_manufacturer: Optional[str] = None
    pv_module_model: Optional[str] = None
    unit_pv_power: Optional[float] = None
    Module_area: Optional[float] = Field(None, alias="Module area")
    
    # Inverter Information
    Inverter_Units: Optional[int] = Field(None, alias="Inverter Units")
    Inverter_Power: Optional[float] = Field(None, alias="Inverter Power")
    inverter_manufacturer: Optional[str] = None
    inverter_model: Optional[str] = None
    Pnom_ratio: Optional[float] = Field(None, alias="Pnom ratio")
    
    # Array Information
    no_arrays: Optional[int] = None
    
    # Losses
    soiling_loss_pct: Optional[str] = None
    lid_loss_pct: Optional[str] = None
    module_quality_loss_pct: Optional[str] = None
    module_mismatch_loss_pct: Optional[str] = None
    dc_wiring_loss_pct: Optional[str] = None
    ac_wiring_loss_pct: Optional[str] = None
    
    # IAM (Incidence Angle Modifier)
    iam_values: Optional[List[float]] = None
    iam_angles: Optional[List[float]] = None

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "Project": "GGC_S_0038 - Ranabima Royal College",
                "System power": 50.4,
                "Longitude": 80.123,
                "Latitude": 6.456,
                "pv_module_manufacturer": "Canadian Solar",
                "pv_module_model": "CS3W-420P",
                "inverter_manufacturer": "Huawei",
                "inverter_model": "SUN2000-50KTL-M3"
            }
        }


class ExtractResponse(BaseModel):
    """Response model for structured data extraction"""
    request_id: str = Field(..., description="Request identifier")
    data: Dict[str, Any] = Field(..., description="Extracted structured data")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current server timestamp")


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: bool = Field(True, description="Error flag")
    message: str = Field(..., description="Human readable error message")
    code: int = Field(..., description="HTTP status code")
