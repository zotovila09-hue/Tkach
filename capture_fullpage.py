import os
import time
import json
import urllib.request
import subprocess
import base64
from run_site_tests import SimpleWebSocket, eval_js

site_dir = r"C:\Users\Илья\Desktop\Новая папка (2)"
chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
chrome_port = 9668
user_data = os.path.join(site_dir, ".chrome_fullshot_profile2")

import http.server
import threading
port = 8113

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

os.chdir(site_dir)
httpd = http.server.HTTPServer(("127.0.0.1", port), QuietHandler)
server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
server_thread.start()

proc = subprocess.Popen([
    chrome_exe,
    "--headless=new",
    f"--remote-debugging-port={chrome_port}",
    f"--user-data-dir={user_data}",
    "--no-first-run",
    "--disable-gpu",
    f"http://127.0.0.1:{port}/index.html"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    time.sleep(2.0)
    tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{chrome_port}/json").read())
    ws = SimpleWebSocket(tabs[0]["webSocketDebuggerUrl"])
    ws.call("Runtime.enable")
    ws.call("Page.enable")
    ws.call("Page.navigate", {"url": f"http://127.0.0.1:{port}/index.html"})
    time.sleep(1.5)

    # 1. Full page mobile screenshot (iPhone 12/13/14: 390px)
    ws.call("Emulation.setDeviceMetricsOverride", {
        "width": 390,
        "height": 844,
        "deviceScaleFactor": 2,
        "mobile": True
    })
    time.sleep(0.5)

    layout = ws.call("Page.getLayoutMetrics")
    content_size = layout.get("result", {}).get("contentSize", {})
    width = int(content_size.get("width", 390))
    height = int(content_size.get("height", 3000))
    print(f"Mobile page full content size: {width} x {height}")

    res = ws.call("Page.captureScreenshot", {
        "clip": {
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "scale": 1
        },
        "captureBeyondViewport": True
    })
    data = res.get("result", {}).get("data")
    if data:
        with open(os.path.join(site_dir, "screenshot_mobile_fullpage.png"), "wb") as f:
            f.write(base64.b64decode(data))
        print("Saved screenshot_mobile_fullpage.png")

    # 2. Full page desktop screenshot (1440px)
    ws.call("Emulation.setDeviceMetricsOverride", {
        "width": 1440,
        "height": 900,
        "deviceScaleFactor": 1,
        "mobile": False
    })
    time.sleep(0.5)
    layout_d = ws.call("Page.getLayoutMetrics")
    content_size_d = layout_d.get("result", {}).get("contentSize", {})
    w_d = int(content_size_d.get("width", 1440))
    h_d = int(content_size_d.get("height", 2000))
    print(f"Desktop page full content size: {w_d} x {h_d}")

    res_d = ws.call("Page.captureScreenshot", {
        "clip": {
            "x": 0,
            "y": 0,
            "width": w_d,
            "height": h_d,
            "scale": 1
        },
        "captureBeyondViewport": True
    })
    data_d = res_d.get("result", {}).get("data")
    if data_d:
        with open(os.path.join(site_dir, "screenshot_desktop_fullpage.png"), "wb") as f:
            f.write(base64.b64decode(data_d))
        print("Saved screenshot_desktop_fullpage.png")

finally:
    try:
        ws.close()
    except:
        pass
    proc.terminate()
    httpd.shutdown()
