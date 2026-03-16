"""
Pydantic models for API requests.
"""
from pydantic import BaseModel, Field, StrictBool


class ForecastStartRequest(BaseModel):
    """Request model for starting a forecast job."""
    asset_id: str = Field(
        ...,
        description="ThingsBoard asset ID to start forecasting from",
        example="78fda490-e08b-11f0-b68f-8f33a9d74e0c"
    )
    already_have: StrictBool = Field(
        ...,
        description="Whether historical telemetry may exist (forecast still runs if history is missing)",
        example=True
    )
    start_date: str = Field(
        ...,
        description="Start date for forecast (ISO-8601)",
        example="2025-01-01"
    )
    end_date: str = Field(
        ...,
        description="End date for forecast (ISO-8601)",
        example="2025-01-31"
    )


class NewAssetRequest(BaseModel):
    """Request model for processing a new asset."""
    asset_id: str = Field(
        ...,
        description="ThingsBoard asset ID of the asset",
        example="b4ee7360-f4fb-11f0-bef0-af3b94c8901e"
    )
    already_have: StrictBool = Field(
        ...,
        description="Whether historical telemetry may exist (forecast still runs if history is missing)",
        example=False
    )
    start_date: str = Field(
        ...,
        description="Start date for forecast (ISO-8601)",
        example="2025-02-01"
    )
    end_date: str = Field(
        ...,
        description="End date for forecast (ISO-8601)",
        example="2025-02-28"
    )
