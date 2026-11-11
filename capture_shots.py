import os
import time
import json
import urllib.request
import subprocess
from run_site_tests import SimpleWebSocket, eval_js, take_screenshot

site_dir = r"C:\Users\Илья\Desktop\Новая папка (2)"
chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
chrome_port = 9777
user_data = os.path.join(site_dir, ".chrome_shot_profile")

proc = subprocess.Popen([
    chrome_exe,
    "--headless=new",
    f"--remote-debugging-port={chrome_port}",
    f"--user-data-dir={user_data}",
    "--no-first-run",
    f"file:///{site_dir}/index.html"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    time.sleep(2.0)
    tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{chrome_port}/json").read())
    ws = SimpleWebSocket(tabs[0]["webSocketDebuggerUrl"])

    # 1. Desktop Top View
    ws.call("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(0.5)
    take_screenshot(ws, os.path.join(site_dir, "screenshot_warm_beige_top.png"))
    print("Saved screenshot_warm_beige_top.png")

    # 2. Form with Live Message Preview
    eval_js(ws, """
    (() => {
        document.getElementById('cardApplication').classList.add('is-open');
        document.getElementById('companyName').value = 'ООО «ТехноПром Инвест»';
        document.getElementById('vacLinear').value = '5';
        document.getElementById('vacSpecialist').value = '2';
        document.getElementById('vacTop').value = '1';
        document.getElementById('fullName').value = 'Мария Воронова';
        document.getElementById('phone').value = '+7 (926) 333-22-11';
        document.getElementById('extraContact').value = 'Telegram @voronova_hr';
        document.getElementById('companyName').dispatchEvent(new Event('input', { bubbles: true }));
        document.getElementById('cardApplication').scrollIntoView({ behavior: 'instant', block: 'center' });
    })()
    """)
    time.sleep(0.5)
    take_screenshot(ws, os.path.join(site_dir, "screenshot_form_message_preview.png"))
    print("Saved screenshot_form_message_preview.png")

    # 3. Form Submitted - Sent Text Message & Messenger Buttons
    eval_js(ws, "document.getElementById('submitAppBtn').click()")
    time.sleep(0.5)
    take_screenshot(ws, os.path.join(site_dir, "screenshot_message_sent_success.png"))
    print("Saved screenshot_message_sent_success.png")

    ws.close()
finally:
    proc.terminate()
