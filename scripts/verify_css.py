import re
import urllib.request
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for path in ["/", "/app", "/streamline.css", "/login"]:
    url = "https://download.spikeiq.cloud" + path
    try:
        r = urllib.request.urlopen(url, timeout=20)
        body = r.read()
        print(path, r.status, r.headers.get("content-type"), len(body))
        if path != "/streamline.css":
            html = body.decode("utf-8", "replace")
            print("  has_streamline_link", "streamline.css" in html)
            print("  hrefs", re.findall(r'href="([^"]+)"', html)[:15])
        else:
            print("  css_snip", body[:120])
    except Exception as e:
        print(path, "ERR", e)
