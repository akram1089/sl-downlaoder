import urllib.request
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
html = urllib.request.urlopen("https://download.spikeiq.cloud/", timeout=20).read().decode("utf-8", "replace")
print(html[:2500])
print("----END HEAD----")
print("has html", "<html" in html.lower())
print("has body", "<body" in html.lower())
print("has head", "<head" in html.lower())
print("streamline", "streamline.css" in html)
