"""
Download a file from a Google Drive share link without extra dependencies.

Usage:
    from utils.download_gdrive import download_from_gdrive
    download_from_gdrive("https://drive.google.com/file/d/FILEID/view?usp=sharing", dest="downloads/")

This script handles the common Google Drive large-file confirmation flow by extracting
the confirmation token from cookies or the HTML and then streaming the file to disk.
"""
from pathlib import Path
import urllib.request
import urllib.parse
import http.cookiejar
import re
import os
from typing import Optional


def _extract_drive_id(url: str) -> str:
    """Extract the Google Drive file id from several share link formats.

    Raises ValueError if no file id can be found.
    """
    if not url:
        raise ValueError("Empty URL")
    url = url.strip()
    if not urllib.parse.urlparse(url).scheme:
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "id" in qs and qs["id"]:
        return qs["id"][0]
    # path like /file/d/<id>/view
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", parsed.path)
    if m:
        return m.group(1)
    # fallback: sometimes id appears in the whole url
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    raise ValueError(f"Could not extract Google Drive file id from URL: {url}")


def _filename_from_cd(cd: Optional[str]) -> Optional[str]:
    """Extract filename from Content-Disposition header if present."""
    if not cd:
        return None
    m = re.search(r"filename\*=UTF-8\'\'(?P<fname>[^;]+)", cd)
    if m:
        return urllib.parse.unquote(m.group("fname"))
    m = re.search(r"filename=\"?(?P<fname>[^\";]+)\"?", cd)
    if m:
        return m.group("fname")
    return None


def _get_confirm_token_from_cookies(cj: http.cookiejar.CookieJar) -> Optional[str]:
    for cookie in cj:
        if cookie.name.startswith("download_warning"):
            return cookie.value
    return None


def download_from_gdrive(url: str, dest: Optional[str] = None, chunk_size: int = 32768, overwrite: bool = False) -> str:
    """
    Download a file from a Google Drive share link.

    Args:
        url: Google Drive share URL
        dest: destination file path or directory. If None, save to current directory
              using the filename from the response (or the file id if unknown).
        chunk_size: bytes to read per iteration while streaming
        overwrite: whether to overwrite an existing file

    Returns:
        Path to the downloaded file (string).
    """
    file_id = _extract_drive_id(url)
    base_url = f"https://docs.google.com/uc?export=download&id={file_id}"

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "python-urllib/3")]

    # initial request
    resp = opener.open(base_url)
    content = resp.read()

    # try to determine if the response is an HTML confirmation page
    content_type = resp.getheader("Content-Type") or ""
    is_html = content_type.startswith("text/html") or (b"<html" in content[:1024].lower())

    # If HTML, look for a confirmation token in cookies or in the page
    confirm_token = None
    if is_html:
        confirm_token = _get_confirm_token_from_cookies(cj)
        if not confirm_token:
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            m = re.search(r"confirm=([0-9A-Za-z-_]+)&", text)
            if m:
                confirm_token = m.group(1)

    # determine filename (may be updated after a confirm request)
    cd = resp.getheader("Content-Disposition")
    filename = _filename_from_cd(cd)

    # helper to resolve final dest path
    def _resolve_dest_path(proposed_name: Optional[str]) -> Path:
        if proposed_name:
            name = proposed_name
        else:
            name = file_id
        if dest is None:
            dest_path = Path.cwd() / name
        else:
            dest_p = Path(dest)
            if dest_p.is_dir():
                dest_path = dest_p / name
            else:
                # dest provided as file path
                dest_path = dest_p
        # handle collisions
        if dest_path.exists() and not overwrite:
            raise FileExistsError(f"File exists: {dest_path} (use overwrite=True to replace)")
        return dest_path

    # If we have a confirm token, make the confirmed request and stream to disk
    if confirm_token:
        final_url = f"{base_url}&confirm={confirm_token}"
        with opener.open(final_url) as final_resp:
            cd = final_resp.getheader("Content-Disposition")
            filename = _filename_from_cd(cd) or filename
            dest_path = _resolve_dest_path(filename)
            total = final_resp.getheader("Content-Length")
            total = int(total) if total is not None else None
            os.makedirs(os.path.dirname(str(dest_path)) or ".", exist_ok=True)
            bytes_written = 0
            print(f"Downloading to {dest_path} ...")
            with open(dest_path, "wb") as out_f:
                while True:
                    chunk = final_resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    bytes_written += len(chunk)
                    if total:
                        percent = bytes_written / total * 100
                        print(f"\r{bytes_written}/{total} bytes ({percent:.1f}%)", end="", flush=True)
            if total:
                print()
            return str(dest_path)

    # Not an HTML confirmation page -> the content read earlier should be the file
    # Use filename if available, otherwise fallback to file id
    dest_path = _resolve_dest_path(filename)
    os.makedirs(os.path.dirname(str(dest_path)) or ".", exist_ok=True)
    print(f"Downloading to {dest_path} ...")
    with open(dest_path, "wb") as out_f:
        out_f.write(content)
    return str(dest_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download a file from a Google Drive share link")
    parser.add_argument("url", help="Google Drive share URL")
    parser.add_argument("--dest", "-d", default=None, help="Destination file or directory")
    parser.add_argument("--chunk-size", type=int, default=32768, help="Chunk size in bytes for streaming (default 32768)")
    parser.add_argument("--overwrite", "-o", action="store_true", help="Overwrite existing file")
    args = parser.parse_args()

    out = download_from_gdrive(args.url, dest=args.dest, chunk_size=args.chunk_size, overwrite=args.overwrite)
    print("Saved to", out)
