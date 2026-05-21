"""
Utility to download a file from a Dropbox shared link.

Provides download_from_dropbox(url, dest=None, chunk_size=1024*1024, overwrite=False).

Usage:
    from utils.download_dropbox import download_from_dropbox
    download_from_dropbox("https://www.dropbox.com/s/abcd1234/file.nii.gz?dl=0", dest="downloads/")
"""
import os
import re
import urllib.request
import urllib.parse
from typing import Optional


def _to_direct_dropbox_url(url: str) -> str:
    """
    Convert a Dropbox share URL to a direct-download URL by ensuring dl=1 in the query.
    If the URL is not a Dropbox URL it's returned unchanged.
    """
    if not url:
        raise ValueError("Empty URL")
    url = url.strip()
    if not urllib.parse.urlparse(url).scheme:
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if "dropbox.com" not in parsed.netloc:
        return url
    # Ensure dl=1
    qs = urllib.parse.parse_qs(parsed.query)
    qs["dl"] = ["1"]
    new_query = urllib.parse.urlencode(qs, doseq=True)
    parsed = parsed._replace(query=new_query)
    return urllib.parse.urlunparse(parsed)


def _filename_from_cd(cd: Optional[str]) -> Optional[str]:
    """Extract filename from Content-Disposition header if present."""
    if not cd:
        return None
    # look for filename="..." or filename=...
    m = re.search(r'filename\*=UTF-8\'\'(?P<fname>[^;]+)', cd)
    if m:
        return urllib.parse.unquote(m.group("fname"))
    m = re.search(r'filename=\"?(?P<fname>[^\";]+)\"?', cd)
    if m:
        return m.group("fname")
    return None


def download_from_dropbox(url: str, dest: Optional[str] = None, chunk_size: int = 1024 * 1024, overwrite: bool = False) -> str:
    """
    Download a file from a Dropbox share link to the local filesystem.

    Args:
        url: Dropbox share URL (e.g. https://www.dropbox.com/s/abcd/file.nii.gz?dl=0)
        dest: destination file path or directory. If None, save to current directory using the
              filename from the URL or response headers.
        chunk_size: number of bytes to read per chunk (default 1MB).
        overwrite: whether to overwrite an existing file.

    Returns:
        Path to the downloaded file.
    """
    direct_url = _to_direct_dropbox_url(url)
    req = urllib.request.Request(direct_url, headers={"User-Agent": "python-urllib/3"})
    try:
        with urllib.request.urlopen(req) as resp:
            # determine filename
            cd = resp.getheader("Content-Disposition")
            filename = _filename_from_cd(cd)
            if not filename:
                parsed = urllib.parse.urlparse(direct_url)
                filename = os.path.basename(parsed.path) or None
            if not filename:
                # fallback
                filename = "downloaded_file"

            # resolve destination path
            if dest is None:
                dest_path = os.path.join(os.getcwd(), filename)
            elif os.path.isdir(dest):
                dest_path = os.path.join(dest, filename)
            else:
                # treat dest as a file path
                dest_path = dest

            if os.path.exists(dest_path) and not overwrite:
                raise FileExistsError(f"File exists: {dest_path} (use overwrite=True to replace)")

            total = resp.getheader("Content-Length")
            total = int(total) if total is not None else None

            # stream to disk
            os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
            bytes_written = 0
            print(f"Downloading to {dest_path} ...")
            with open(dest_path, "wb") as out_f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    bytes_written += len(chunk)
                    if total:
                        percent = bytes_written / total * 100
                        print(f"\r{bytes_written}/{total} bytes ({percent:.1f}%)", end="", flush=True)
            if total:
                print()
            return dest_path
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error while downloading {direct_url}: {e}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error while downloading {direct_url}: {e}") from e


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download a file from a Dropbox share link")
    parser.add_argument("url", help="Dropbox share URL")
    parser.add_argument("--dest", "-d", default=None, help="Destination file or directory")
    parser.add_argument("--overwrite", "-o", action="store_true", help="Overwrite existing file")
    args = parser.parse_args()
    out = download_from_dropbox(args.url, args.dest, overwrite=args.overwrite)
    print("Saved to", out)
