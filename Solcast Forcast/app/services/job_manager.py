"""
Job manager for tracking forecast job status.
In-memory implementation with easy migration path to Redis.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4
from enum import Enum

from app.utils.logger import logger


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobInfo:
    """Information about a forecast job."""
    
    def __init__(self, job_id: str, main_asset_id: str, already_have: bool, start_date: str, end_date: str):
        self.job_id = job_id
        self.main_asset_id = main_asset_id
        self.already_have = already_have
        self.start_date = start_date
        self.end_date = end_date
        self.status = JobStatus.PENDING
        self.progress: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.assets_processed: int = 0
        self.total_assets: Optional[int] = None
        self.successful_assets: int = 0
        self.failed_assets: int = 0
        self.skipped_assets: int = 0
        self.current_step: Optional[str] = None
        self.errors: list = []  # List of asset-level errors
    
    def to_dict(self) -> Dict:
        """Convert job info to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "asset_id": self.main_asset_id,
            "already_have": self.already_have,
            "date_range": {
                "start_date": self.start_date,
                "end_date": self.end_date
            },
            "progress": self.progress,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "total_assets": self.total_assets,
            "processed_assets": self.assets_processed,
            "successful_assets": self.successful_assets,
            "failed_assets": self.failed_assets,
            "skipped_assets": self.skipped_assets,
            "current_step": self.current_step,
            "errors": self.errors
        }


class JobManager:
    """
    Manages forecast job tracking and status updates.
    
    This is an in-memory implementation that can be easily replaced
    with Redis for distributed/production environments.
    """
    
    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = asyncio.Lock()
    
    async def create_job(self, main_asset_id: str, already_have: bool, start_date: str, end_date: str) -> str:
        """
        Create a new forecast job.
        
        Args:
            main_asset_id: Main asset ID for the job
            already_have: Whether asset already has historical data
            start_date: Forecast start date (ISO-8601)
            end_date: Forecast end date (ISO-8601)
            
        Returns:
            Job ID
        """
        job_id = str(uuid4())
        
        async with self._lock:
            job_info = JobInfo(job_id, main_asset_id, already_have, start_date, end_date)
            job_info.started_at = datetime.now()
            job_info.updated_at = datetime.now()
            self._jobs[job_id] = job_info
        
        logger.info(f"Created job {job_id} for asset {main_asset_id}")
        return job_id
    
    async def get_job(self, job_id: str) -> Optional[JobInfo]:
        """
        Get job information by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            JobInfo object or None if not found
        """
        async with self._lock:
            return self._jobs.get(job_id)
    
    async def update_job_status(
        self, 
        job_id: str, 
        status: JobStatus,
        progress: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update job status and progress.
        
        Args:
            job_id: Job ID
            status: New job status
            progress: Progress message
            error: Error message (if failed)
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                logger.warning(f"Attempted to update non-existent job {job_id}")
                return
            
            job.status = status
            job.updated_at = datetime.now()
            
            if progress:
                job.progress = progress
            
            if error:
                job.error = error
            
            if status == JobStatus.COMPLETED or status == JobStatus.FAILED:
                job.completed_at = datetime.now()
        
        logger.info(f"Job {job_id} status updated to {status.value}")
    
    async def update_job_progress(
        self,
        job_id: str,
        assets_processed: Optional[int] = None,
        total_assets: Optional[int] = None,
        progress_message: Optional[str] = None,
        successful: Optional[int] = None,
        failed: Optional[int] = None,
        skipped: Optional[int] = None,
        current_step: Optional[str] = None
    ) -> None:
        """
        Update job progress metrics.
        
        Args:
            job_id: Job ID
            assets_processed: Number of assets processed so far
            total_assets: Total number of assets to process
            progress_message: Custom progress message
            successful: Number of successful assets
            failed: Number of failed assets
            skipped: Number of skipped assets
            current_step: Current processing step
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            if assets_processed is not None:
                job.assets_processed = assets_processed
            
            if total_assets is not None:
                job.total_assets = total_assets
            
            if progress_message:
                job.progress = progress_message
            
            if successful is not None:
                job.successful_assets = successful
            
            if failed is not None:
                job.failed_assets = failed
            
            if skipped is not None:
                job.skipped_assets = skipped
            
            if current_step:
                job.current_step = current_step
            
            job.updated_at = datetime.now()
        
        logger.debug(f"Job {job_id} progress: {assets_processed}/{total_assets} (success: {successful}, failed: {failed})")
    
    async def add_job_error(
        self,
        job_id: str,
        asset_id: str,
        error_message: str,
        missing_attributes: Optional[list] = None
    ) -> None:
        """Add an asset-level error to the job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            
            error_record = {
                "asset_id": asset_id,
                "error": error_message
            }
            
            if missing_attributes:
                error_record["missing_attributes"] = missing_attributes
            
            job.errors.append(error_record)
            job.updated_at = datetime.now()
        
        logger.warning(f"Job {job_id} - Asset {asset_id} error: {error_message}")
    
    async def mark_running(self, job_id: str) -> None:
        """Mark job as running."""
        await self.update_job_status(job_id, JobStatus.RUNNING, progress="Job started")
    
    async def mark_completed(self, job_id: str) -> None:
        """Mark job as completed."""
        await self.update_job_status(job_id, JobStatus.COMPLETED, progress="Job completed successfully")
    
    async def mark_failed(self, job_id: str, error: str) -> None:
        """Mark job as failed."""
        await self.update_job_status(job_id, JobStatus.FAILED, error=error)
    
    async def list_jobs(self) -> Dict[str, JobInfo]:
        """
        List all jobs.
        
        Returns:
            Dictionary of job_id -> JobInfo
        """
        async with self._lock:
            return dict(self._jobs)
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove old completed/failed jobs.
        
        Args:
            max_age_hours: Maximum age in hours for completed jobs
            
        Returns:
            Number of jobs cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned = 0
        
        async with self._lock:
            jobs_to_remove = []
            
            for job_id, job in self._jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    if job.completed_at and job.completed_at < cutoff_time:
                        jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                cleaned += 1
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old jobs")
        
        return cleaned


# Global job manager instance
job_manager = JobManager()
