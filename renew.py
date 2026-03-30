import base64
import json
import time
import sys
import io
import requests
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth

# 解决乱码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 从系统环境变量获取配置 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENEW_URL = os.getenv("RENEW_URL")
USERNAME = os.getenv("MC_USERNAME")
TELEGRAM_API = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# 截图保存到当前目录下的 screenshots 文件夹
SAVE_DIR = Path("./screenshots")
SAVE_DIR.mkdir(exist_ok=True)

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_API}/sendPhoto"
        with open(photo_path, "rb") as photo:
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files={"photo": photo}, timeout=30)
    except Exception as e:
        print(f"[!] TG发送失败: {e}")

def get_gemini_indices(image_base64, task_text):
    # 按照要求，继续使用 gemini-2.5-flash
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"Task: {task_text}. This is a 3x3 image grid. Indices 0-8 from top-left. Return ONLY a JSON list like [0, 2, 5]."
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/png", "data": image_base64}}]}],
        "generationConfig": {"temperature": 0}
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        content = resp.json()['candidates'][0]['content']['parts'][0]['text']
        print(f"[*] AI 建议: {content.strip()}")
        return [int(n) for n in re.findall(r'\d+', content)]
    except Exception as e:
        print(f"[-] AI识别异常: {e}")
        return []

def solve_captcha(frame):
    try:
        instr = frame.locator('.rc-imageselect-instructions')
        if not instr.is_visible(timeout=3000): return False
        task = instr.inner_text().replace('\n', ' ')
        img_b64 = base64.b64encode(frame.locator('.rc-imageselect-payload').screenshot()).decode('utf-8')
        indices = get_gemini_indices(img_b64, task)
        tiles = frame.locator('.rc-imageselect-tile')
        for idx in indices:
            if idx < tiles.count():
                tiles.nth(idx).click()
                time.sleep(0.5)
        frame.locator('#recaptcha-verify-button').click()
        time.sleep(3)
        return True
    except: return False

def run():
    print(f"🚀 开始执行续期任务 (用户: {USERNAME})")
    with sync_playwright() as p:
        # GitHub 上必须用 headless=True
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        try:
            page.goto(RENEW_URL, timeout=60000)
            time.sleep(5)

            # 1. 冷却检测
            cooldown = page.locator('text=/can be renewed in/i')
            if cooldown.is_visible():
                msg = cooldown.inner_text()
                print(f"⚠️ 冷却中: {msg}")
                path = SAVE_DIR / "cooldown.png"
                page.screenshot(path=str(path))
                send_telegram_photo(str(path), f"⚠️ {USERNAME} 还没到续期时间\n{msg}")
                return

            # 2. 填写用户
            page.locator('input[name="username"]').fill(USERNAME)
            
            # 3. 触发验证
            anchor = page.frame_locator('iframe[title*="reCAPTCHA"][src*="anchor"]')
            anchor.locator('#recaptcha-anchor').click()
            time.sleep(5)

            # 4. 图片挑战
            challenge_frame = next((f for f in page.frames if "api2/bframe" in f.url), None)
            if challenge_frame:
                for r in range(6):
                    if not challenge_frame.locator('.rc-imageselect-instructions').is_visible(timeout=2000): break
                    print(f"[*] 正在处理第 {r+1} 轮图片挑战...")
                    solve_captcha(challenge_frame)
                    time.sleep(2)

            # 5. 点击 Renew
            submit_btn = page.locator('#submit-button')
            # 增加超时容忍度，GitHub Actions 有时网络慢
            page.wait_for_function("document.querySelector('#submit-button').value.includes('Renew') && !document.querySelector('#submit-button').disabled", timeout=30000)
            
            submit_btn.click()
            print("[+] 已点击 Renew 按钮")
            time.sleep(10)

            # 6. 结果截图
            res_path = SAVE_DIR / "result.png"
            page.screenshot(path=str(res_path))
            
            content = page.content().lower()
            if "renewed" in content or "success" in content:
                send_telegram_photo(str(res_path), f"✅ {USERNAME} 续期成功！")
            else:
                send_telegram_photo(str(res_path), f"⚠️ {USERNAME} 已尝试点击，结果请看截图")

        except Exception as e:
            print(f"[-] 错误: {e}")
            err_path = SAVE_DIR / "error.png"
            page.screenshot(path=str(err_path))
            send_telegram_photo(str(err_path), f"❌ {USERNAME} 运行报错: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
