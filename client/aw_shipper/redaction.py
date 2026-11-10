import re
from typing import Dict, Any, List

class RedactionEngine:
    """
    Scrubs sensitive client-side information (credentials, tokens, private browsing)
    BEFORE telemetry payloads leave the laptop.
    """

    def __init__(self, patterns: List[str]):
        self.compiled = [re.compile(p) for p in patterns]

    def redact_text(self, text: str) -> str:
        if not text:
            return ""
        scrubbed = text
        for pat in self.compiled:
            scrubbed = pat.sub("[REDACTED]", scrubbed)
        return scrubbed

    def scrub_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = dict(event)
        data = dict(cleaned.get("data", {}))

        if "title" in data and isinstance(data["title"], str):
            data["title"] = self.redact_text(data["title"])
        
        if "url" in data and isinstance(data["url"], str):
            # Strip query parameters that might carry session tokens
            url_str = data["url"]
            if "?" in url_str:
                base, _ = url_str.split("?", 1)
                url_str = f"{base}?[REDACTED_PARAMS]"
            data["url"] = self.redact_text(url_str)

        cleaned["data"] = data
        return cleaned

