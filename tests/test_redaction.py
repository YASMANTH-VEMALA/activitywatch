import unittest
from client.aw_shipper.redaction import RedactionEngine
from client.aw_shipper.config import ShipperConfig

class TestRedaction(unittest.TestCase):
    def setUp(self):
        config = ShipperConfig()
        self.engine = RedactionEngine(config.redaction_patterns)

    def test_strip_sensitive_credentials(self):
        text = "Login with password=SecretPassword123 and token: eyJhbGciOi"
        redacted = self.engine.redact_text(text)
        self.assertNotIn("SecretPassword123", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_scrub_url_query_parameters(self):
        event = {
            "timestamp": "2026-11-10T10:00:00Z",
            "data": {
                "title": "Google Chrome - Internal Dashboard",
                "url": "https://intranet.company.com/auth?token=super_secret_jwt_token_123"
            }
        }
        cleaned = self.engine.scrub_event(event)
        self.assertNotIn("super_secret_jwt_token_123", cleaned["data"]["url"])
        self.assertIn("[REDACTED_PARAMS]", cleaned["data"]["url"])

    def test_strip_private_browsing(self):
        event = {
            "timestamp": "2026-11-10T10:00:00Z",
            "data": {
                "title": "Private Browsing - Confidential Research"
            }
        }
        cleaned = self.engine.scrub_event(event)
        self.assertIn("[REDACTED]", cleaned["data"]["title"])

if __name__ == "__main__":
    unittest.main()
