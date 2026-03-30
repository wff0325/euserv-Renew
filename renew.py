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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# 默认值改为 1.5-flash，这个是最稳的
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
RENEW_URL = os.getenv("RENEW_URL")
USERNAME = os.getenv("MC_USERNAME")
TELEGRAM_API = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

SAVE_DIR = Path("./screenshots")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_API}/sendPhoto"
        with open(photo_path, "rb") as photo:
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files={"photo": photo}, timeout=30)
    except Exception as e:
        print(f"[!] Telegram 发送失败: {e}")

def get_gemini_indices(image_base64, task_text):
    """调用 Gemini AI 视觉识别"""
    # 构造 API URL，注意这里增加了 v1beta 以获得更好的模型兼容性
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"Task: {task_text}. This is a 3x3 image grid. Indices are 0-8 from top-left. Return ONLY a JSON list like [0, 2, 5]. If none match, return []."
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": image_base64}}
            ]
        }],
        "generationConfig": {"temperature": 0}
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        res_json = response.json()
        
        # --- 新增：错误信息打印 ---
        if 'error' in res_json:
            print(f"[-] Gemini API 报错: {res_json['error']['message']}")
            return []
        
        if 'candidates' not in res_json or not res_json['candidates']:
            print(f"[-] Gemini 未返回结果，可能被安全过滤拦截。响应: {res_json}")
            return []

        content = res_json['candidates'][0]['content']['parts'][0]['text']
        print(f"[*] AI 回复: {content.strip()}")
        return [int(n) for n in re.findall(r'\d+', content)]
    except Exception as e:
        print(f"[-] AI 识别捕获到异常: {e}")
        return []

def solve_captcha(challenge_frame):
    try:
        instr = challenge_frame.locator('.rc-imageselect-instructions')
        if not instr.is_visible(timeout=3000): return False
        
        task_text = instr.inner_text().replace('\n', ' ').strip()
        print(f"[*] 当前任务: {task_text}")
        
        payload_box = challenge_frame.locator('.rc-imageselect-payload')
        img_b64 = base64.b64encode(payload_box.screenshot()).decode('utf-8')
        
        indices = get_gemini_indices(img_b64, task_text)
        print(f"[*] AI 建议点击索引: {indices}")
        
        tiles = challenge_frame.locator('.rc-imageselect-tile')
        for idx in indices:
            if idx < tiles.count():
                tiles.nth(idx).click()
                time.sleep(0.5)
        
        challenge_frame.locator('#recaptcha-verify-button').click()
        time.sleep(3)
        return True
    except:
        return False

def run_auto_renew():
    print(f"🚀 启动续期 | 模型: {GEMINI_MODEL}")
    with sync_playwright() as p:
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
                print(f"⚠️ 尚未到期: {msg}")
                return

            # 2. 输入用户
            page.locator('input[name="username"]').fill(USERNAME)
            time.sleep(1)

            # 3. 触发验证
            print("[*] 正在触发 reCAPTCHA...")
            anchor_frame = page.frame_locator('iframe[title*="reCAPTCHA"][src*="anchor"]')
            anchor_frame.locator('#recaptcha-anchor').click()
            time.sleep(5)

            # 4. 图片挑战
            challenge_frame = next((f for f in page.frames if "api2/bframe" in f.url), None)
            if challenge_frame:
                for r in range(6):
                    if not challenge_frame.locator('.rc-imageselect-instructions').is_visible(timeout=2000):
                        break
                    print(f"--- 轮次 {r+1} ---")
                    solve_captcha(challenge_frame)
                    time.sleep(2)
            
            # 5. 等待按钮就绪
            print("[*] 正在检查按钮状态...")
            submit_btn = page.locator('#submit-button')
            
            # 如果 AI 识别失败，这里可能会超时
            page.wait_for_function(
                "document.querySelector('#submit-button').value.includes('Renew') && !document.querySelector('#submit-button').disabled", 
                timeout=30000
            )
            
            submit_btn.click()
            print("[+] 已点击 Renew，等待结果...")
            time.sleep(8)

            res_path = SAVE_DIR / "final_result.png"
            page.screenshot(path=str(res_path))
            
            content = page.content().lower()
            if "renewed" in content or "success" in content:
                send_telegram_photo(str(res_path), f"✅ {USERNAME} 续期成功！")
            else:
                send_telegram_photo(str(res_path), f"⚠️ {USERNAME} 操作完成，请看图确认结果")

        except Exception as e:
            print(f"[-] 异常报错: {e}")
            err_path = SAVE_DIR / "error.png"
            page.screenshot(path=str(err_path))
            send_telegram_photo(str(err_path), f"❌ {USERNAME} 报错: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_auto_renew()
