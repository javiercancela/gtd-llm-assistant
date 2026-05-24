import pathlib
import json
from typing import Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = ".token.json"

SCOPES = [
    "https://www.googleapis.com/auth/tasks",
]


def _build_tasks_service() -> Any:
    creds = _get_credentials()
    return build("tasks", "v1", credentials=creds)


def _load_oauth_client_config() -> dict[str, Any]:
    client_secret_path = pathlib.Path(CLIENT_SECRET_FILE)
    if not client_secret_path.exists():
        raise RuntimeError(
            "Missing OAuth client file 'client_secret.json'. "
            "Create a Google Cloud OAuth Desktop App client and save it as "
            "'client_secret.json' in the project root."
        )

    client_config = json.loads(client_secret_path.read_text(encoding="utf-8"))
    if "installed" in client_config:
        return client_config

    if "web" in client_config:
        raise RuntimeError(
            "Invalid OAuth client type in 'client_secret.json': found 'web', "
            "but local OAuth requires a Desktop App client (with 'installed'). "
            "Create a Desktop App OAuth client in Google Cloud Console and "
            "replace this file."
        )

    raise RuntimeError(
        "Invalid OAuth client file format. Expected top-level key " "'installed' (Desktop App credentials)."
    )


def _get_credentials() -> Credentials:
    token_path = pathlib.Path(TOKEN_FILE)

    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            scopes=SCOPES,
        )

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_config(
            _load_oauth_client_config(),
            scopes=SCOPES,
        )

        # Starts a temporary local server and opens the browser.
        # Google redirects back to localhost after consent.
        creds = flow.run_local_server(
            host="localhost",
            port=0,
            access_type="offline",
            prompt="consent",
        )

    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds
