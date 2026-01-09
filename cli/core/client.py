import json
import urllib.request
import urllib.error
import sys
from typing import Dict, Any, Optional
from cli.core.config import settings

class APIClient:
    """
    Enterprise-grade HTTP Client using standard library.
    Handles headers, error parsing, and interaction with the backend.
    """

    def __init__(self):
        self.base_url = settings.api_url
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "SemanticSQL-CLI/1.0.0",
            "Accept": "application/json"
        }

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        if payload:
            data = json.dumps(payload).encode('utf-8')

        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)

        if settings.debug:
            print(f"[DEBUG] {method} {url}")
            if payload:
                print(f"[DEBUG] Payload: {json.dumps(payload)}")

        try:
            with urllib.request.urlopen(req, timeout=settings.timeout) as response:
                response_data = response.read().decode('utf-8')
                if not response_data:
                    return None
                return json.loads(response_data)

        except urllib.error.HTTPError as e:
            self._handle_error(e)
        except urllib.error.URLError as e:
            print(f"❌ Connection Error: {e.reason}")
            print(f"   URL: {url}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON response from server")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
            sys.exit(1)

    def _handle_error(self, e: urllib.error.HTTPError):
        """Parse structured API errors if available"""
        code = e.code
        try:
            error_body = e.read().decode('utf-8')
            error_json = json.loads(error_body)
            # Try to find Detail in common FastAPI format
            detail = error_json.get("detail", error_body)
        except Exception:
            detail = e.reason

        print(f"❌ API Error ({code}): {detail}")
        sys.exit(1)

    def post(self, path: str, payload: Dict[str, Any]) -> Any:
        return self._request("POST", path, payload)

    def get(self, path: str) -> Any:
        return self._request("GET", path)

client = APIClient()
