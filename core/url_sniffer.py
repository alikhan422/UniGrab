import urllib.parse
import requests

DIRECT_EXTENSIONS = (
    '.exe', '.zip', '.rar', '.7z', '.tar', '.gz', '.iso', '.dmg',
    '.msi', '.bin', '.pdf', '.apk', '.doc', '.docx', '.xls', '.xlsx',
    '.ppt', '.pptx', '.txt', '.csv'
)

def is_direct_download(url):
    try:
        path = urllib.parse.urlparse(url).path.lower()
        for ext in DIRECT_EXTENSIONS:
            if path.endswith(ext):
                return True, ext[1:].upper()

        # Agar extension na ho to Content-Type se check karein (fast timeout)
        resp = requests.head(url, allow_redirects=True, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        content_type = resp.headers.get("content-type", "").lower()
        if any(b in content_type for b in ["application/", "octet-stream", "zip", "pdf"]):
            return True, "FILE"
    except Exception:
        pass

    return False, "VIDEO"
