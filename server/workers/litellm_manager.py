import os
import urllib.request
import urllib.parse
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000")
LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "sk-master-key-pilot-stage-a")

class LiteLLMKeyManager:
    """
    Automates the provisioning and lifecycle of virtual AI keys in LiteLLM:
    - Per-person & per-project keys
    - Budget limits (max_budget, duration)
    - Rate limits (TPM, RPM)
    - Model whitelists (restricting to approved models)
    """

    def __init__(self, base_url: str = LITELLM_URL, master_key: str = LITELLM_MASTER_KEY):
        self.base_url = base_url.rstrip("/")
        self.master_key = master_key

    def generate_virtual_key(
        self,
        key_alias: str,
        person_id: str,
        project_id: str,
        monthly_budget_usd: float = 100.0,
        rate_limit_tpm: int = 60000,
        rate_limit_rpm: int = 60,
        allowed_models: Optional[list] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/key/generate"
        payload = {
            "key_alias": key_alias,
            "max_budget": monthly_budget_usd,
            "budget_duration": "30d",
            "tpm_limit": rate_limit_tpm,
            "rpm_limit": rate_limit_rpm,
            "models": allowed_models or ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"],
            "metadata": {
                "person_id": person_id,
                "project_id": project_id
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.master_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Generated virtual key for {key_alias}: key_id={data.get('key')}")
                return data
        except Exception as e:
            logger.warning(f"Failed to communicate with LiteLLM at {url}: {e}. (Mock key generated for offline use)")
            return {
                "key": f"sk-virtual-{key_alias}-mock",
                "key_alias": key_alias,
                "max_budget": monthly_budget_usd,
                "is_mock": True
            }

    def get_key_info(self, key_hash: str) -> Dict[str, Any]:
        url = f"{self.base_url}/key/info?key={key_hash}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.master_key}"},
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {"spend": 0.0, "max_budget": 100.0}

