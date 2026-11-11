import os
import sys
import time
import json
import socket
import urllib.request
import subprocess
from run_site_tests import SimpleWebSocket, eval_js, take_screenshot

site_dir = r"C:\Users\Илья\Desktop\Новая папка (2)"
chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
chrome_port = 9555
user_data = os.path.join(site_dir, ".chrome_deep_profile")

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

    print("--- 1. VERIFY TOP BAR & SINGLE RED DOT ---")
    brand_text = eval_js(ws, "document.querySelector('.brand-word').innerText.trim()")
    print("Brand text:", repr(brand_text))
    assert "TKACH" in brand_text, "Brand text missing TKACH"
    
    # Check red dot styling
    has_red_dot = eval_js(ws, "Boolean(document.querySelector('.red-dot-i'))")
    assert has_red_dot, "red-dot-i element missing"

    # Verify logo is transparent png without black background style
    logo_bg = eval_js(ws, "window.getComputedStyle(document.querySelector('.dark-logo-img')).backgroundColor")
    print("Dark logo computed background:", logo_bg)
    assert "rgba(0, 0, 0, 0)" in logo_bg or "transparent" in logo_bg, f"Logo should be transparent, got {logo_bg}"

    print("--- 2. VERIFY VACANCY INPUT BACKSPACE & NUMERIC TYPING ---")
    eval_js(ws, "document.getElementById('cardApplication').classList.add('is-open')")
    
    # Test: clear field, then type '5'
    vac_res = eval_js(ws, """
    (() => {
        let inp = document.getElementById('vacLinear');
        inp.value = '';
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        let valWhenEmpty = inp.value;
        inp.value = '5';
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        let valAfterTyping5 = inp.value;
        return { valWhenEmpty, valAfterTyping5 };
    })()
    """)
    print("Vacancy input test:", vac_res)
    assert vac_res["valWhenEmpty"] == "", f"Expected empty string when user clears, got {vac_res['valWhenEmpty']}"
    assert vac_res["valAfterTyping5"] == "5", f"Expected '5' after typing 5, got {vac_res['valAfterTyping5']}"

    # Test: blur on empty field restores 0
    vac_blur_res = eval_js(ws, """
    (() => {
        let inp = document.getElementById('vacLinear');
        inp.value = '';
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('blur', { bubbles: true }));
        return inp.value;
    })()
    """)
    print("Vacancy blur on empty string:", repr(vac_blur_res))
    assert vac_blur_res == "0", f"Expected '0' on blur after empty, got {vac_blur_res}"

    print("--- 3. VERIFY CARET PRESERVATION IN CALCULATOR ---")
    caret_test = eval_js(ws, """
    (() => {
        let inp = document.getElementById('calcAnnualIncome');
        inp.value = '1 200 000';
        inp.setSelectionRange(1, 1);
        // Simulate inserting '5' after '1' -> '15 200 000'
        inp.value = '15 200 000';
        inp.setSelectionRange(2, 2);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        return {
            val: inp.value,
            selStart: inp.selectionStart,
            selEnd: inp.selectionEnd
        };
    })()
    """)
    print("Caret preservation test:", caret_test)
    assert caret_test["val"] == "15 200 000" or caret_test["val"] == "15\xa0200\xa0000", f"Unexpected formatted value {caret_test['val']}"
    assert caret_test["selStart"] == 2, f"Expected caret at index 2, got {caret_test['selStart']}"

    print("--- 4. VERIFY CARD 1 HIGHLIGHT INTERACTION ---")
    eval_js(ws, "document.getElementById('cardServices').classList.add('is-open')")
    service1 = eval_js(ws, """
    (() => {
        let s = document.querySelectorAll('.service-item')[0];
        s.click();
        return s.classList.contains('is-active');
    })()
    """)
    print("Service 1 is-active on click:", service1)
    assert service1, "Service item should toggle is-active on click"

    print("--- 5. VERIFY FORM SUBMIT AND WIDGET REMOVAL ---")
    # Verify widgets from user screenshots are absent
    copy_btn_exists = eval_js(ws, "Boolean(document.getElementById('copyLeadBtn') || document.getElementById('quickCopyPreviewBtn'))")
    preview_exists = eval_js(ws, "Boolean(document.querySelector('.message-preview-container'))")
    assert not copy_btn_exists, "copy button must be removed per user screenshot"
    assert not preview_exists, "message preview container must be removed per user screenshot"

    eval_js(ws, """
    (() => {
        document.getElementById('companyName').value = 'ООО Тестовая Компания';
        document.getElementById('vacLinear').value = '3';
        document.getElementById('vacSpecialist').value = '1';
        document.getElementById('vacTop').value = '0';
        document.getElementById('fullName').value = 'Алексей Смирнов';
        document.getElementById('phone').value = '+7 (903) 111-22-33';
        document.getElementById('extraContact').value = 'WhatsApp';
        document.getElementById('submitAppBtn').click();
    })()
    """)
    time.sleep(0.5)

    success_displayed = eval_js(ws, "window.getComputedStyle(document.getElementById('formSuccessBox')).display !== 'none'")
    assert success_displayed, "Success box must be visible after submission"

    # Check localStorage persistence
    saved_leads = eval_js(ws, "localStorage.getItem('tkachi_leads')")
    print("Saved leads in localStorage:", saved_leads)
    assert "ООО Тестовая Компания" in saved_leads, "Lead must be saved in localStorage"
    success_text = eval_js(ws, "document.getElementById('formSuccessBox').innerText")
    assert "olga.tkach@tkachi.pro" in success_text and "ilya.zotov@tkachi.pro" in success_text, "Founders emails missing from success notification"

    print("\nALL DEEP VERIFICATION TESTS PASSED PERFECTLY!")
    ws.close()
finally:
    proc.terminate()
