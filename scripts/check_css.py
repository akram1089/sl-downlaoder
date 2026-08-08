import re
import urllib.request

html = urllib.request.urlopen("https://download.spikeiq.cloud/app", timeout=20).read().decode("utf-8", "replace")
print("html_len", len(html))
print(html[:1500])
print("---")
css = re.findall(r'href="([^"]+\.css[^"]*)"', html)
js = re.findall(r'src="([^"]+)"', html)
print("css", css)
print("js", [x for x in js if "_next" in x][:8])
for u in css[:6]:
    url = u if u.startswith("http") else "https://download.spikeiq.cloud" + u
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
            print(url, r.status, r.headers.get("content-type"), len(body), body[:80])
    except Exception as e:
        print(url, "ERR", e)

# also check homepage
home = urllib.request.urlopen("https://download.spikeiq.cloud/", timeout=20).read().decode("utf-8", "replace")
hcss = re.findall(r'href="([^"]+\.css[^"]*)"', home)
print("home css", hcss)
for u in hcss[:4]:
    url = u if u.startswith("http") else "https://download.spikeiq.cloud" + u
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            print("home", url, r.status, r.headers.get("content-type"), len(r.read()))
    except Exception as e:
        print("home", url, "ERR", e)
