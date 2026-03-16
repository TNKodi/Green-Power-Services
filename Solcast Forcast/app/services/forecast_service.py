"""
Forecast service that orchestrates the power prediction workflow.
Integrates with existing power prediction logic from Scripts/power_predicition.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import math
from statistics import median
from zoneinfo import ZoneInfo
import pandas as pd

# Add the scripts directory to Python path to import existing modules
scripts_path = Path(__file__).parent.parent.parent / "Scripts" / "power_predicition"
sys.path.insert(0, str(scripts_path))

from Scripts.power_predicition.power import power_prediction
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
    TELEMETRY_KEY = "active_power_solcast"
    DAILY_TELEMETRY_KEY = "solcast_daily"
    
    def __init__(self):
        pass

    def _to_telemetry_timestamp_ms(self, timestamp: Any) -> int:
        """
        Convert a timestamp to local timezone and return epoch milliseconds.
        """
        ts = pd.Timestamp(timestamp)
        local_tz = ZoneInfo(settings.TZ_LOCAL)

        if ts.tzinfo is None:
            ts = ts.tz_localize(local_tz)
        else:
            ts = ts.tz_convert(local_tz)
        return int(ts.timestamp() * 1000)

    def _default_interval_hours(self) -> float:
        period = str(getattr(settings, "SOLCAST_PERIOD", "PT5M")).strip().upper()
        if period.startswith("PT") and period.endswith("M"):
            minutes = period[2:-1]
            if minutes.isdigit() and int(minutes) > 0:
                return int(minutes) / 60.0
        if period.startswith("PT") and period.endswith("H"):
            hours = period[2:-1]
            if hours.isdigit() and int(hours) > 0:
                return float(int(hours))
        return 5.0 / 60.0

    def _restamp_to_requested_date(
        self, df: pd.DataFrame, requested_start_dt
    ) -> pd.DataFrame:
        """
        Shift the DataFrame index by whole days so the first entry falls on the
        requested date.  Time-of-day is preserved; only the date component is
        corrected.  No-op when the data already lands on the right date.
        """
        if not isinstance(df.index, pd.DatetimeIndex) or len(df) == 0:
            return df

        local_tz = ZoneInfo(settings.TZ_LOCAL)
        requested_date = pd.Timestamp(requested_start_dt)
        if requested_date.tzinfo is None:
            requested_date = requested_date.tz_localize(local_tz)
        else:
            requested_date = requested_date.tz_convert(local_tz)
        requested_date = requested_date.normalize()  # midnight of requested day

        first_ts = df.index[0]
        if first_ts.tzinfo is not None:
            first_date = first_ts.tz_convert(local_tz).normalize()
        else:
            first_date = first_ts.normalize()

        day_offset = requested_date - first_date
        if day_offset != pd.Timedelta(0):
            df = df.copy()
            df.index = df.index + day_offset
            logger.info(
                f"Restamped data by {day_offset} to align with requested date "
                f"{requested_date.date()}"
            )
        return df

    def _to_daily_write_timestamp_ms(self, timestamp: Any) -> int:
        """
        Convert a daily timestamp to local timezone and write at 01:00 local time.
        """
        ts = pd.Timestamp(timestamp)
        local_tz = ZoneInfo(settings.TZ_LOCAL)

        if ts.tzinfo is None:
            ts = ts.tz_localize(local_tz)
        else:
            ts = ts.tz_convert(local_tz)

        write_ts = ts.normalize() + pd.Timedelta(hours=1)
        return int(write_ts.timestamp() * 1000)

    def _get_yesterday_range(self) -> Tuple[datetime, datetime]:
        """
        Return yesterday start/end in local timezone.
        """
        local_tz = ZoneInfo(settings.TZ_LOCAL)
        now_local = datetime.now(local_tz)
        yesterday = (now_local - timedelta(days=1)).date()

        start_dt = datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            0,
            0,
            0,
            tzinfo=local_tz,
        )
        end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)
        return start_dt, end_dt
    
    def validate_asset_attributes(self, attributes: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that asset has all required attributes.
        
        Args:
            attributes: Asset attributes dictionary
            
        Returns:
            Tuple of (is_valid, missing_attributes)
        """
        missing = []
        for attr in self.REQUIRED_ATTRIBUTES:
            if attr not in attributes or attributes[attr] is None:
                missing.append(attr)
        
        return len(missing) == 0, missing

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
        write_telemetry: bool = True,
        job_id: Optional[str] = None
    ) -> tuple[
        bool,
        Optional[str],
        Optional[List[str]],
        Optional[List[Dict[str, Any]]],
        Optional[List[Dict[str, Any]]]
    ]:
        """
        Process a single asset: read attributes, run forecast, write telemetry.
        
        Args:
            asset_id: Asset ID to process
            tb_client: ThingsBoard client instance
            job_id: Optional job ID for tracking
            
        Returns:
            Tuple of (success, error_message, missing_attributes, interval_telemetry_records, daily_telemetry_records)
        """
        try:
            logger.info(f"Processing asset {asset_id}")
            
            # Step 1: Read device attributes
            logger.debug(f"Reading attributes for {asset_id}")
            attributes = await tb_client.read_device_attributes(asset_id)
            
            if not attributes:
                logger.warning(f"No attributes found for {asset_id}, skipping")
                return False, "no_attributes_found", None, None, None
            
            logger.info(f"Retrieved {len(attributes)} attributes for {asset_id}")
            
            # Step 2: Validate attributes
            is_valid, missing = self.validate_asset_attributes(attributes)
            if not is_valid:
                logger.warning(f"Asset {asset_id} missing required attributes: {missing}")
                return False, "missing_required_attributes", missing, None, None

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
                interval_power, daily_power, total_energy = power_prediction(
                    attributes,
                    start_date=start_dt.date().isoformat(),
                    end_date=end_dt.date().isoformat(),
                )
                # Anchor timestamps to the requested date (shift whole days if needed)
                interval_power = self._restamp_to_requested_date(interval_power, start_dt)
                daily_power = self._restamp_to_requested_date(daily_power, start_dt)
                # Filter to requested date range if possible
                if isinstance(interval_power.index, pd.DatetimeIndex):
                    start_bound, end_bound = self._normalize_bounds_for_index(interval_power.index, start_dt, end_dt)
                    interval_power = interval_power.loc[(interval_power.index >= start_bound) & (interval_power.index <= end_bound)]
                logger.info(f"Prediction completed for {asset_id}: {total_energy:.2f} kWh total")
            except Exception as e:
                logger.error(f"Power prediction failed for {asset_id}: {e}")
                return False, f"forecast_calculation_error: {str(e)}", None, None, None
            
            # Step 5: Write telemetry to ThingsBoard
            logger.info(f"Writing telemetry for {asset_id}")
            telemetry_records = self._prepare_telemetry(interval_power, asset_id, start_dt, end_dt)
            daily_telemetry_records = self._prepare_daily_telemetry(daily_power, asset_id, start_dt, end_dt)
            
            if telemetry_records and write_telemetry:
                try:
                    await tb_client.write_bulk_telemetry(asset_id, telemetry_records)
                    logger.info(f"Successfully wrote {len(telemetry_records)} telemetry records for {asset_id}")
                except Exception as e:
                    logger.error(f"Telemetry write failed for {asset_id}: {e}")
                    return False, f"telemetry_write_failed: {str(e)}", None, None, None
            else:
                logger.warning(f"No telemetry records to write for {asset_id}")

            if daily_telemetry_records and write_telemetry:
                try:
                    await tb_client.write_bulk_telemetry(asset_id, daily_telemetry_records)
                    logger.info(
                        f"Successfully wrote {len(daily_telemetry_records)} daily energy records for {asset_id}"
                    )
                except Exception as e:
                    logger.error(f"Daily telemetry write failed for {asset_id}: {e}")
                    return False, f"daily_telemetry_write_failed: {str(e)}", None, None, None
            else:
                logger.warning(f"No daily telemetry records to write for {asset_id}")
            
            return True, None, None, telemetry_records, daily_telemetry_records
            
        except Exception as e:
            logger.error(f"Failed to process asset {asset_id}: {e}", exc_info=True)
            return False, f"unexpected_error: {str(e)}", None, None, None

    def _telemetry_list_to_map(
        self,
        telemetry_list: List[Dict[str, Any]]
    ) -> Dict[int, float]:
        telemetry_map: Dict[int, float] = {}
        for row in telemetry_list:
            ts = int(row.get("ts", 0))
            value = float(row.get("values", {}).get(self.TELEMETRY_KEY, 0.0))
            telemetry_map[ts] = value
        return telemetry_map

    def _telemetry_map_to_list(self, telemetry_map: Dict[int, float]) -> List[Dict[str, Any]]:
        return [
            {
                "ts": ts,
                "values": {self.TELEMETRY_KEY: float(value)}
            }
            for ts, value in sorted(telemetry_map.items(), key=lambda item: item[0])
        ]

    def _daily_telemetry_list_to_map(
        self,
        telemetry_list: List[Dict[str, Any]]
    ) -> Dict[int, float]:
        telemetry_map: Dict[int, float] = {}
        for row in telemetry_list:
            ts = int(row.get("ts", 0))
            value = float(row.get("values", {}).get(self.DAILY_TELEMETRY_KEY, 0.0))
            telemetry_map[ts] = value
        return telemetry_map

    def _daily_telemetry_map_to_list(self, telemetry_map: Dict[int, float]) -> List[Dict[str, Any]]:
        return [
            {
                "ts": ts,
                "values": {self.DAILY_TELEMETRY_KEY: float(value)}
            }
            for ts, value in sorted(telemetry_map.items(), key=lambda item: item[0])
        ]

    def _sum_telemetry_records(
        self,
        child_telemetry_records: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        summed: Dict[int, float] = {}

        for telemetry_list in child_telemetry_records:
            child_map = self._telemetry_list_to_map(telemetry_list)
            for ts, value in child_map.items():
                summed[ts] = summed.get(ts, 0.0) + float(value)

        return self._telemetry_map_to_list(summed)

    def _sum_daily_telemetry_records(
        self,
        child_telemetry_records: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        summed: Dict[int, float] = {}

        for telemetry_list in child_telemetry_records:
            child_map = self._daily_telemetry_list_to_map(telemetry_list)
            for ts, value in child_map.items():
                summed[ts] = summed.get(ts, 0.0) + float(value)

        return self._daily_telemetry_map_to_list(summed)

    def _telemetry_total_kwh(self, telemetry_list: List[Dict[str, Any]]) -> float:
        if not telemetry_list:
            return 0.0

        sorted_rows = sorted(telemetry_list, key=lambda row: int(row.get("ts", 0)))
        timestamps = [int(row.get("ts", 0)) for row in sorted_rows]
        powers: List[float] = []
        for row in sorted_rows:
            value = float(row.get("values", {}).get(self.TELEMETRY_KEY, 0.0))
            if not math.isfinite(value):
                value = 0.0
            powers.append(value)

        if len(timestamps) > 1:
            diffs_hours = [
                (timestamps[i] - timestamps[i - 1]) / 3_600_000.0
                for i in range(1, len(timestamps))
                if timestamps[i] > timestamps[i - 1]
            ]
            dt_hours = median(diffs_hours) if diffs_hours else self._default_interval_hours()
        else:
            dt_hours = self._default_interval_hours()

        return float(sum(powers) * dt_hours)

    def _daily_telemetry_total_kwh(self, telemetry_list: List[Dict[str, Any]]) -> float:
        if not telemetry_list:
            return 0.0

        total = 0.0
        for row in telemetry_list:
            value = float(row.get("values", {}).get(self.DAILY_TELEMETRY_KEY, 0.0))
            if not math.isfinite(value):
                value = 0.0
            total += value

        return float(total)
    
    def _prepare_telemetry(
        self, 
        interval_power: pd.DataFrame,
        asset_id: str,
        start_dt,
        end_dt
    ) -> List[Dict[str, Any]]:
        """
        Prepare telemetry records from interval power DataFrame.
        
        Args:
            daily_power: DataFrame with daily energy predictions
            asset_id: Asset ID (for logging)
            
        Returns:
            List of telemetry records
        """
        telemetry_list = []
        invalid_value_count = 0
        
        try:
            # Apply date filtering just in case upstream did not filter
            if isinstance(interval_power.index, pd.DatetimeIndex):
                start_bound, end_bound = self._normalize_bounds_for_index(interval_power.index, start_dt, end_dt)
                interval_power = interval_power.loc[(interval_power.index >= start_bound) & (interval_power.index <= end_bound)]

            # Get the power column
            if 'active_power_kw' in interval_power.columns:
                power_column = 'active_power_kw'
            else:
                # Use first column
                power_column = interval_power.columns[0]
            
            for i in range(len(interval_power)):
                timestamp = interval_power.index[i]
                raw_power_value = interval_power.iloc[i][power_column]
                power_value = float(raw_power_value)
                if not math.isfinite(power_value):
                    invalid_value_count += 1
                    power_value = 0.0
                
                # Convert timestamp to milliseconds
                ts_ms = self._to_telemetry_timestamp_ms(timestamp)
                
                telemetry_record = {
                    "ts": ts_ms,
                    "values": {
                        self.TELEMETRY_KEY: float(power_value)
                    }
                }
                
                telemetry_list.append(telemetry_record)
            
            logger.debug(f"Prepared {len(telemetry_list)} telemetry records for {asset_id}")
            if invalid_value_count > 0:
                logger.warning(
                    f"Replaced {invalid_value_count} non-finite telemetry values with 0.0 for {asset_id}"
                )
            
        except Exception as e:
            logger.error(f"Error preparing telemetry for {asset_id}: {e}")
        
        return telemetry_list

    def _prepare_daily_telemetry(
        self,
        daily_power: pd.DataFrame,
        asset_id: str,
        start_dt,
        end_dt
    ) -> List[Dict[str, Any]]:
        """
        Prepare daily energy telemetry records from daily power DataFrame.
        """
        telemetry_list: List[Dict[str, Any]] = []
        invalid_value_count = 0

        try:
            if daily_power is None or daily_power.empty:
                return telemetry_list

            if isinstance(daily_power.index, pd.DatetimeIndex):
                start_bound, end_bound = self._normalize_bounds_for_index(daily_power.index, start_dt, end_dt)
                daily_power = daily_power.loc[(daily_power.index >= start_bound) & (daily_power.index <= end_bound)]

            if daily_power.empty:
                return telemetry_list

            if "energy_kwh" in daily_power.columns:
                energy_column = "energy_kwh"
            else:
                energy_column = daily_power.columns[0]

            for i in range(len(daily_power)):
                day_timestamp = daily_power.index[i]
                raw_energy_value = daily_power.iloc[i][energy_column]
                energy_value = float(raw_energy_value)
                if not math.isfinite(energy_value):
                    invalid_value_count += 1
                    energy_value = 0.0

                telemetry_record = {
                    "ts": self._to_daily_write_timestamp_ms(day_timestamp),
                    "values": {
                        self.DAILY_TELEMETRY_KEY: float(energy_value)
                    }
                }
                telemetry_list.append(telemetry_record)

            logger.debug(f"Prepared {len(telemetry_list)} daily telemetry records for {asset_id}")
            if invalid_value_count > 0:
                logger.warning(
                    f"Replaced {invalid_value_count} non-finite daily telemetry values with 0.0 for {asset_id}"
                )

        except Exception as e:
            logger.error(f"Error preparing daily telemetry for {asset_id}: {e}")

        return telemetry_list
    
    async def run_forecast_for_main_asset(
        self,
        job_id: str,
        main_asset_id: str,
        already_have: bool,
        start_dt=None,
        end_dt=None,
    ) -> None:
        """
        Execute forecast workflow for a main asset and all its children.
        This is the long-running background task.
        
        Args:
            job_id: Job ID for tracking
            main_asset_id: Main asset ID to start from
            already_have: Whether historical data exists
            start_dt: Optional start datetime (defaults to yesterday)
            end_dt: Optional end datetime (defaults to yesterday)
        """
        try:
            if start_dt is None or end_dt is None:
                start_dt, end_dt = self._get_yesterday_range()
            logger.info(
                f"Starting forecast job {job_id} for main asset {main_asset_id} | "
                f"already_have={already_have} | start={start_dt.isoformat()} end={end_dt.isoformat()}"
            )
            
            # Mark job as running
            await job_manager.mark_running(job_id)
            
            async with ThingsBoardClient() as tb_client:
                # Step 1: Build hierarchy for bottom-up roll-up
                logger.info(f"Retrieving hierarchy from {main_asset_id}")
                await job_manager.update_job_progress(
                    job_id,
                    progress_message="Retrieving asset hierarchy"
                )
                
                target_level = settings.DEFAULT_TARGET_LEVEL
                levels, children_by_parent = await tb_client.get_hierarchy_levels(main_asset_id, target_level)

                if not levels:
                    logger.warning(f"No hierarchy found for {main_asset_id}")
                    await job_manager.mark_completed(job_id)
                    return

                # Deepest non-empty level is the forecast source level
                deepest_assets: List[str] = []
                deepest_level_index = 0
                for level_index in range(len(levels) - 1, -1, -1):
                    level_assets = levels[level_index]
                    if level_assets:
                        deepest_assets = level_assets
                        deepest_level_index = level_index
                        break

                logger.info(
                    f"Hierarchy ready with {len(levels)} levels. "
                    f"Processing {len(deepest_assets)} assets at deepest level"
                )
                await job_manager.update_job_progress(
                    job_id,
                    total_assets=len(deepest_assets),
                    assets_processed=0,
                    successful=0,
                    failed=0,
                    skipped=0,
                    progress_message=f"Processing {len(deepest_assets)} deepest-level assets",
                    current_step="asset_traversal_complete"
                )
                
                if not deepest_assets:
                    logger.warning(f"No assets found for {main_asset_id}")
                    await job_manager.mark_completed(job_id)
                    return
                
                # Step 2: Process deepest-level assets and write their telemetry
                successful = 0
                failed = 0
                skipped = 0
                telemetry_by_asset: Dict[str, List[Dict[str, Any]]] = {}
                daily_telemetry_by_asset: Dict[str, List[Dict[str, Any]]] = {}
                
                for idx, asset_id in enumerate(deepest_assets, 1):
                    logger.info(f"Processing deepest asset {idx}/{len(deepest_assets)}: {asset_id}")
                    
                    await job_manager.update_job_progress(
                        job_id,
                        current_step=f"processing_asset_{idx}"
                    )
                    
                    success, error_msg, missing_attrs, telemetry_records, daily_telemetry_records = await self.process_single_asset(
                        asset_id,
                        tb_client,
                        start_dt,
                        end_dt,
                        already_have,
                        job_id=job_id,
                    )
                    
                    if success:
                        successful += 1
                        if telemetry_records:
                            telemetry_by_asset[asset_id] = telemetry_records
                        if daily_telemetry_records:
                            daily_telemetry_by_asset[asset_id] = daily_telemetry_records
                    elif error_msg and ("missing_required_attributes" in error_msg or "historical_data_not_available" in error_msg):
                        skipped += 1
                        await job_manager.add_job_error(
                            job_id, asset_id, error_msg, missing_attrs
                        )
                    else:
                        failed += 1
                        await job_manager.add_job_error(
                            job_id, asset_id, error_msg or "unknown_error"
                        )
                    
                    # Update job progress
                    await job_manager.update_job_progress(
                        job_id,
                        assets_processed=idx,
                        successful=successful,
                        failed=failed,
                        skipped=skipped,
                        progress_message=f"Processed {idx}/{len(deepest_assets)} (success: {successful}, failed: {failed}, skipped: {skipped})"
                    )

                deepest_level_total = sum(
                    self._telemetry_total_kwh(telemetry_by_asset[asset_id])
                    for asset_id in deepest_assets
                    if asset_id in telemetry_by_asset
                )
                logger.info(
                    f"Level {deepest_level_index + 1} total forecast: {deepest_level_total:.2f} kWh "
                    f"across {len([a for a in deepest_assets if a in telemetry_by_asset])} assets"
                )
                deepest_level_daily_total = sum(
                    self._daily_telemetry_total_kwh(daily_telemetry_by_asset[asset_id])
                    for asset_id in deepest_assets
                    if asset_id in daily_telemetry_by_asset
                )
                logger.info(
                    f"Level {deepest_level_index + 1} total daily forecast: {deepest_level_daily_total:.2f} kWh "
                    f"across {len([a for a in deepest_assets if a in daily_telemetry_by_asset])} assets"
                )

                # Step 3: Roll-up sums bottom-up (L4->L3->L2->L1)
                await job_manager.update_job_progress(
                    job_id,
                    progress_message="Rolling up telemetry from child levels to parent levels",
                    current_step="hierarchy_rollup"
                )

                if len(levels) > 1:
                    for level_index in range(len(levels) - 2, -1, -1):
                        parent_assets = levels[level_index]
                        level_rollup_total = 0.0
                        level_daily_rollup_total = 0.0
                        rolled_up_parent_count = 0

                        for parent_id in parent_assets:
                            child_ids = children_by_parent.get(parent_id, [])
                            child_records = [
                                telemetry_by_asset[child_id]
                                for child_id in child_ids
                                if child_id in telemetry_by_asset and telemetry_by_asset[child_id]
                            ]

                            if child_records:
                                parent_telemetry = self._sum_telemetry_records(child_records)
                                if parent_telemetry:
                                    parent_total_kwh = self._telemetry_total_kwh(parent_telemetry)

                                    telemetry_by_asset[parent_id] = parent_telemetry
                                    level_rollup_total += parent_total_kwh
                                    rolled_up_parent_count += 1
                                    logger.info(
                                        f"Rolled up {len(parent_telemetry)} records for parent {parent_id} "
                                        f"from {len(child_records)} children | total={parent_total_kwh:.2f} kWh "
                                        f"(interval telemetry write skipped for roll-up)"
                                    )
                            else:
                                logger.warning(
                                    f"No child telemetry available to roll up for parent {parent_id}"
                                )

                            child_daily_records = [
                                daily_telemetry_by_asset[child_id]
                                for child_id in child_ids
                                if child_id in daily_telemetry_by_asset and daily_telemetry_by_asset[child_id]
                            ]

                            if not child_daily_records:
                                logger.warning(
                                    f"No child daily telemetry available to roll up for parent {parent_id}"
                                )
                                continue

                            parent_daily_telemetry = self._sum_daily_telemetry_records(child_daily_records)
                            if not parent_daily_telemetry:
                                continue

                            parent_daily_total_kwh = self._daily_telemetry_total_kwh(parent_daily_telemetry)
                            daily_telemetry_by_asset[parent_id] = parent_daily_telemetry
                            level_daily_rollup_total += parent_daily_total_kwh
                            try:
                                await tb_client.write_bulk_telemetry(parent_id, parent_daily_telemetry)
                                logger.info(
                                    f"Rolled up and wrote {len(parent_daily_telemetry)} daily records for parent {parent_id} "
                                    f"from {len(child_daily_records)} children | total={parent_daily_total_kwh:.2f} kWh"
                                )
                            except Exception as e:
                                logger.error(f"Daily roll-up telemetry write failed for parent {parent_id}: {e}")
                                await job_manager.add_job_error(
                                    job_id,
                                    parent_id,
                                    f"daily_rollup_write_failed: {str(e)}"
                                )

                        logger.info(
                            f"Level {level_index + 1} roll-up total: {level_rollup_total:.2f} kWh "
                            f"across {rolled_up_parent_count} parent assets"
                        )
                        logger.info(
                            f"Level {level_index + 1} daily roll-up total: {level_daily_rollup_total:.2f} kWh"
                        )
                
                # Step 4: Mark job as completed
                logger.info(f"Forecast job {job_id} completed: {successful} successful, {failed} failed, {skipped} skipped")
                await job_manager.mark_completed(job_id)
                
        except Exception as e:
            error_msg = f"Forecast job {job_id} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await job_manager.mark_failed(job_id, error_msg)
    
    async def process_new_asset(self, asset_id: str, already_have: bool) -> Dict[str, Any]:
        """
        Process a single new asset (synchronous execution).
        
        Args:
            asset_id: Asset ID to process
            already_have: Whether asset already has historical data
            
        Returns:
            Result dictionary with status and message
        """
        try:
            start_dt, end_dt = self._get_yesterday_range()
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
                
                success, error_msg, missing_attrs, _, _ = await self.process_single_asset(
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
