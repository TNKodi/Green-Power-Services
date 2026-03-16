"""
Forecast API endpoints.
"""
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, BackgroundTasks, status

from app.models.request_models import ForecastStartRequest, ForecastWithDateRequest, NewAssetRequest
from app.models.response_models import (
    ForecastStartResponse,
    ForecastStatusResponse,
    NewAssetResponse,
    ErrorResponse
)
from app.services.job_manager import job_manager
from app.services.forecast_service import forecast_service
from app.services.thingsboard_client import ThingsBoardClient
from app.utils.logger import logger
from app.utils.config import settings

router = APIRouter()


def _yesterday_date_range_iso() -> tuple[str, str]:
    local_tz = ZoneInfo(settings.TZ_LOCAL)
    yesterday = (datetime.now(local_tz) - timedelta(days=1)).date()
    iso_day = yesterday.isoformat()
    return iso_day, iso_day


@router.post(
    "/forecast/start",
    response_model=ForecastStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Forecast Job",
    description="Trigger a long-running forecast job. Returns immediately with job ID.",
    tags=["Forecast"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Asset not found"}
    }
)
async def start_forecast(
    request: ForecastStartRequest,
    background_tasks: BackgroundTasks
) -> ForecastStartResponse:
    """
    Start a long-running forecast job for a main asset and all its related assets.
    
    The job runs in the background and does not block this request.
    Use the /forecast/status/{job_id} endpoint to check progress.
    
    Args:
            request: Request containing asset_id and already_have flag
        background_tasks: FastAPI background tasks manager
        
    Returns:
        ForecastStartResponse with job_id and status
        
    Raises:
        HTTPException 400: If asset_id is missing or invalid
        HTTPException 404: If asset does not exist in ThingsBoard
    """
    try:
        # Validate asset_id is not empty
        if not request.asset_id or not request.asset_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ASSET_ID_REQUIRED",
                    "message": "asset_id must be provided in the request body"
                }
            )

        logger.info(
            f"Received forecast request for asset: {request.asset_id} | already_have={request.already_have}"
        )

        effective_start, effective_end = _yesterday_date_range_iso()
        
        # Check if asset exists in ThingsBoard
        async with ThingsBoardClient() as tb_client:
            exists = await tb_client.asset_exists(request.asset_id)
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "ASSET_NOT_FOUND",
                        "message": "The provided asset_id does not exist in ThingsBoard",
                        "asset_id": request.asset_id
                    }
                )
        
        # Create job
        job_id = await job_manager.create_job(
            request.asset_id,
            request.already_have,
            effective_start,
            effective_end
        )
        
        # Schedule background task
        background_tasks.add_task(
            forecast_service.run_forecast_for_main_asset,
            job_id,
            request.asset_id,
            request.already_have
        )
        
        logger.info(f"Forecast job {job_id} started in background")
        
        return ForecastStartResponse(
            job_id=job_id,
            status="started",
            asset_id=request.asset_id,
            date_range={"start_date": effective_start, "end_date": effective_end},
            already_have=request.already_have
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start forecast job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start forecast job: {str(e)}"
        )


@router.post(
    "/forecast/start-date",
    response_model=ForecastStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Forecast Job for a Specific Date",
    description="Trigger a forecast job for a single date. Returns immediately with job ID.",
    tags=["Forecast"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or date format"},
        404: {"model": ErrorResponse, "description": "Asset not found"}
    }
)
async def start_forecast_with_date(
    request: ForecastWithDateRequest,
    background_tasks: BackgroundTasks
) -> ForecastStartResponse:
    """
    Start a forecast job for a main asset on a given date.

    The job runs in the background. Use /forecast/status/{job_id} to check progress.
    """
    try:
        if not request.asset_id or not request.asset_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ASSET_ID_REQUIRED",
                    "message": "asset_id must be provided in the request body"
                }
            )

        try:
            date_obj = date.fromisoformat(request.date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_DATE_FORMAT",
                    "message": "date must be in YYYY-MM-DD format"
                }
            )

        local_tz = ZoneInfo(settings.TZ_LOCAL)
        start_dt = datetime(date_obj.year, date_obj.month, date_obj.day, tzinfo=local_tz)
        end_dt = datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59, tzinfo=local_tz)

        logger.info(
            f"Received single-date forecast request for asset: {request.asset_id} | "
            f"{request.date} | already_have={request.already_have}"
        )

        async with ThingsBoardClient() as tb_client:
            exists = await tb_client.asset_exists(request.asset_id)
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "ASSET_NOT_FOUND",
                        "message": "The provided asset_id does not exist in ThingsBoard",
                        "asset_id": request.asset_id
                    }
                )

        job_id = await job_manager.create_job(
            request.asset_id,
            request.already_have,
            request.date,
            request.date
        )

        background_tasks.add_task(
            forecast_service.run_forecast_for_main_asset,
            job_id,
            request.asset_id,
            request.already_have,
            start_dt,
            end_dt
        )

        logger.info(f"Single-date forecast job {job_id} started in background")

        return ForecastStartResponse(
            job_id=job_id,
            status="started",
            asset_id=request.asset_id,
            date_range={"start_date": request.date, "end_date": request.date},
            already_have=request.already_have
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start single-date forecast job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start forecast job: {str(e)}"
        )


@router.get(
    "/forecast/status/{job_id}",
    response_model=ForecastStatusResponse,
    summary="Get Forecast Job Status",
    description="Check the status and progress of a forecast job.",
    tags=["Forecast"]
)
async def get_forecast_status(job_id: str) -> ForecastStatusResponse:
    """
    Get the current status of a forecast job.
    
    Args:
        job_id: Job ID returned from /forecast/start
        
    Returns:
        ForecastStatusResponse with job status and progress
        
    Raises:
        HTTPException: If job not found
    """
    try:
        job = await job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        return ForecastStatusResponse(**job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job status for {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}"
        )


@router.post(
    "/forecast/new-asset",
    response_model=NewAssetResponse,
    summary="Process New Asset",
    description="Process a single new asset and write forecast telemetry.",
    tags=["Forecast"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Asset not found"},
        422: {"model": ErrorResponse, "description": "Asset exists but missing required attributes"}
    }
)
async def process_new_asset(request: NewAssetRequest) -> NewAssetResponse:
    """
    Process a single new asset that was recently added.
    
    This endpoint runs synchronously and returns when processing is complete.
    It's designed for processing individual new devices/assets.
    
    Args:
        request: Request containing asset_id
        
    Returns:
        NewAssetResponse with processing status
        
    Raises:
        HTTPException 400: If asset_id is missing or invalid
        HTTPException 404: If asset does not exist
        HTTPException 422: If asset exists but missing required attributes
    """
    try:
        # Validate asset_id is not empty
        if not request.asset_id or not request.asset_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ASSET_ID_REQUIRED",
                    "message": "asset_id must be provided in the request body"
                }
            )

        logger.info(f"Processing new asset: {request.asset_id}")

        effective_start, _ = _yesterday_date_range_iso()
        
        result = await forecast_service.process_new_asset(
            request.asset_id,
            request.already_have
        )

        if result.get("status") in {"telemetry_written", "failed"}:
            result["message"] = f"{result.get('message', '')} | effective_date={effective_start}".strip()
        
        # Handle different error cases
        if result.get("status") == "error":
            if result.get("error") == "ASSET_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "ASSET_NOT_FOUND",
                        "message": result.get("message"),
                        "asset_id": request.asset_id
                    }
                )
            elif result.get("error") == "ASSET_MISSING_ATTRIBUTES":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": "ASSET_MISSING_ATTRIBUTES",
                        "message": result.get("message"),
                        "asset_id": request.asset_id,
                        "missing_attributes": result.get("missing_attributes", [])
                    }
                )

        return NewAssetResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process new asset {request.asset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process new asset: {str(e)}"
        )
