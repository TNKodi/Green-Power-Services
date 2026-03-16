"""
Forecast service that orchestrates the power prediction workflow.
Integrates with existing power prediction logic from Scripts/power_predicition.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

# Add the scripts directory to Python path to import existing modules
scripts_path = Path(__file__).parent.parent.parent / "Scripts" / "power_predicition"
sys.path.insert(0, str(scripts_path))

from power import power_prediction
from app.services.thingsboard_client import ThingsBoardClient
from app.services.job_manager import job_manager, JobStatus
from app.utils.logger import logger
from app.utils.config import settings


class ForecastService:
    """
    Service for executing power forecasts on assets.
    """
    
    # Required attributes for successful forecast
    REQUIRED_ATTRIBUTES = [
        "latitude",
        "longitude",
        "orientation",
        "pv_module_area",
        "inverter_power"
    ]

    REQUIRED_NUMERIC_ATTRIBUTES = [
        "latitude",
        "longitude",
        "pv_module_area",
        "inverter_power"
    ]
    
    def __init__(self):
        pass
    
    def validate_asset_attributes(self, attributes: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that asset has all required attributes.
        
        Args:
            attributes: Asset attributes dictionary
            
        Returns:
            Tuple of (is_valid, missing_attributes)
        """
        issues: List[str] = []

        def _is_missing(value: Any) -> bool:
            return value is None or (isinstance(value, str) and not value.strip())

        def _is_numeric(value: Any) -> bool:
            try:
                float(value)
                return True
            except (TypeError, ValueError):
                return False

        for attr in self.REQUIRED_ATTRIBUTES:
            if attr not in attributes or _is_missing(attributes[attr]):
                issues.append(f"{attr}: missing")

        for attr in self.REQUIRED_NUMERIC_ATTRIBUTES:
            if attr in attributes and not _is_missing(attributes[attr]) and not _is_numeric(attributes[attr]):
                issues.append(f"{attr}: must be numeric")

        orientation = attributes.get("orientation")
        if "orientation" in attributes and not _is_missing(orientation):
            if not isinstance(orientation, list) or len(orientation) == 0:
                issues.append("orientation: must be a non-empty list")
            else:
                for idx, orient in enumerate(orientation):
                    if not isinstance(orient, dict):
                        issues.append(f"orientation[{idx}]: must be an object")
                        continue

                    module_count = orient.get("module_count")
                    tilt = orient.get("tilt")
                    azimuth = orient.get("azimuth")

                    if _is_missing(module_count):
                        issues.append(f"orientation[{idx}].module_count: missing")
                    else:
                        try:
                            if int(module_count) <= 0:
                                issues.append(f"orientation[{idx}].module_count: must be > 0")
                        except (TypeError, ValueError):
                            issues.append(f"orientation[{idx}].module_count: must be an integer")

                    if _is_missing(tilt):
                        issues.append(f"orientation[{idx}].tilt: missing")
                    elif not _is_numeric(tilt):
                        issues.append(f"orientation[{idx}].tilt: must be numeric")

                    if _is_missing(azimuth):
                        issues.append(f"orientation[{idx}].azimuth: missing")
                    elif not _is_numeric(azimuth):
                        issues.append(f"orientation[{idx}].azimuth: must be numeric")

        return len(issues) == 0, issues

    def _normalize_bounds_for_index(self, index: pd.DatetimeIndex, start_dt, end_dt):
        """
        Normalize start/end datetimes to be compatible with a DatetimeIndex timezone.
        """
        start_ts = pd.Timestamp(start_dt)
        end_ts = pd.Timestamp(end_dt)

        if index.tz is not None:
            if start_ts.tzinfo is None:
                start_ts = start_ts.tz_localize(index.tz)
            else:
                start_ts = start_ts.tz_convert(index.tz)

            if end_ts.tzinfo is None:
                end_ts = end_ts.tz_localize(index.tz)
            else:
                end_ts = end_ts.tz_convert(index.tz)
        else:
            if start_ts.tzinfo is not None:
                start_ts = start_ts.tz_localize(None)
            if end_ts.tzinfo is not None:
                end_ts = end_ts.tz_localize(None)

        return start_ts, end_ts
    
    async def process_single_asset(
        self, 
        asset_id: str,
        tb_client: ThingsBoardClient,
        start_dt,
        end_dt,
        already_have: bool,
        job_id: Optional[str] = None
    ) -> tuple[bool, Optional[str], Optional[List[str]], Optional[List[Dict[str, Any]]]]:
        """
        Process a single asset: read attributes, run forecast, write telemetry.
        
        Args:
            asset_id: Asset ID to process
            tb_client: ThingsBoard client instance
            job_id: Optional job ID for tracking
            
        Returns:
            Tuple of (success, error_message, missing_attributes, telemetry_records)
        """
        try:
            logger.info(f"Processing asset {asset_id}")
            
            # Step 1: Read device attributes
            logger.debug(f"Reading attributes for {asset_id}")
            attributes = await tb_client.read_device_attributes(asset_id)
            
            if not attributes:
                logger.warning(f"No attributes found for {asset_id}, skipping")
                return False, "no_attributes_found", None, None
            
            logger.info(f"Retrieved {len(attributes)} attributes for {asset_id}")
            
            # Step 2: Validate attributes
            is_valid, attribute_issues = self.validate_asset_attributes(attributes)
            if not is_valid:
                logger.warning(f"Asset {asset_id} has attribute errors: {attribute_issues}")
                return False, "missing_required_attributes", attribute_issues, None

            # Step 3: Historical data requirement when already_have is True
            if already_have:
                has_history = await tb_client.has_historical_data(asset_id, start_dt, end_dt)
                if not has_history:
                    logger.warning(
                        f"Asset {asset_id} lacks historical data in requested range; "
                        "continuing with forecast-only generation"
                    )
            
            # Step 4: Run power prediction (synchronous call to existing code)
            logger.info(f"Running power prediction for {asset_id}")
            try:
                daily_power, total_energy = power_prediction(
                    attributes,
                    start_date=start_dt.date().isoformat(),
                    end_date=end_dt.date().isoformat(),
                )
                # Filter to requested date range if possible
                if isinstance(daily_power.index, pd.DatetimeIndex):
                    start_bound, end_bound = self._normalize_bounds_for_index(daily_power.index, start_dt, end_dt)
                    daily_power = daily_power.loc[(daily_power.index >= start_bound) & (daily_power.index <= end_bound)]
                logger.info(f"Prediction completed for {asset_id}: {total_energy:.2f} kWh total")
            except Exception as e:
                logger.error(f"Power prediction failed for {asset_id}: {e}")
                return False, f"forecast_calculation_error: {str(e)}", None, None
            
            # Step 5: Write telemetry to ThingsBoard
            logger.info(f"Writing telemetry for {asset_id}")
            telemetry_records = self._prepare_telemetry(daily_power, asset_id, start_dt, end_dt)
            
            if telemetry_records:
                try:
                    await tb_client.write_bulk_telemetry(asset_id, telemetry_records)
                    logger.info(f"Successfully wrote {len(telemetry_records)} telemetry records for {asset_id}")
                except Exception as e:
                    logger.error(f"Telemetry write failed for {asset_id}: {e}")
                    return False, f"telemetry_write_failed: {str(e)}", None, telemetry_records
            else:
                logger.warning(f"No telemetry records to write for {asset_id}")
            
            return True, None, None, telemetry_records
            
        except Exception as e:
            logger.error(f"Failed to process asset {asset_id}: {e}", exc_info=True)
            return False, f"unexpected_error: {str(e)}", None, None

    def _sum_telemetry_records(self, telemetry_batches: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Sum multiple telemetry record lists by timestamp.

        Args:
            telemetry_batches: List of telemetry record lists

        Returns:
            Summed telemetry list sorted by timestamp
        """
        totals_by_ts: Dict[int, float] = {}

        for records in telemetry_batches:
            for record in records:
                ts = record.get("ts")
                if ts is None:
                    continue
                value = float(record.get("values", {}).get("daily_energy_kwh_forecast", 0.0))
                totals_by_ts[ts] = totals_by_ts.get(ts, 0.0) + value

        return [
            {
                "ts": ts,
                "values": {
                    "daily_energy_kwh_forecast": value
                }
            }
            for ts, value in sorted(totals_by_ts.items())
        ]
    
    def _prepare_telemetry(
        self, 
        daily_power: pd.DataFrame, 
        asset_id: str,
        start_dt,
        end_dt
    ) -> List[Dict[str, Any]]:
        """
        Prepare telemetry records from daily power DataFrame.
        
        Args:
            daily_power: DataFrame with daily energy predictions
            asset_id: Asset ID (for logging)
            
        Returns:
            List of telemetry records
        """
        telemetry_list = []
        
        try:
            # Apply date filtering just in case upstream did not filter
            if isinstance(daily_power.index, pd.DatetimeIndex):
                start_bound, end_bound = self._normalize_bounds_for_index(daily_power.index, start_dt, end_dt)
                daily_power = daily_power.loc[(daily_power.index >= start_bound) & (daily_power.index <= end_bound)]

            # Get the energy column (first column typically contains energy_kwh)
            if 'energy_kwh' in daily_power.columns:
                energy_column = 'energy_kwh'
            else:
                # Use first column
                energy_column = daily_power.columns[0]
            
            for i in range(len(daily_power)):
                timestamp = daily_power.index[i]
                energy_value = daily_power.iloc[i][energy_column]
                
                # Convert timestamp to milliseconds
                ts_ms = int(timestamp.timestamp() * 1000)
                
                telemetry_record = {
                    "ts": ts_ms,
                    "values": {
                        "daily_energy_kwh_forecast": float(energy_value)
                    }
                }
                
                telemetry_list.append(telemetry_record)
            
            logger.debug(f"Prepared {len(telemetry_list)} telemetry records for {asset_id}")
            
        except Exception as e:
            logger.error(f"Error preparing telemetry for {asset_id}: {e}")
        
        return telemetry_list
    
    async def run_forecast_for_main_asset(
        self,
        job_id: str,
        main_asset_id: str,
        already_have: bool,
        start_dt,
        end_dt
    ) -> None:
        """
        Execute forecast workflow for a main asset and all its children.
        This is the long-running background task.
        
        Args:
            job_id: Job ID for tracking
            main_asset_id: Main asset ID to start from
            already_have: Whether historical data exists
            start_dt: Start date for forecast
            end_dt: End date for forecast
        """
        try:
            logger.info(
                f"Starting forecast job {job_id} for main asset {main_asset_id} | "
                f"already_have={already_have} | start={start_dt.isoformat()} end={end_dt.isoformat()}"
            )
            
            # Mark job as running
            await job_manager.mark_running(job_id)
            
            async with ThingsBoardClient() as tb_client:
                # Step 1: Build hierarchy up to configured target level (supports level 4+)
                logger.info(f"Retrieving hierarchy from {main_asset_id}")
                await job_manager.update_job_progress(
                    job_id,
                    progress_message="Retrieving asset hierarchy"
                )

                target_level = max(2, settings.DEFAULT_TARGET_LEVEL)
                level_assets: Dict[int, List[str]] = {}
                parent_to_children: Dict[Tuple[int, str], List[str]] = {}

                level_assets[2] = list(dict.fromkeys(await tb_client.get_asset_relations(main_asset_id)))
                for level in range(3, target_level + 1):
                    previous_level_assets = level_assets.get(level - 1, [])
                    if not previous_level_assets:
                        level_assets[level] = []
                        continue

                    current_level_assets: List[str] = []
                    for parent_asset_id in previous_level_assets:
                        children = list(dict.fromkeys(await tb_client.get_asset_relations(parent_asset_id)))
                        parent_to_children[(level - 1, parent_asset_id)] = children
                        current_level_assets.extend(children)

                    level_assets[level] = list(dict.fromkeys(current_level_assets))

                deepest_level = 0
                deepest_assets: List[str] = []
                for level in range(target_level, 1, -1):
                    assets_at_level = level_assets.get(level, [])
                    if assets_at_level:
                        deepest_level = level
                        deepest_assets = assets_at_level
                        break

                if deepest_level == 0:
                    logger.warning(
                        f"No descendant assets found under main asset {main_asset_id} up to level {target_level}"
                    )
                    await job_manager.mark_completed(job_id)
                    return

                hierarchy_counts = ", ".join(
                    [f"L{level}={len(level_assets.get(level, []))}" for level in range(2, target_level + 1)]
                )
                logger.info(
                    f"Hierarchy resolved for {main_asset_id}: target_level={target_level}, {hierarchy_counts}, "
                    f"processing_deepest_level=L{deepest_level}"
                )

                await job_manager.update_job_progress(
                    job_id,
                    total_assets=len(deepest_assets),
                    assets_processed=0,
                    successful=0,
                    failed=0,
                    skipped=0,
                    progress_message=f"Processing {len(deepest_assets)} level-{deepest_level} assets",
                    current_step="asset_traversal_complete"
                )

                # Step 2: Process each deepest-level asset
                successful = 0
                failed = 0
                skipped = 0
                telemetry_by_level: Dict[int, Dict[str, List[Dict[str, Any]]]] = {deepest_level: {}}

                for idx, asset_id in enumerate(deepest_assets, 1):
                    asset_name = await tb_client.get_entity_name("ASSET", asset_id)
                    logger.info(
                        f"Processing level-{deepest_level} asset {idx}/{len(deepest_assets)}: "
                        f"{asset_name} ({asset_id})"
                    )

                    await job_manager.update_job_progress(
                        job_id,
                        current_step=f"processing_level{deepest_level}_asset_{idx}"
                    )

                    success, error_msg, missing_attrs, telemetry_records = await self.process_single_asset(
                        asset_id, tb_client, start_dt, end_dt, already_have, job_id
                    )

                    if success:
                        successful += 1
                        telemetry_by_level[deepest_level][asset_id] = telemetry_records or []
                    elif error_msg and ("missing_required_attributes" in error_msg or "historical_data_not_available" in error_msg):
                        skipped += 1
                        await job_manager.add_job_error(job_id, asset_id, error_msg, missing_attrs)
                    else:
                        failed += 1
                        await job_manager.add_job_error(job_id, asset_id, error_msg or "unknown_error")

                    await job_manager.update_job_progress(
                        job_id,
                        assets_processed=idx,
                        successful=successful,
                        failed=failed,
                        skipped=skipped,
                        progress_message=f"Processed {idx}/{len(deepest_assets)} (success: {successful}, failed: {failed}, skipped: {skipped})"
                    )

                # Step 3: Roll up from deepest level down to level 2 assets
                asset_rollup_assets_written = 0
                asset_rollup_records_written = 0
                for parent_level in range(deepest_level - 1, 1, -1):
                    await job_manager.update_job_progress(
                        job_id,
                        progress_message=f"Rolling up Level {parent_level + 1} forecast sums to Level {parent_level}",
                        current_step=f"rollup_level{parent_level + 1}_to_level{parent_level}"
                    )

                    current_level_telemetry: Dict[str, List[Dict[str, Any]]] = {}
                    for parent_asset_id in level_assets.get(parent_level, []):
                        parent_asset_name = await tb_client.get_entity_name("ASSET", parent_asset_id)
                        children = parent_to_children.get((parent_level, parent_asset_id), [])
                        child_telemetry_map = telemetry_by_level.get(parent_level + 1, {})
                        child_batches = [
                            child_telemetry_map[child_id]
                            for child_id in children
                            if child_id in child_telemetry_map and child_telemetry_map[child_id]
                        ]

                        if not child_batches:
                            logger.warning(
                                f"No successful level-{parent_level + 1} telemetry to roll up for level-{parent_level} asset "
                                f"{parent_asset_name} ({parent_asset_id})"
                            )
                            continue

                        summed_parent = self._sum_telemetry_records(child_batches)
                        if not summed_parent:
                            continue

                        try:
                            await tb_client.write_bulk_telemetry(parent_asset_id, summed_parent)
                            current_level_telemetry[parent_asset_id] = summed_parent
                            asset_rollup_assets_written += 1
                            asset_rollup_records_written += len(summed_parent)
                            logger.info(
                                f"Rolled up {len(children)} level-{parent_level + 1} assets into level-{parent_level} asset "
                                f"{parent_asset_name} ({parent_asset_id})"
                            )
                        except Exception as e:
                            failed += 1
                            await job_manager.add_job_error(
                                job_id, parent_asset_id, f"level{parent_level}_rollup_write_failed: {str(e)}"
                            )
                            logger.error(
                                f"Failed level-{parent_level} rollup write for {parent_asset_name} ({parent_asset_id}): {e}"
                            )

                    telemetry_by_level[parent_level] = current_level_telemetry

                # Step 4: Roll up Level 2 sums to main asset (level 1)
                await job_manager.update_job_progress(
                    job_id,
                    progress_message="Rolling up Level 2 forecast sums to Level 1",
                    current_step="rollup_level2_to_level1"
                )

                level2_telemetry_map = telemetry_by_level.get(2, {})
                level2_batches = [records for records in level2_telemetry_map.values() if records]
                level1_rollup_records_written = 0
                level1_rollup_payload: List[Dict[str, Any]] = []
                if level2_batches:
                    summed_level1 = self._sum_telemetry_records(level2_batches)
                    try:
                        await tb_client.write_bulk_telemetry(main_asset_id, summed_level1)
                        level1_rollup_records_written = len(summed_level1)
                        level1_rollup_payload = summed_level1
                        level1_asset_name = await tb_client.get_entity_name("ASSET", main_asset_id)
                        logger.info(
                            f"Rolled up {len(level2_batches)} level-2 assets into level-1 asset "
                            f"{level1_asset_name} ({main_asset_id})"
                        )
                    except Exception as e:
                        failed += 1
                        await job_manager.add_job_error(
                            job_id, main_asset_id, f"level1_rollup_write_failed: {str(e)}"
                        )
                        logger.error(f"Failed level-1 rollup write for {main_asset_id}: {e}")
                else:
                    logger.warning(f"No level-2 telemetry available for rollup to level-1 asset {main_asset_id}")

                # Step 5: Roll up Level 1 sum to Level 0 sending devices (DEVICE entities)
                await job_manager.update_job_progress(
                    job_id,
                    progress_message="Rolling up Level 1 forecast sums to Level 0 sending device",
                    current_step="rollup_level1_to_level0_device"
                )

                level0_devices_written = 0
                level0_records_written = 0
                if level1_rollup_payload:
                    level0_devices = await tb_client.get_device_relations(main_asset_id)
                    if level0_devices:
                        for level0_device_id in level0_devices:
                            try:
                                await tb_client.write_bulk_telemetry_to_entity(
                                    "DEVICE",
                                    level0_device_id,
                                    level1_rollup_payload
                                )
                                level0_devices_written += 1
                                level0_records_written += len(level1_rollup_payload)
                                level0_device_name = await tb_client.get_entity_name("DEVICE", level0_device_id)
                                logger.info(
                                    f"Rolled up level-1 asset {main_asset_id} into level-0 sending device "
                                    f"{level0_device_name} ({level0_device_id})"
                                )
                            except Exception as e:
                                failed += 1
                                await job_manager.add_job_error(
                                    job_id, level0_device_id, f"level0_device_rollup_write_failed: {str(e)}"
                                )
                                logger.error(f"Failed level-0 device rollup write for {level0_device_id}: {e}")
                    else:
                        logger.warning(f"No level-0 sending devices found under main asset {main_asset_id}")
                else:
                    logger.warning(
                        f"Skipping level-0 sending device rollup because level-1 rollup payload is empty for {main_asset_id}"
                    )

                rollup_summary = (
                    f"Roll-up summary: target_level={target_level}, processed_level={deepest_level}, "
                    f"asset_rollup_assets_written={asset_rollup_assets_written}, "
                    f"asset_rollup_records_written={asset_rollup_records_written}, "
                    f"level1_records_written={level1_rollup_records_written}, "
                    f"level0_devices_written={level0_devices_written}, "
                    f"level0_records_written={level0_records_written}"
                )
                await job_manager.update_job_progress(
                    job_id,
                    progress_message=rollup_summary,
                    current_step="rollup_complete"
                )
                logger.info(f"Job {job_id} {rollup_summary}")

                # Step 6: Mark job as completed
                logger.info(f"Forecast job {job_id} completed: {successful} successful, {failed} failed, {skipped} skipped")
                await job_manager.mark_completed(job_id)
                
        except Exception as e:
            error_msg = f"Forecast job {job_id} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await job_manager.mark_failed(job_id, error_msg)
    
    async def process_new_asset(self, asset_id: str, already_have: bool, start_dt, end_dt) -> Dict[str, Any]:
        """
        Process a single new asset (synchronous execution).
        
        Args:
            asset_id: Asset ID to process
            already_have: Whether asset already has historical data
            start_dt: Start date for forecast
            end_dt: End date for forecast
            
        Returns:
            Result dictionary with status and message
        """
        try:
            logger.info(
                f"Processing new asset {asset_id} | already_have={already_have} | "
                f"start={start_dt.isoformat()} end={end_dt.isoformat()}"
            )
            
            async with ThingsBoardClient() as tb_client:
                # Check if asset exists
                exists = await tb_client.asset_exists(asset_id)
                if not exists:
                    return {
                        "status": "error",
                        "asset_id": asset_id,
                        "error": "ASSET_NOT_FOUND",
                        "message": "The provided asset_id does not exist in ThingsBoard"
                    }
                
                success, error_msg, missing_attrs, _ = await self.process_single_asset(
                    asset_id, tb_client, start_dt, end_dt, already_have
                )
                
                if success:
                    return {
                        "status": "telemetry_written",
                        "asset_id": asset_id,
                        "message": "Successfully processed new asset"
                    }
                elif error_msg and "missing_required_attributes" in error_msg:
                    return {
                        "status": "error",
                        "asset_id": asset_id,
                        "error": "ASSET_MISSING_ATTRIBUTES",
                        "message": "Asset exists but required attributes are missing",
                        "missing_attributes": missing_attrs or []
                    }
                else:
                    return {
                        "status": "failed",
                        "asset_id": asset_id,
                        "message": error_msg or "Failed to process asset"
                    }
                    
        except Exception as e:
            logger.error(f"Error processing new asset {asset_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "asset_id": asset_id,
                "message": str(e)
            }


# Global forecast service instance
forecast_service = ForecastService()
