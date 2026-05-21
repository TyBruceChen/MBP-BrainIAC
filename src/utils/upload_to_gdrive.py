"""
Upload file(s) to a Google Drive folder using a credentials JSON file.

Supports both service account credentials JSON and OAuth client_secrets JSON
(installed/web). For OAuth client credentials the script will open a browser
to authorize the app (local server flow).

Dependencies:
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

Example:
    python src/utils/upload_to_gdrive.py --creds credentials.json --folder-id YOUR_FOLDER_ID path/to/file1.nii.gz path/to/dir/

Notes:
 - For service account credentials the file will be uploaded into the service
   account's Drive (or into a shared drive / delegated account if configured).
 - The script uses the full Drive scope (drive) so it can place files into an
   arbitrary folder id. Consider using a narrower scope if appropriate.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Iterable, List


try:
    import google.auth
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover - helpful error if libs missing
    raise RuntimeError(
        "Missing Google API libraries. Install with: ``pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib``"
    )


SCOPES = ["https://www.googleapis.com/auth/drive"]


def load_credentials(creds_json_path: str):
    """Load credentials from a JSON file.

    Detects service account JSON (contains "type": "service_account") or
    OAuth client secrets (contains "installed" or "web"). For client secrets
    it runs the InstalledAppFlow to obtain user credentials.
    """
    creds_json_path = str(creds_json_path)
    with open(creds_json_path, "r") as f:
        data = json.load(f)

    # Service account
    if isinstance(data, dict) and data.get("type") == "service_account":
        creds = service_account.Credentials.from_service_account_file(creds_json_path, scopes=SCOPES)
        return creds

    # OAuth client secrets (installed or web)
    if "installed" in data or "web" in data:
        flow = InstalledAppFlow.from_client_secrets_file(creds_json_path, SCOPES)
        creds = flow.run_local_server(port=0)
        return creds

    raise ValueError("Unrecognized credentials JSON format. Provide a service account JSON or an OAuth client_secrets JSON.")


def _gather_files(paths: Iterable[str], recursive: bool = False) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"Warning: path does not exist, skipping: {path}")
            continue
        if path.is_file():
            out.append(path)
            continue
        if path.is_dir():
            if recursive:
                for f in path.rglob("*"):
                    if f.is_file():
                        out.append(f)
            else:
                for f in path.iterdir():
                    if f.is_file():
                        out.append(f)
    return out


def upload_file(service, filepath: Path, folder_id: str | None = None) -> dict:
    """Upload a single file to Google Drive. Returns the created file resource.
    """
    name = filepath.name
    mimetype, _ = mimetypes.guess_type(str(filepath))
    file_metadata = {"name": name}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(str(filepath), mimetype=mimetype or None, resumable=True)

    request = service.files().create(body=file_metadata, media_body=media, fields="id,name,size")
    response = None
    try:
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"Uploading {name}: {progress}%")
        return response
    except HttpError as e:
        raise RuntimeError(f"Failed to upload {filepath}: {e}") from e


def upload_files(creds_json: str, paths: Iterable[str], folder_id: str | None = None, recursive: bool = False, dry_run: bool = False) -> List[dict]:
    creds = load_credentials(creds_json)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    files_to_upload = _gather_files(paths, recursive=recursive)
    if not files_to_upload:
        print("No files found to upload.")
        return []

    uploaded = []
    for fp in files_to_upload:
        if dry_run:
            print(f"DRY RUN: would upload {fp} to folder {folder_id or 'root'}")
            continue
        print(f"Uploading {fp} ...")
        info = upload_file(service, fp, folder_id)
        print(f"Uploaded: {info.get('name')} (id: {info.get('id')})")
        uploaded.append(info)

    return uploaded


def _parse_args():
    p = argparse.ArgumentParser(description="Upload files to a Google Drive folder using a credentials JSON file")
    p.add_argument("--creds", required=True, help="Path to credentials JSON file (service account or client_secrets.json)")
    p.add_argument("--folder-id", required=False, default=None, help="Google Drive folder ID to upload into. If omitted uploads to Drive root or service account root.")
    p.add_argument("--recursive", "-r", action="store_true", help="If a directory is provided, recurse into subdirectories")
    p.add_argument("--dry-run", action="store_true", help="Print what would be uploaded without performing uploads")
    p.add_argument("paths", nargs="+", help="File or directory paths to upload")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    try:
        uploaded = upload_files(args.creds, args.paths, folder_id=args.folder_id, recursive=args.recursive, dry_run=args.dry_run)
        print(f"Done. Uploaded {len(uploaded)} files.")
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
