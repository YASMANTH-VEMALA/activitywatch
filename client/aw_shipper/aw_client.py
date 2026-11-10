import urllib.request
import urllib.parse
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class AWLocalClient:
    """
    Communicates with the local ActivityWatch server running on localhost:5600.
    """

    def __init__(self, base_url: str = "http://localhost:5600/api/0"):
        self.base_url = base_url.rstrip("/")

    def get_buckets(self) -> Dict[str, Any]:
        url = f"{self.base_url}/buckets/"
        req = urllib.request.Request(url, headers={"User-Agent": "aw-shipper/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            # When running without aw-server, return empty dict gracefully
            return {}

    def get_events(self, bucket_id: str, start_time: Optional[datetime] = None, limit: int = 500) -> List[Dict[str, Any]]:
        params = {"limit": limit}
        if start_time:
            params["start"] = start_time.isoformat()
        
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}/buckets/{bucket_id}/events?{query_string}"
        req = urllib.request.Request(url, headers={"User-Agent": "aw-shipper/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return []
