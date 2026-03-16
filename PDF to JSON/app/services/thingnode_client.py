"""
ThingNode/ThingsBoard client service for writing asset attributes
"""
import os
from typing import Any, Dict

import requests

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

from ..utils.logger import logger

if load_dotenv:
    load_dotenv()


class ThingNodeClient:
    """Client for ThingNode attribute writes"""

    def __init__(self) -> None:
        self.host = os.getenv("THINGNODE_HOST", "https://cloud.thingsnode.cc").rstrip("/")
        self.username = os.getenv("THINGNODE_USERNAME", "")
        self.password = os.getenv("THINGNODE_PASSWORD", "")
        self.attribute_scope = os.getenv("THINGNODE_ATTRIBUTE_SCOPE", "SERVER_SCOPE")
        self.timeout_seconds = int(os.getenv("THINGNODE_TIMEOUT_SECONDS", "20"))

    def _validate_config(self) -> None:
        if not self.username or not self.password:
            raise ValueError("ThingNode credentials are missing. Set THINGNODE_USERNAME and THINGNODE_PASSWORD.")

    def get_jwt_token(self) -> str:
        """Authenticate and return JWT token"""
        self._validate_config()

        response = requests.post(
            f"{self.host}/api/auth/login",
            json={"username": self.username, "password": self.password},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        token = payload.get("token")
        if not token:
            raise ValueError("ThingNode login succeeded but no token was returned.")

        return token

    def write_asset_attributes(self, asset_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Write attributes to a ThingNode asset"""
        if not asset_id:
            raise ValueError("asset_id is required.")

        token = self.get_jwt_token()
        headers = {
            "X-Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.host}/api/plugins/telemetry/ASSET/{asset_id}/attributes/{self.attribute_scope}"
        response = requests.post(url, headers=headers, json=attributes, timeout=self.timeout_seconds)
        response.raise_for_status()

        logger.info(f"Asset attributes written to ThingNode for asset_id={asset_id}")
        return {
            "asset_id": asset_id,
            "status_code": response.status_code,
            "scope": self.attribute_scope,
            "host": self.host,
            "written": True,
        }


thingnode_client = ThingNodeClient()
