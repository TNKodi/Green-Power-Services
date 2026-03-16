"""
ThingsBoard REST API client.
Handles authentication, asset retrieval, attribute reading, and telemetry writing.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import httpx

from app.utils.config import settings
from app.utils.logger import logger


class ThingsBoardClient:
    """
    Async client for ThingsBoard REST API operations.
    Handles JWT authentication with automatic token refresh.
    """
    
    def __init__(self):
        self.base_url = settings.TB_HOST
        self.username = settings.TB_USERNAME
        self.password = settings.TB_PASSWORD
        self._token: Optional[str] = None
        self._token_timestamp: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    async def _ensure_token(self) -> str:
        """
        Ensure we have a valid JWT token.
        Refreshes token if expired or missing.
        
        Returns:
            Valid JWT token
        """
        now = datetime.now()
        
        # Check if token needs refresh
        if (self._token is None or 
            self._token_timestamp is None or 
            (now - self._token_timestamp).total_seconds() > settings.TB_TOKEN_EXPIRY - 300):
            
            logger.info("Authenticating with ThingsBoard...")
            await self._login()
        
        return self._token
    
    async def _login(self) -> None:
        """
        Authenticate with ThingsBoard and obtain JWT token.
        
        Raises:
            httpx.HTTPError: If authentication fails
        """
        url = f"{self.base_url}/api/auth/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            self._token = data["token"]
            self._token_timestamp = datetime.now()
            
            logger.info("Successfully authenticated with ThingsBoard")
            
        except httpx.HTTPError as e:
            logger.error(f"ThingsBoard authentication failed: {e}")
            raise
    
    async def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers with valid JWT token.
        
        Returns:
            Headers dictionary with authorization
        """
        token = await self._ensure_token()
        return {"X-Authorization": f"Bearer {token}"}
    
    async def get_asset_relations(self, asset_id: str) -> List[str]:
        """
        Get all child assets related to a parent asset.
        
        Args:
            asset_id: Parent asset ID
            
        Returns:
            List of child asset IDs
        """
        url = f"{self.base_url}/api/relations/info"
        params = {
            "fromId": asset_id,
            "fromType": "ASSET"
        }
        headers = await self._get_headers()
        
        try:
            response = await self._client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            relations = response.json()
            children = []
            
            for rel in relations:
                if rel.get("to", {}).get("entityType") == "ASSET" and rel.get("type") == "Contains":
                    child_id = rel["to"]["id"]
                    children.append(child_id)
            
            logger.debug(f"Found {len(children)} child assets for {asset_id}")
            return children
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get asset relations for {asset_id}: {e}")
            raise
    
    async def get_assets_by_level(self, root_asset_id: str, target_level: int) -> List[str]:
        """
        Recursively traverse asset hierarchy to get assets at a specific level.
        
        Args:
            root_asset_id: Root asset ID to start from
            target_level: Target level depth (1-based)
            
        Returns:
            List of asset IDs at the target level
        """
        logger.info(f"Traversing asset hierarchy from {root_asset_id} to level {target_level}")
        
        current_assets = [root_asset_id]
        
        for level in range(1, target_level + 1):
            next_assets = []
            
            # Process each asset in current level
            for asset_id in current_assets:
                children = await self.get_asset_relations(asset_id)
                next_assets.extend(children)
            
            current_assets = next_assets
            logger.info(f"Level {level}: Found {len(current_assets)} assets")
            
            if not current_assets:
                logger.warning(f"No assets found at level {level}. Stopping traversal.")
                break
        
        return current_assets

    async def get_hierarchy_levels(
        self,
        root_asset_id: str,
        max_depth: int
    ) -> Tuple[List[List[str]], Dict[str, List[str]]]:
        """
        Traverse hierarchy and return assets by level with parent->children mapping.

        Args:
            root_asset_id: Root/main asset ID (level 1)
            max_depth: Maximum depth to traverse from root level

        Returns:
            Tuple of:
              - levels: List where index 0 is root level assets, index n is level n+1
              - children_by_parent: Mapping parent asset ID -> direct child asset IDs
        """
        logger.info(
            f"Building hierarchy from root {root_asset_id} up to depth {max_depth}"
        )

        levels: List[List[str]] = [[root_asset_id]]
        children_by_parent: Dict[str, List[str]] = {}

        for depth in range(1, max_depth):
            current_level_assets = levels[depth - 1]
            next_level_assets: List[str] = []

            for parent_id in current_level_assets:
                children = await self.get_asset_relations(parent_id)
                children_by_parent[parent_id] = children
                next_level_assets.extend(children)

            # De-duplicate while preserving order
            dedup_next_level = list(dict.fromkeys(next_level_assets))
            levels.append(dedup_next_level)

            logger.info(
                f"Hierarchy level {depth + 1}: found {len(dedup_next_level)} assets"
            )

            if not dedup_next_level:
                logger.warning(
                    f"No assets found at hierarchy level {depth + 1}. Stopping traversal."
                )
                break

        return levels, children_by_parent
    
    async def read_device_attributes(
        self, 
        asset_id: str, 
        scope: str = "SERVER_SCOPE"
    ) -> Dict[str, Any]:
        """
        Read attributes from a ThingsBoard device/asset.
        
        Args:
            asset_id: Device/Asset ID
            scope: Attribute scope (SERVER_SCOPE or SHARED_SCOPE)
            
        Returns:
            Dictionary of attribute key-value pairs
        """
        url = f"{self.base_url}/api/plugins/telemetry/ASSET/{asset_id}/values/attributes/{scope}"
        headers = await self._get_headers()
        
        try:
            response = await self._client.get(url, headers=headers)
            response.raise_for_status()
            
            attributes = response.json()
            
            # Convert list of {key, value} objects to dictionary
            attributes_dict = {item['key']: item['value'] for item in attributes}
            
            logger.debug(f"Read {len(attributes_dict)} attributes from {asset_id}")
            return attributes_dict
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to read attributes for {asset_id}: {e}")
            raise
    
    async def write_device_telemetry(
        self, 
        device_id: str, 
        telemetry: Dict[str, Any]
    ) -> None:
        """
        Write telemetry data to a ThingsBoard device/asset.
        
        Args:
            device_id: Device/Asset ID
            telemetry: Telemetry data with 'ts' and 'values' keys
            
        Example telemetry format:
            {
                "ts": 1640000000000,  # Timestamp in milliseconds
                "values": {
                    "daily_energy_kwh_forecast": 150.5
                }
            }
        """
        url = f"{self.base_url}/api/plugins/telemetry/ASSET/{device_id}/timeseries/ANY"
        headers = await self._get_headers()
        
        try:
            response = await self._client.post(url, headers=headers, json=telemetry)
            response.raise_for_status()
            
            logger.debug(f"Wrote telemetry to {device_id}")
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to write telemetry to {device_id}: {e}")
            raise
    
    async def write_bulk_telemetry(
        self,
        device_id: str,
        telemetry_list: List[Dict[str, Any]]
    ) -> None:
        """
        Write multiple telemetry records to a device.
        
        Args:
            device_id: Device/Asset ID
            telemetry_list: List of telemetry records
        """
        if not telemetry_list:
            logger.warning(f"No telemetry records to write for {device_id}")
            return

        logger.info(
            f"Writing {len(telemetry_list)} telemetry records to {device_id} in a single API call"
        )

        url = f"{self.base_url}/api/plugins/telemetry/ASSET/{device_id}/timeseries/ANY"
        headers = await self._get_headers()

        try:
            # ThingsBoard accepts a list of {ts, values} objects for bulk timeseries insert.
            response = await self._client.post(url, headers=headers, json=telemetry_list)
            response.raise_for_status()

            logger.info(f"Successfully wrote {len(telemetry_list)} records to {device_id}")

        except httpx.HTTPError as e:
            logger.error(f"Failed to write bulk telemetry to {device_id}: {e}")
            raise
    
    async def asset_exists(self, asset_id: str) -> bool:
        """
        Check if an asset exists in ThingsBoard.
        
        Args:
            asset_id: Asset ID to check
            
        Returns:
            True if asset exists, False otherwise
        """
        url = f"{self.base_url}/api/asset/{asset_id}"
        headers = await self._get_headers()
        
        try:
            response = await self._client.get(url, headers=headers)
            
            if response.status_code == 404:
                logger.warning(f"Asset {asset_id} not found in ThingsBoard")
                return False
            
            response.raise_for_status()
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Error checking asset existence for {asset_id}: {e}")
            return False

    async def has_historical_data(self, asset_id: str, start_dt: datetime, end_dt: datetime) -> bool:
        """
        Check whether telemetry exists for the asset within the given date range.
        Uses presence of any timeseries key with at least one datapoint as a proxy.
        """
        try:
            # First, get available telemetry keys
            keys_url = f"{self.base_url}/api/plugins/telemetry/ASSET/{asset_id}/keys/timeseries"
            headers = await self._get_headers()
            keys_resp = await self._client.get(keys_url, headers=headers)

            if keys_resp.status_code == 404:
                logger.warning(f"No telemetry keys found for asset {asset_id}")
                return False

            keys_resp.raise_for_status()
            keys = keys_resp.json()
            if not keys:
                logger.warning(f"Asset {asset_id} has no telemetry keys")
                return False

            # Probe the first key for any datapoint in the range
            probe_key = keys[0]
            query_url = f"{self.base_url}/api/plugins/telemetry/ASSET/{asset_id}/values/timeseries"
            params = {
                "keys": probe_key,
                "startTs": int(start_dt.timestamp() * 1000),
                "endTs": int(end_dt.timestamp() * 1000),
                "limit": 1
            }
            data_resp = await self._client.get(query_url, headers=headers, params=params)

            if data_resp.status_code == 404:
                logger.warning(f"No telemetry for key {probe_key} on asset {asset_id}")
                return False

            data_resp.raise_for_status()
            data = data_resp.json()

            has_data = bool(data.get(probe_key))
            if not has_data:
                logger.warning(f"No telemetry data in range for asset {asset_id}")
            return has_data

        except httpx.HTTPError as e:
            logger.error(f"Error checking historical data for {asset_id}: {e}")
            return False
