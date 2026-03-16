"""
Pydantic models for API responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Service status", example="ok")
    service: str = Field(..., description="Service name", example="thingsboard-power-forecast-api")
    timestamp: datetime = Field(..., description="Current server timestamp")


class ForecastStartResponse(BaseModel):
    """Response model for forecast start endpoint."""
    job_id: str = Field(..., description="Unique job identifier", example="550e8400-e29b-41d4-a716-446655440000")
    status: str = Field(..., description="Job status", example="started")
    asset_id: Optional[str] = Field(None, description="Main asset ID")
    date_range: Optional[Dict[str, str]] = Field(None, description="Requested date range with start_date and end_date")
    already_have: Optional[bool] = Field(None, description="Whether historical data already exists")


class ForecastStatusResponse(BaseModel):
    """Response model for forecast status endpoint."""
    job_id: str = Field(..., description="Unique job identifier")
    asset_id: Optional[str] = Field(None, description="Main asset ID for the job")
    status: str = Field(..., description="Current job status (pending, running, completed, failed)")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range requested for the job")
    already_have: Optional[bool] = Field(None, description="Whether historical data existed for job context")
    progress: Optional[str] = Field(None, description="Human-readable progress message")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    error: Optional[str] = Field(None, description="Error message if job failed")
    total_assets: Optional[int] = Field(None, description="Total number of assets to process")
    processed_assets: Optional[int] = Field(None, description="Number of assets processed")
    successful_assets: Optional[int] = Field(None, description="Number of successfully processed assets")
    failed_assets: Optional[int] = Field(None, description="Number of failed assets")
    skipped_assets: Optional[int] = Field(None, description="Number of skipped assets")
    current_step: Optional[str] = Field(None, description="Current processing step")
    errors: Optional[List[Any]] = Field(None, description="List of asset-level errors")


class NewAssetResponse(BaseModel):
    """Response model for new asset processing endpoint."""
    status: str = Field(..., description="Processing status", example="telemetry_written")
    asset_id: str = Field(..., description="Asset ID that was processed")
    message: Optional[str] = Field(None, description="Additional information")


class ErrorResponse(BaseModel):
    """Response model for API errors."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
