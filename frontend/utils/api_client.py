# ===========================================================================
# SecureBank — HTTP API Client
# Thread-safe helper for all Tkinter→Flask calls.
# ===========================================================================
import requests
import threading
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv('API_BASE_URL', 'http://localhost:5000/api')
_TIMEOUT = 10  # seconds


class APIClient:
    """Stateful API client that stores the JWT token after login."""

    def __init__(self):
        self.token = None
        self.user = None

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _parse(self, r):
        """
        Normalise any Flask response into {success, data/error} format.
        Handles Flask-JWT-Extended error responses that use 'msg' key.
        """
        try:
            data = r.json()
        except ValueError:
            return {"success": False, "error": f"Non-JSON response (HTTP {r.status_code})"}

        # If the API already returns our format, pass through
        if "success" in data:
            return data

        # Flask-JWT-Extended error format: {"msg": "..."}
        if r.status_code >= 400:
            err_msg = data.get("msg") or data.get("error") or data.get("message") or str(data)
            return {"success": False, "error": f"[{r.status_code}] {err_msg}"}

        # Successful but not our format — wrap it
        return {"success": True, "data": data}

    # ---- synchronous helpers (called from background threads) ---------------
    def get(self, path, params=None):
        r = requests.get(f"{API_URL}{path}", headers=self._headers(),
                         params=params, timeout=_TIMEOUT)
        return self._parse(r)

    def post(self, path, data=None):
        r = requests.post(f"{API_URL}{path}", headers=self._headers(),
                          json=data, timeout=_TIMEOUT)
        return self._parse(r)

    def put(self, path, data=None):
        r = requests.put(f"{API_URL}{path}", headers=self._headers(),
                         json=data, timeout=_TIMEOUT)
        return self._parse(r)

    # ---- login (special: stores token) -------------------------------------
    def login(self, username, password):
        """Returns (success, message, role)."""
        try:
            r = requests.post(
                f"{API_URL}/auth/login",
                json={"username": username, "password": password},
                timeout=_TIMEOUT
            )
            try:
                data = r.json()
            except ValueError:
                return False, f"Server error (HTTP {r.status_code})", None

            if data.get("success"):
                self.token = data["token"]
                self.user  = data["user"]
                return True, "Login successful", data["user"]["role"]

            err = data.get("error") or data.get("msg") or "Unknown error"
            return False, err, None
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to server. Is the backend running?", None
        except Exception as e:
            return False, str(e), None

    # ---- async wrapper (runs call in thread, invokes callback on main) -----
    def async_call(self, method, path, callback, root, data=None, params=None):
        """
        Execute an API call in a background thread, then schedule
        callback(result) on the Tkinter main loop via root.after().
        """
        def _work():
            try:
                if method == 'GET':
                    result = self.get(path, params=params)
                elif method == 'POST':
                    result = self.post(path, data=data)
                elif method == 'PUT':
                    result = self.put(path, data=data)
                else:
                    result = {"success": False, "error": f"Unknown method {method}"}
            except requests.exceptions.ConnectionError:
                result = {"success": False, "error": "Connection lost. Is the backend still running?"}
            except Exception as e:
                result = {"success": False, "error": str(e)}

            # Schedule callback on Tkinter main thread
            try:
                root.after(0, lambda r=result: callback(r))
            except Exception:
                pass  # Window might have been closed

        t = threading.Thread(target=_work, daemon=True)
        t.start()


# Global singleton
api = APIClient()
