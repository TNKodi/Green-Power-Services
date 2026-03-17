import os
import json
import importlib
import socket
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FastAPI = None
uvicorn = None
except_import_error: Optional[BaseException] = None

try:
	fastapi_module = importlib.import_module("fastapi")
	FastAPI = getattr(fastapi_module, "FastAPI", None)
except Exception as exc:  # pragma: no cover - optional dependency for API mode
	except_import_error = exc

try:
	uvicorn = importlib.import_module("uvicorn")
except Exception:
	uvicorn = None


def load_env_file(env_path: str) -> None:
	if not os.path.exists(env_path):
		return

	with open(env_path, "r", encoding="utf-8") as env_file:
		for line in env_file:
			entry = line.strip()
			if not entry or entry.startswith("#") or "=" not in entry:
				continue

			key, value = entry.split("=", 1)
			key = key.strip()
			value = value.strip().strip('"').strip("'")
			if key and key not in os.environ:
				os.environ[key] = value


def ms_to_iso(ts_ms: Optional[int]) -> str:
	if ts_ms is None:
		return "-"
	dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone()
	return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def to_float_or_none(value: Optional[object]) -> Optional[float]:
	if value is None:
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def format_point(point: Optional[Dict]) -> Dict[str, Optional[object]]:
	if not point:
		return {"ts": None, "time": None, "value": None}
	ts = point.get("ts")
	return {
		"ts": int(ts) if ts is not None else None,
		"time": ms_to_iso(int(ts)) if ts is not None else None,
		"value": point.get("value"),
	}


def format_points(points: List[Dict]) -> List[Dict[str, Optional[object]]]:
	formatted: List[Dict[str, Optional[object]]] = []
	for point in points:
		ts = point.get("ts")
		formatted.append(
			{
				"ts": int(ts) if ts is not None else None,
				"time": ms_to_iso(int(ts)) if ts is not None else None,
				"value": point.get("value"),
			}
		)
	return formatted


def calculate_energy_kwh(points: List[Dict[str, Optional[object]]]) -> Optional[float]:
	if len(points) < 2:
		return None

	ordered = sorted(points, key=lambda item: int(item.get("ts") or 0))

	deduped: List[Dict[str, Optional[object]]] = []
	for point in ordered:
		ts = point.get("ts")
		value = to_float_or_none(point.get("value"))
		if ts is None or value is None:
			continue

		if deduped and deduped[-1].get("ts") == ts:
			deduped[-1] = {"ts": int(ts), "value": value}
		else:
			deduped.append({"ts": int(ts), "value": value})

	if len(deduped) == 1:
		return 0.0

	if len(deduped) < 2:
		return None

	energy_kwh = 0.0
	for i in range(len(deduped) - 1):
		p1 = deduped[i]
		p2 = deduped[i + 1]
		t1 = int(p1["ts"])
		t2 = int(p2["ts"])
		if t2 <= t1:
			continue

		v1 = float(p1["value"])
		v2 = float(p2["value"])
		duration_hours = (t2 - t1) / 1000 / 3600
		energy_kwh += ((v1 + v2) / 2.0) * duration_hours

	return round(energy_kwh, 6)


def get_latest_numeric_value_in_range(
	client: "ThingBoardClient",
	asset_id: str,
	key: str,
	start_ts: int,
	end_ts: int,
) -> Optional[Dict[str, Optional[object]]]:
	payload = client.get_asset_telemetry_in_range(
		asset_id=asset_id,
		keys=[key],
		start_ts=start_ts,
		end_ts=end_ts,
	)
	entries = payload.get(key, []) if isinstance(payload, dict) else []
	if not entries:
		return None

	valid_entries = []
	for entry in entries:
		ts = entry.get("ts")
		value = to_float_or_none(entry.get("value"))
		if ts is None or value is None:
			continue
		valid_entries.append({"ts": int(ts), "value": value})

	if not valid_entries:
		return None

	latest = max(valid_entries, key=lambda item: int(item.get("ts") or 0))
	return {"ts": latest["ts"], "time": ms_to_iso(int(latest["ts"])), "value": latest["value"]}


def safe_get_latest_numeric_value_in_range(
	client: "ThingBoardClient",
	asset_id: str,
	key: str,
	start_ts: int,
	end_ts: int,
) -> Optional[Dict[str, Optional[object]]]:
	try:
		return get_latest_numeric_value_in_range(
			client=client,
			asset_id=asset_id,
			key=key,
			start_ts=start_ts,
			end_ts=end_ts,
		)
	except Exception as exc:
		print(f"Warning: failed to read {key} for asset {asset_id}: {exc}")
		return None


def normalize_telemetry_entries(entries: Optional[List[Dict]]) -> List[Dict]:
	if not entries:
		return []
	ordered_entries = sorted(entries, key=lambda item: int(item.get("ts", 0)))
	valid_entries: List[Dict] = []
	for entry in ordered_entries:
		ts = entry.get("ts")
		value = to_float_or_none(entry.get("value"))
		if ts is None or value is None:
			continue
		valid_entries.append({"ts": int(ts), "value": value})
	return valid_entries


def latest_before(entries: List[Dict], point_ts: int) -> Optional[Dict]:
	for entry in reversed(entries):
		if int(entry.get("ts", 0)) < point_ts:
			return entry
	return None


def first_at_or_after(entries: List[Dict], point_ts: int) -> Optional[Dict]:
	for entry in entries:
		if int(entry.get("ts", 0)) >= point_ts:
			return entry
	return None


def filter_entries_between(entries: List[Dict], start_ts: int, end_ts: int) -> List[Dict]:
	return [entry for entry in entries if start_ts <= int(entry.get("ts", 0)) <= end_ts]


def classify_other_loss(raw_difference_value: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
	if raw_difference_value is None:
		return None, None
	if raw_difference_value > 0:
		return round(raw_difference_value, 6), 0.0
	if raw_difference_value < 0:
		return 0.0, round(abs(raw_difference_value), 6)
	return 0.0, 0.0


class ThingBoardClient:
	def __init__(
		self,
		base_url: str,
		username: str,
		password: str,
		timeout: int = 30,
		max_retries: int = 2,
		retry_delay_seconds: float = 1.5,
	) -> None:
		self.base_url = base_url.rstrip("/")
		self.username = username
		self.password = password
		self.timeout = timeout
		self.max_retries = max(0, int(max_retries))
		self.retry_delay_seconds = max(0.0, float(retry_delay_seconds))
		self.token: Optional[str] = None

	def _request(
		self,
		method: str,
		path: str,
		params: Optional[Dict[str, str]] = None,
		body: Optional[Dict] = None,
	) -> Dict:
		url = f"{self.base_url}{path}"
		if params:
			url = f"{url}?{urlencode(params)}"

		headers = {"Content-Type": "application/json"}
		if self.token:
			headers["X-Authorization"] = f"Bearer {self.token}"

		data = None
		if body is not None:
			data = json.dumps(body).encode("utf-8")

		request = Request(url=url, data=data, headers=headers, method=method.upper())

		last_error: Optional[BaseException] = None
		for attempt in range(self.max_retries + 1):
			try:
				with urlopen(request, timeout=self.timeout) as response:
					response_text = response.read().decode("utf-8")
					return json.loads(response_text) if response_text else {}
			except HTTPError as exc:
				response_text = exc.read().decode("utf-8", errors="ignore")
				raise RuntimeError(f"ThingBoard API HTTP error {exc.code}: {response_text}") from exc
			except (URLError, TimeoutError, socket.timeout, ssl.SSLError) as exc:
				last_error = exc
				if attempt >= self.max_retries:
					break
				print(
					f"Warning: API request failed ({exc}); retry {attempt + 1}/{self.max_retries} after {self.retry_delay_seconds}s."
				)
				time.sleep(self.retry_delay_seconds)

		raise RuntimeError(f"ThingBoard API connection error after retries: {last_error}")

	def login(self) -> None:
		payload = self._request(
			method="POST",
			path="/api/auth/login",
			body={"username": self.username, "password": self.password},
		)
		token = payload.get("token")
		if not token:
			raise RuntimeError("Login succeeded but no JWT token was returned.")
		self.token = token

	def _get_yesterday_range_ms(self) -> Tuple[int, int]:
		now_local = datetime.now().astimezone()
		today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
		yesterday_start = today_start - timedelta(days=1)

		start_time_ms = int(yesterday_start.timestamp() * 1000)
		end_time_ms = int(today_start.timestamp() * 1000) - 1
		return start_time_ms, end_time_ms

	def _get_yesterday_one_am_ms(self) -> int:
		now_local = datetime.now().astimezone()
		today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
		yesterday_one_am = (today_start - timedelta(days=1)).replace(hour=1)
		return int(yesterday_one_am.timestamp() * 1000)

	def get_related_devices(self, asset_id: str) -> List[Dict[str, str]]:
		params = {
			"fromId": asset_id,
			"fromType": "ASSET",
			"relationTypeGroup": "COMMON",
		}
		payload = self._request(method="GET", path="/api/relations/info", params=params)

		relations = payload if isinstance(payload, list) else []
		devices: Dict[str, str] = {}
		for relation in relations:
			to_entity = relation.get("to") or {}
			if to_entity.get("entityType") != "DEVICE":
				continue

			device_id = to_entity.get("id")
			if not device_id:
				continue

			device_name = relation.get("toName") or device_id
			devices[device_id] = device_name

		return [{"id": device_id, "name": device_name} for device_id, device_name in devices.items()]

	def get_related_child_assets(self, asset_id: str) -> List[Dict[str, str]]:
		params = {
			"fromId": asset_id,
			"fromType": "ASSET",
			"relationTypeGroup": "COMMON",
		}
		payload = self._request(method="GET", path="/api/relations/info", params=params)

		relations = payload if isinstance(payload, list) else []
		assets: Dict[str, str] = {}
		for relation in relations:
			to_entity = relation.get("to") or {}
			if to_entity.get("entityType") != "ASSET":
				continue

			child_asset_id = to_entity.get("id")
			if not child_asset_id:
				continue

			child_asset_name = relation.get("toName") or child_asset_id
			assets[child_asset_id] = child_asset_name

		return [{"id": child_asset_id, "name": child_asset_name} for child_asset_id, child_asset_name in assets.items()]

	def get_asset_and_descendant_assets(self, main_asset_id: str, max_depth: int = 3) -> List[Dict[str, object]]:
		assets_to_process: List[Dict[str, object]] = [
			{"id": main_asset_id, "name": main_asset_id, "depth": 0, "parent_id": None}
		]
		visited = {main_asset_id}
		queue: List[Dict[str, object]] = [{"id": main_asset_id, "depth": 0, "parent_id": None}]

		while queue:
			current = queue.pop(0)
			current_id = str(current["id"])
			current_depth = int(current["depth"])
			if current_depth >= max_depth:
				continue

			children = self.get_related_child_assets(current_id)
			for child in children:
				child_id = child["id"]
				if child_id in visited:
					continue
				visited.add(child_id)
				next_depth = current_depth + 1
				assets_to_process.append(
					{"id": child_id, "name": child.get("name", child_id), "depth": next_depth, "parent_id": current_id}
				)
				queue.append({"id": child_id, "depth": next_depth, "parent_id": current_id})

		return assets_to_process

	def get_yesterday_alarms_for_asset_devices(self, asset_id: str) -> List[Dict]:
		start_time_ms, end_time_ms = self._get_yesterday_range_ms()
		devices = self.get_related_devices(asset_id)
		alarm_page_size = int(os.getenv("THINGBOARD_ALARM_PAGE_SIZE", "1000"))

		all_alarms: List[Dict] = []
		for device in devices:
			page = 1
			page_size = max(1, alarm_page_size)
			max_pages_per_device = 1000
			device_alarm_count = 0

			print(
				f"Fetching yesterday alarms for device {device['name']} ({device['id']}) - page 0, pageSize {page_size}."
			)

			# Try to fetch all alarms in one API call first.
			params = {
				"page": "0",
				"pageSize": str(page_size),
				"startTime": str(start_time_ms),
				"endTime": str(end_time_ms),
				"searchStatus": "ANY",
				"fetchOriginator": "true",
			}
			payload = self._request(method="GET", path=f"/api/alarm/DEVICE/{device['id']}", params=params)
			page_data = payload.get("data", [])
			for alarm in page_data:
				alarm["relatedDeviceId"] = device["id"]
				alarm["relatedDeviceName"] = device["name"]
				all_alarms.append(alarm)
				device_alarm_count += 1

			if not payload.get("hasNext", False):
				print(
					f"Completed device {device['name']} ({device['id']}): fetched {device_alarm_count} alarms in 1 API call."
				)
				continue
			print(
				f"Info: alarms exceed pageSize ({page_size}) for device {device['name']} ({device['id']}); fetching remaining pages."
			)

			while True:
				if page >= max_pages_per_device:
					print(f"Warning: reached page limit for device {device['name']} ({device['id']}).")
					break

				params = {
					"page": str(page),
					"pageSize": str(page_size),
					"startTime": str(start_time_ms),
					"endTime": str(end_time_ms),
					"searchStatus": "ANY",
					"fetchOriginator": "true",
				}
				print(
					f"Fetching yesterday alarms for device {device['name']} ({device['id']}) - page {page}, pageSize {page_size}."
				)
				payload = self._request(method="GET", path=f"/api/alarm/DEVICE/{device['id']}", params=params)
				page_data = payload.get("data", [])
				if not page_data:
					break

				for alarm in page_data:
					alarm["relatedDeviceId"] = device["id"]
					alarm["relatedDeviceName"] = device["name"]
					all_alarms.append(alarm)
					device_alarm_count += 1

				if not payload.get("hasNext", False):
					print(
						f"Completed device {device['name']} ({device['id']}): fetched {device_alarm_count} alarms in {page + 1} API calls."
					)
					break
				page += 1

		return all_alarms

	def get_asset_telemetry_in_range(self, asset_id: str, keys: List[str], start_ts: int, end_ts: int) -> Dict:
		if start_ts > end_ts:
			return {}

		params = {
			"keys": ",".join(keys),
			"startTs": str(start_ts),
			"endTs": str(end_ts),
			"limit": "100000",
			"agg": "NONE",
			"useStrictDataTypes": "true",
		}
		return self._request(
			method="GET",
			path=f"/api/plugins/telemetry/ASSET/{asset_id}/values/timeseries",
			params=params,
		)

	def get_asset_latest_value_before(self, asset_id: str, key: str, point_ts: int) -> Optional[Dict]:
		params = {
			"keys": key,
			"startTs": "0",
			"endTs": str(max(point_ts, 0)),
			"limit": "1",
			"agg": "NONE",
			"useStrictDataTypes": "true",
		}
		payload = self._request(
			method="GET",
			path=f"/api/plugins/telemetry/ASSET/{asset_id}/values/timeseries",
			params=params,
		)
		entries = payload.get(key, []) if isinstance(payload, dict) else []
		if not entries:
			return None
		return entries[0]

	def get_asset_first_value_at_or_after(
		self,
		asset_id: str,
		key: str,
		point_ts: int,
		look_ahead_ms: int = 7 * 24 * 60 * 60 * 1000,
	) -> Optional[Dict]:
		end_ts = point_ts + look_ahead_ms
		payload = self.get_asset_telemetry_in_range(
			asset_id=asset_id,
			keys=[key],
			start_ts=point_ts,
			end_ts=end_ts,
		)
		entries = payload.get(key, []) if isinstance(payload, dict) else []
		if not entries:
			return None

		ordered_entries = sorted(entries, key=lambda item: int(item.get("ts", 0)))
		for item in ordered_entries:
			item_ts = item.get("ts")
			if item_ts is not None and int(item_ts) >= point_ts:
				return item
		return None

	def get_asset_middle_values_between(self, asset_id: str, key: str, start_ts: int, end_ts: int) -> List[Dict]:
		if start_ts >= end_ts:
			return []

		payload = self.get_asset_telemetry_in_range(
			asset_id=asset_id,
			keys=[key],
			start_ts=start_ts,
			end_ts=end_ts,
		)
		entries = payload.get(key, []) if isinstance(payload, dict) else []

		middle_entries: List[Dict] = []
		for entry in entries:
			ts = entry.get("ts")
			if ts is None:
				continue
			ts_int = int(ts)
			if start_ts < ts_int < end_ts:
				middle_entries.append(entry)

		return sorted(middle_entries, key=lambda item: int(item.get("ts", 0)))

	def save_asset_telemetry(self, asset_id: str, ts_ms: int, values: Dict[str, float]) -> None:
		payload = {"ts": int(ts_ms), "values": values}
		self._request(
			method="POST",
			path=f"/api/plugins/telemetry/ASSET/{asset_id}/timeseries/ANY",
			body=payload,
		)

	def save_asset_summary_telemetry(self, asset_id: str, values: Dict[str, float], ts_ms: Optional[int] = None) -> int:
		if not values:
			return 0

		timestamp_ms = self._get_yesterday_one_am_ms() if ts_ms is None else int(ts_ms)
		self.save_asset_telemetry(asset_id=asset_id, ts_ms=timestamp_ms, values=values)
		return 1


def enrich_alarms_with_asset_data(
	client: ThingBoardClient,
	alarms: List[Dict],
	asset_id: str,
	keys: List[str],
	telemetry_cache: Optional[Dict] = None,
) -> None:
	telemetry_by_key: Dict[str, List[Dict]] = {}
	if isinstance(telemetry_cache, dict):
		for key in keys:
			telemetry_by_key[key] = normalize_telemetry_entries(telemetry_cache.get(key, []))

	for alarm in alarms:
		alarm["assetTelemetrySource"] = f"ASSET/{asset_id}"
		alarm["assetBoundaryMetrics"] = {}
		active_ts = alarm.get("startTs")
		cleared_ts = alarm.get("clearTs")

		if active_ts is None or cleared_ts is None:
			alarm["assetTelemetry"] = {}
			alarm["assetTelemetryNote"] = "Skipped telemetry fetch (missing active or cleared time)."
			continue

		asset_telemetry: Dict[str, List[Dict]] = {}
		if telemetry_by_key:
			for key in keys:
				asset_telemetry[key] = filter_entries_between(telemetry_by_key.get(key, []), int(active_ts), int(cleared_ts))
		else:
			telemetry = client.get_asset_telemetry_in_range(
				asset_id=asset_id,
				keys=keys,
				start_ts=int(active_ts),
				end_ts=int(cleared_ts),
			)
			asset_telemetry = telemetry if isinstance(telemetry, dict) else {}
		alarm["assetTelemetry"] = asset_telemetry

		boundary_metrics: Dict[str, Dict[str, Dict[str, Optional[Dict]]]] = {}
		for key in keys:
			key_metrics: Dict[str, Dict[str, Optional[Dict]]] = {}
			entries_for_key = telemetry_by_key.get(key, []) if telemetry_by_key else []

			for label, point_ts in (("active", int(active_ts)), ("clear", int(cleared_ts))):
				if entries_for_key:
					before = latest_before(entries_for_key, point_ts)
					after = first_at_or_after(entries_for_key, point_ts)
				else:
					before = client.get_asset_latest_value_before(asset_id=asset_id, key=key, point_ts=point_ts - 1)
					after = client.get_asset_first_value_at_or_after(asset_id=asset_id, key=key, point_ts=point_ts)

				lowest = None
				interval_start = point_ts
				interval_end = point_ts
				if before and before.get("ts") is not None:
					interval_start = int(before.get("ts"))
				if after and after.get("ts") is not None:
					interval_end = int(after.get("ts"))

				if interval_start > interval_end:
					interval_start, interval_end = interval_end, interval_start

				if entries_for_key:
					interval_entries = filter_entries_between(entries_for_key, interval_start, interval_end)
				else:
					interval_payload = client.get_asset_telemetry_in_range(
						asset_id=asset_id,
						keys=[key],
						start_ts=interval_start,
						end_ts=interval_end,
					)
					interval_entries = interval_payload.get(key, []) if isinstance(interval_payload, dict) else []

				candidate_entries = list(interval_entries)
				if before:
					candidate_entries.append(before)
				if after:
					candidate_entries.append(after)

				valid_entries = [entry for entry in candidate_entries if to_float_or_none(entry.get("value")) is not None]
				if valid_entries:
					lowest = min(valid_entries, key=lambda entry: to_float_or_none(entry.get("value")) or float("inf"))

				key_metrics[label] = {
					"before": before,
					"at_or_after": after,
					"lowest": lowest,
				}

			boundary_metrics[key] = key_metrics

		alarm["assetBoundaryMetrics"] = boundary_metrics
		alarm["assetTelemetryNote"] = ""


def build_latest_lowest_records(alarms: List[Dict], keys: List[str]) -> List[Dict]:
	records: List[Dict] = []
	for alarm in alarms:
		alarm_id = alarm.get("id", {}).get("id", "unknown")
		name = alarm.get("name") or alarm.get("type") or "Unnamed alarm"
		device_name = alarm.get("relatedDeviceName", "unknown")
		device_id = alarm.get("relatedDeviceId", "unknown")
		originator_name = alarm.get("originatorName", "unknown")
		active_ts = alarm.get("startTs")
		cleared_ts = alarm.get("clearTs")
		asset_source = alarm.get("assetTelemetrySource", "ASSET/unknown")

		key_results: Dict[str, Dict[str, Dict[str, Optional[object]]]] = {}
		metrics_by_key = alarm.get("assetBoundaryMetrics", {})
		for key in keys:
			key_metric = metrics_by_key.get(key, {}) if isinstance(metrics_by_key, dict) else {}
			active_metric = key_metric.get("active", {}) if isinstance(key_metric, dict) else {}
			clear_metric = key_metric.get("clear", {}) if isinstance(key_metric, dict) else {}

			key_results[key] = {
				"active_lowest": format_point(active_metric.get("lowest") if isinstance(active_metric, dict) else None),
				"clear_lowest": format_point(clear_metric.get("lowest") if isinstance(clear_metric, dict) else None),
			}

		records.append(
			{
				"alarm_id": alarm_id,
				"alarm_name": name,
				"device_name": device_name,
				"device_id": device_id,
				"originator": originator_name,
				"active_time": ms_to_iso(active_ts),
				"cleared_time": ms_to_iso(cleared_ts),
				"asset_source": asset_source,
				"keys": key_results,
			}
		)

	return records


def enrich_records_with_middle_points(
	client: ThingBoardClient,
	records: List[Dict],
	asset_id: str,
	keys: List[str],
	telemetry_cache: Optional[Dict] = None,
) -> None:
	telemetry_by_key: Dict[str, List[Dict]] = {}
	if isinstance(telemetry_cache, dict):
		for key in keys:
			telemetry_by_key[key] = normalize_telemetry_entries(telemetry_cache.get(key, []))

	for record in records:
		keys_data = record.get("keys", {})
		for key in keys:
			key_data = keys_data.get(key, {}) if isinstance(keys_data, dict) else {}
			active_lowest = key_data.get("active_lowest", {}) if isinstance(key_data, dict) else {}
			clear_lowest = key_data.get("clear_lowest", {}) if isinstance(key_data, dict) else {}

			active_lowest_ts = active_lowest.get("ts") if isinstance(active_lowest, dict) else None
			clear_lowest_ts = clear_lowest.get("ts") if isinstance(clear_lowest, dict) else None

			if active_lowest_ts is None or clear_lowest_ts is None:
				key_data["middle_points"] = []
				key_data["energy_kwh"] = None
				continue

			start_ts = min(int(active_lowest_ts), int(clear_lowest_ts))
			end_ts = max(int(active_lowest_ts), int(clear_lowest_ts))

			if telemetry_by_key.get(key):
				middle_points = [
					entry
					for entry in telemetry_by_key[key]
					if start_ts < int(entry.get("ts", 0)) < end_ts
				]
			else:
				middle_points = client.get_asset_middle_values_between(
					asset_id=asset_id,
					key=key,
					start_ts=start_ts,
					end_ts=end_ts,
				)
			formatted_middle_points = format_points(middle_points)
			key_data["middle_points"] = formatted_middle_points

			series_points: List[Dict[str, Optional[object]]] = []
			series_points.append({"ts": active_lowest.get("ts"), "value": active_lowest.get("value")})
			series_points.extend(formatted_middle_points)
			series_points.append({"ts": clear_lowest.get("ts"), "value": clear_lowest.get("value")})

			key_data["energy_kwh"] = calculate_energy_kwh(series_points)


def print_alarm_report(
	alarms: List[Dict],
	client: ThingBoardClient,
	asset_id: str,
	asset_name: Optional[str] = None,
	asset_depth: int = 0,
	telemetry_cache: Optional[Dict] = None,
) -> Dict[str, float]:
	asset_label = asset_name or asset_id
	related_devices = client.get_related_devices(asset_id)
	device_names = [str(device.get("name") or device.get("id") or "unknown") for device in related_devices]
	device_names_text = ", ".join(device_names) if device_names else "no related devices"

	print(f"\nAsset: {asset_label} ({asset_id})")
	print(f"Asset depth from main: {asset_depth}")
	print(f"Related devices: {device_names_text}")

	start_ts, end_ts = client._get_yesterday_range_ms()
	latest_solcast_daily_value = None
	latest_daily_gen_max_value = None
	if isinstance(telemetry_cache, dict):
		solcast_entries = normalize_telemetry_entries(telemetry_cache.get("solcast_daily", []))
		daily_entries = normalize_telemetry_entries(telemetry_cache.get("daily_gen_max", []))
		if solcast_entries:
			latest_solcast_daily_value = solcast_entries[-1].get("value")
		if daily_entries:
			latest_daily_gen_max_value = daily_entries[-1].get("value")
	if latest_solcast_daily_value is None:
		solcast_daily_point = safe_get_latest_numeric_value_in_range(
			client=client,
			asset_id=asset_id,
			key="solcast_daily",
			start_ts=start_ts,
			end_ts=end_ts,
		)
		latest_solcast_daily_value = solcast_daily_point.get("value") if solcast_daily_point else None
	if latest_daily_gen_max_value is None:
		daily_gen_max_point = safe_get_latest_numeric_value_in_range(
			client=client,
			asset_id=asset_id,
			key="daily_gen_max",
			start_ts=start_ts,
			end_ts=end_ts,
		)
		latest_daily_gen_max_value = daily_gen_max_point.get("value") if daily_gen_max_point else None

	if not alarms:
		grid_cluster_value = 0.0
		inverter_cluster_value = 0.0

		print("No alarms found for yesterday (local timezone).")
		print("Fallback loss calculation:")
		print(
			f"  solcast_daily (latest yesterday) : {latest_solcast_daily_value if latest_solcast_daily_value is not None else 'no data'}"
		)
		print(
			f"  daily_gen_max (latest yesterday): {latest_daily_gen_max_value if latest_daily_gen_max_value is not None else 'no data'}"
		)

		if latest_solcast_daily_value is None or latest_daily_gen_max_value is None:
			raw_difference_value: Optional[float] = None
		else:
			raw_difference_value = round(
				float(latest_solcast_daily_value)
				- float(grid_cluster_value + inverter_cluster_value + float(latest_daily_gen_max_value)),
				6,
			)

		other_loss_value, grid_over_performance_value = classify_other_loss(raw_difference_value)
		print(
			f"  solcast_daily - (grid + inverter + daily_gen_max): {raw_difference_value if raw_difference_value is not None else 'no data'}"
		)

		print("Final report:")
		print(f"  grid loss                              : {grid_cluster_value}")
		print(f"  inverter loss                          : {inverter_cluster_value}")
		print(
			f"  grid_over_performance_kwh              : {grid_over_performance_value if grid_over_performance_value is not None else 'no data'}"
		)
		print(f"  other_loss_kwh                         : {other_loss_value if other_loss_value is not None else 'no data'}")

		telemetry_values: Dict[str, float] = {
			"grid_loss": float(grid_cluster_value),
			"inverter_loss": float(inverter_cluster_value),
			"grid_over_performance_kwh": float(grid_over_performance_value or 0.0),
			"other_loss_kwh": float(other_loss_value or 0.0),
		}

		try:
			written_count = client.save_asset_summary_telemetry(asset_id=asset_id, values=telemetry_values)
			print(f"  telemetry_write_time                  : {ms_to_iso(client._get_yesterday_one_am_ms())}")
			print(f"  telemetry_written_assets              : {written_count}")
		except Exception as exc:
			print(f"  telemetry_write_error                 : {exc}")
		print(f"  telemetry_related_device_names        : {device_names_text}")
		return telemetry_values

	report_keys = ["active_power", "active_power_solcast", "solcast_daily", "daily_gen_max"]
	records = build_latest_lowest_records(alarms=alarms, keys=report_keys)
	enrich_records_with_middle_points(
		client=client,
		records=records,
		asset_id=asset_id,
		keys=["active_power", "active_power_solcast"],
		telemetry_cache=telemetry_cache,
	)
	grid_cluster_alarm_names = {
		"al_st_utility_loss",
		"al_st_vac_fail_grid_voltage_overrun",
		"al_st_grid_frequency_overrun",
	}
	cluster_totals = {"grid": 0.0, "inverter": 0.0}

	print(f"Alarm energy differences for {len(records)} alarm(s):\n")
	for record in records:
		alarm_name = str(record.get("alarm_name") or "")
		normalized_alarm_name = alarm_name.strip().lower()
		cluster_name = (
			"grid"
			if normalized_alarm_name.startswith("grid") or normalized_alarm_name in grid_cluster_alarm_names
			else "inverter"
		)

		print(f"Alarm: {record.get('alarm_name')} ({record.get('alarm_id')})")
		print(f"  Cluster     : {cluster_name}")
		print(f"  Device      : {record.get('device_name')} ({record.get('device_id')})")
		print(f"  Active Time : {record.get('active_time')}")
		print(f"  Cleared Time: {record.get('cleared_time')}")

		keys_data = record.get("keys", {})
		active_energy = None
		solcast_energy = None

		active_power_data = keys_data.get("active_power", {}) if isinstance(keys_data, dict) else {}
		if isinstance(active_power_data, dict):
			active_energy = active_power_data.get("energy_kwh")

		solcast_power_data = keys_data.get("active_power_solcast", {}) if isinstance(keys_data, dict) else {}
		if isinstance(solcast_power_data, dict):
			solcast_energy = solcast_power_data.get("energy_kwh")

		print(
			f"  active_power energy_kwh         : {active_energy if active_energy is not None else 'no data'}"
		)
		print(
			f"  active_power_solcast energy_kwh : {solcast_energy if solcast_energy is not None else 'no data'}"
		)

		solcast_daily_value = None
		daily_gen_max_value = None

		solcast_daily_data = keys_data.get("solcast_daily", {}) if isinstance(keys_data, dict) else {}
		if isinstance(solcast_daily_data, dict):
			solcast_daily_active = solcast_daily_data.get("active_lowest", {})
			if isinstance(solcast_daily_active, dict):
				solcast_daily_value = solcast_daily_active.get("value")

		daily_gen_max_data = keys_data.get("daily_gen_max", {}) if isinstance(keys_data, dict) else {}
		if isinstance(daily_gen_max_data, dict):
			daily_gen_max_active = daily_gen_max_data.get("active_lowest", {})
			if isinstance(daily_gen_max_active, dict):
				daily_gen_max_value = daily_gen_max_active.get("value")

		print(
			f"  solcast_daily (asset)           : {solcast_daily_value if solcast_daily_value is not None else 'no data'}"
		)
		print(
			f"  daily_gen_max (asset)           : {daily_gen_max_value if daily_gen_max_value is not None else 'no data'}"
		)

		if active_energy is None or solcast_energy is None:
			print("  energy_difference_kwh           : no data")
		else:
			difference = round(max(float(solcast_energy) - float(active_energy), 0.0), 6)
			cluster_totals[cluster_name] += difference
			print(f"  energy_difference_kwh           : {difference}")

		print("-" * 60)

	grid_total = round(cluster_totals["grid"], 6)
	inverter_total = round(cluster_totals["inverter"], 6)

	if latest_solcast_daily_value is None or latest_daily_gen_max_value is None:
		raw_difference_value = None
	else:
		raw_difference_value = round(
			float(latest_solcast_daily_value) - float(grid_total + inverter_total + float(latest_daily_gen_max_value)),
			6,
		)

	other_loss_value, grid_over_performance_value = classify_other_loss(raw_difference_value)

	print("Cluster summary:")
	print(f"  grid loss                              : {grid_total}")
	print(f"  inverter loss                          : {inverter_total}")
	print(
		f"  solcast_daily (latest yesterday)       : {latest_solcast_daily_value if latest_solcast_daily_value is not None else 'no data'}"
	)
	print(
		f"  daily_gen_max (latest yesterday)       : {latest_daily_gen_max_value if latest_daily_gen_max_value is not None else 'no data'}"
	)
	print(
		f"  solcast_daily - (grid + inverter + daily_gen_max): {raw_difference_value if raw_difference_value is not None else 'no data'}"
	)
	print(
		f"  grid_over_performance_kwh              : {grid_over_performance_value if grid_over_performance_value is not None else 'no data'}"
	)
	print(f"  other_loss_kwh                         : {other_loss_value if other_loss_value is not None else 'no data'}")

	telemetry_values: Dict[str, float] = {
		"grid_loss": float(grid_total),
		"inverter_loss": float(inverter_total),
		"grid_over_performance_kwh": float(grid_over_performance_value or 0.0),
		"other_loss_kwh": float(other_loss_value or 0.0),
	}

	try:
		written_count = client.save_asset_summary_telemetry(asset_id=asset_id, values=telemetry_values)
		print(f"  telemetry_write_time                  : {ms_to_iso(client._get_yesterday_one_am_ms())}")
		print(f"  telemetry_written_assets              : {written_count}")
	except Exception as exc:
		print(f"  telemetry_write_error                 : {exc}")
	print(f"  telemetry_related_device_names        : {device_names_text}")
	return telemetry_values


def run_loss_breakdown(
	env_overrides: Optional[Dict[str, str]] = None,
	max_depth: int = 3,
	process_depth: int = 3,
) -> Dict[str, Any]:
	load_env_file(os.path.join(os.path.dirname(__file__), ".env"))

	if env_overrides:
		for key, value in env_overrides.items():
			if value is not None:
				os.environ[key] = str(value)

	base_url = os.getenv("THINGBOARD_URL")
	username = os.getenv("THINGBOARD_USERNAME")
	password = os.getenv("THINGBOARD_PASSWORD")
	asset_id = os.getenv("THINGBOARD_ASSET_ID")
	timeout_seconds = int(os.getenv("THINGBOARD_TIMEOUT", "20"))
	max_retries = int(os.getenv("THINGBOARD_RETRIES", "2"))
	retry_delay_seconds = float(os.getenv("THINGBOARD_RETRY_DELAY_SECONDS", "1.5"))

	if not base_url or not username or not password or not asset_id:
		raise RuntimeError(
			"Please set THINGBOARD_URL, THINGBOARD_USERNAME, THINGBOARD_PASSWORD, and THINGBOARD_ASSET_ID in environment variables or .env."
		)

	client = ThingBoardClient(
		base_url=base_url,
		username=username,
		password=password,
		timeout=timeout_seconds,
		max_retries=max_retries,
		retry_delay_seconds=retry_delay_seconds,
	)
	client.login()
	assets_to_process = client.get_asset_and_descendant_assets(main_asset_id=asset_id, max_depth=max_depth)
	asset_lookup: Dict[str, Dict[str, object]] = {
		str(item.get("id")): item for item in assets_to_process if item.get("id") is not None
	}
	print(f"Processing {len(assets_to_process)} asset(s): main + up to {max_depth} child levels.")
	level3_count = 0
	level3_loss_by_asset: Dict[str, Dict[str, float]] = {}
	skipped_assets: List[str] = []
	asset_errors: List[Dict[str, str]] = []

	for asset_info in assets_to_process:
		current_asset_id = str(asset_info.get("id"))
		current_asset_name = str(asset_info.get("name") or current_asset_id)
		current_asset_depth = int(asset_info.get("depth") or 0)

		if current_asset_depth != process_depth:
			print(f"\nAsset: {current_asset_name} ({current_asset_id})")
			print(f"Asset depth from main: {current_asset_depth}")
			print(f"Skipped: device checks and telemetry writes are only enabled for level {process_depth} assets.")
			skipped_assets.append(current_asset_id)
			continue

		level3_count += 1
		print(f"\nProcessing level-{process_depth} asset: {current_asset_name} ({current_asset_id})")
		try:
			start_ts, end_ts = client._get_yesterday_range_ms()
			telemetry_cache = client.get_asset_telemetry_in_range(
				asset_id=current_asset_id,
				keys=["active_power", "active_power_solcast", "solcast_daily", "daily_gen_max"],
				start_ts=start_ts,
				end_ts=end_ts,
			)
			if not isinstance(telemetry_cache, dict):
				telemetry_cache = {}

			alarms = client.get_yesterday_alarms_for_asset_devices(current_asset_id)
			enrich_alarms_with_asset_data(
				client=client,
				alarms=alarms,
				asset_id=current_asset_id,
				keys=["active_power", "active_power_solcast", "solcast_daily", "daily_gen_max"],
				telemetry_cache=telemetry_cache,
			)
			loss_values = print_alarm_report(
				alarms,
				client=client,
				asset_id=current_asset_id,
				asset_name=current_asset_name,
				asset_depth=current_asset_depth,
				telemetry_cache=telemetry_cache,
			)
			level3_loss_by_asset[current_asset_id] = loss_values
		except Exception as exc:
			print(f"Error processing level-3 asset {current_asset_name} ({current_asset_id}): {exc}")
			asset_errors.append(
				{
					"asset_id": current_asset_id,
					"asset_name": current_asset_name,
					"error": str(exc),
				}
			)
			continue

	if level3_count == 0:
		print(f"No level {process_depth} child assets found. Nothing processed for device checks or telemetry writes.")
		return {
			"status": "ok",
			"processed_at": datetime.now().astimezone().isoformat(),
			"main_asset_id": asset_id,
			"assets_discovered": len(assets_to_process),
			"process_depth": process_depth,
			"processed_assets": 0,
			"skipped_assets": skipped_assets,
			"errors": asset_errors,
			"level_asset_losses": {},
			"rollup_by_parent": {},
			"main_rollup": {
				"grid_loss": 0.0,
				"inverter_loss": 0.0,
				"grid_over_performance_kwh": 0.0,
				"other_loss_kwh": 0.0,
			},
		}

	rollup_by_parent: Dict[str, Dict[str, float]] = {}
	total_from_level3: Dict[str, float] = {
		"grid_loss": 0.0,
		"inverter_loss": 0.0,
		"grid_over_performance_kwh": 0.0,
		"other_loss_kwh": 0.0,
	}
	for leaf_asset_id, leaf_values in level3_loss_by_asset.items():
		for key in ("grid_loss", "inverter_loss", "grid_over_performance_kwh", "other_loss_kwh"):
			total_from_level3[key] += float(leaf_values.get(key, 0.0))

		parent_id = asset_lookup.get(leaf_asset_id, {}).get("parent_id")
		while parent_id:
			parent_id_str = str(parent_id)
			if parent_id_str not in rollup_by_parent:
				rollup_by_parent[parent_id_str] = {
					"grid_loss": 0.0,
					"inverter_loss": 0.0,
					"grid_over_performance_kwh": 0.0,
					"other_loss_kwh": 0.0,
				}
			for key in ("grid_loss", "inverter_loss", "grid_over_performance_kwh", "other_loss_kwh"):
				rollup_by_parent[parent_id_str][key] += float(leaf_values.get(key, 0.0))
			parent_id = asset_lookup.get(parent_id_str, {}).get("parent_id")

	print("\nParent level roll-up writeback (levels 2, 1, and 0):")
	for parent_asset_id, parent_values in rollup_by_parent.items():
		parent_name = str(asset_lookup.get(parent_asset_id, {}).get("name") or parent_asset_id)
		parent_depth = int(asset_lookup.get(parent_asset_id, {}).get("depth") or -1)
		rounded_values = {k: round(v, 6) for k, v in parent_values.items()}
		try:
			client.save_asset_summary_telemetry(asset_id=parent_asset_id, values=rounded_values)
			print(
				f"  Parent asset {parent_name} ({parent_asset_id}) depth {parent_depth} <- {rounded_values}"
			)
		except Exception as exc:
			print(
				f"  Parent roll-up write error for {parent_name} ({parent_asset_id}) depth {parent_depth}: {exc}"
			)

	# Always write and print level-0 main asset explicitly for visibility.
	main_asset_name = str(asset_lookup.get(asset_id, {}).get("name") or asset_id)
	main_rounded_values = {k: round(v, 6) for k, v in total_from_level3.items()}
	try:
		client.save_asset_summary_telemetry(asset_id=asset_id, values=main_rounded_values)
		print(f"  Main asset {main_asset_name} ({asset_id}) depth 0 <- {main_rounded_values}")
	except Exception as exc:
		print(f"  Main asset roll-up write error for {main_asset_name} ({asset_id}) depth 0: {exc}")

	rollup_summary: Dict[str, Dict[str, float]] = {
		parent_asset_id: {k: round(v, 6) for k, v in values.items()} for parent_asset_id, values in rollup_by_parent.items()
	}

	return {
		"status": "ok",
		"processed_at": datetime.now().astimezone().isoformat(),
		"main_asset_id": asset_id,
		"assets_discovered": len(assets_to_process),
		"process_depth": process_depth,
		"processed_assets": level3_count,
		"skipped_assets": skipped_assets,
		"errors": asset_errors,
		"level_asset_losses": level3_loss_by_asset,
		"rollup_by_parent": rollup_summary,
		"main_rollup": main_rounded_values,
	}


def main() -> None:
	result = run_loss_breakdown()
	print("\nExecution summary:")
	print(json.dumps(result, indent=2))


def create_api_app() -> Any:
	if FastAPI is None:
		raise RuntimeError(
			f"FastAPI is not available. Install dependencies first. Import error: {except_import_error}"
		)

	app = FastAPI(title="Loss Breakdown API", version="1.0.0")

	@app.get("/health")
	def health() -> Dict[str, str]:
		return {"status": "ok"}

	@app.post("/run")
	def run_breakdown(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		request_payload = payload or {}
		env_overrides_raw = request_payload.get("env_overrides", {})
		env_overrides: Dict[str, str] = {}
		if isinstance(env_overrides_raw, dict):
			env_overrides = {str(k): str(v) for k, v in env_overrides_raw.items() if v is not None}

		max_depth = int(request_payload.get("max_depth", 3))
		process_depth = int(request_payload.get("process_depth", 3))

		return run_loss_breakdown(
			env_overrides=env_overrides,
			max_depth=max_depth,
			process_depth=process_depth,
		)

	return app


app = create_api_app() if FastAPI is not None else None


if __name__ == "__main__":
	if "--api" in sys.argv:
		if uvicorn is None:
			raise RuntimeError("uvicorn is not available. Install dependencies first: pip install fastapi uvicorn")
		host = os.getenv("API_HOST", "0.0.0.0")
		port = int(os.getenv("API_PORT", "8000"))
		uvicorn.run(app, host=host, port=port)
	else:
		main()
