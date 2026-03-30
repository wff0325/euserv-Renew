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

# 解决控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 从系统环境变量获取配置 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# 这里的模型名确保在 GitHub Secrets 里填的是 gemini-1.5-flash (目前最稳的)
# 如果你填的是 gemini-2.5-flash 且接口报错，说明 Google 还没在 v1 接口放出这个模型
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
RENEW_URL = os.getenv("RENEW_URL")
USERNAME = os.getenv("MC_USERNAME")
TELEGRAM_API = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# 截图保存到当前目录下的 screenshots 文件夹
SAVE_DIR = Path("./screenshots")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_API}/sendPhoto"
        with open(photo_path, "rb") as photo:
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files={"photo": photo}, timeout=30)
    except:
        pass

def get_gemini_indices(image_base64, task_text):
    """严格使用 v1 接口进行识别"""
    # 接口地址完全按照你的要求
    url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"Task: {task_text}. This is a 3x3 image grid. Indices 0-8 from top-left. Return ONLY a JSON list like [0, 2]. If none match, return []."
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": image_base64}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 100
        }
    }
    
    try:
        print(f"[*] 正在请求 Google API (Model: {GEMINI_MODEL})...")
        response = requests.post(url, json=payload, timeout=30)
        res_json = response.json()
        
        # --- 调试核心：如果报错，打印完整响应 ---
        if 'candidates' not in res_json:
            print(f"[-] API 异常响应: {json.dumps(res_json, indent=2)}")
            # 如果提示 model not found，说明你的 GEMINI_MODEL 变量填错了
            return []

        content = res_json['candidates'][0]['content']['parts'][0]['text']
        print(f"[*] AI 识别结果: {content.strip()}")
        
        # 提取数组中的数字
        indices = [int(n) for n in re.findall(r'\d+', content)]
        return indices
    except Exception as e:
        print(f"[-] 请求发生错误: {e}")
        return []

def solve_captcha(frame):
    try:
        instr = frame.locator('.rc-imageselect-instructions')
        if not instr.is_visible(timeout=3000): return False
        
        task_text = instr.inner_text().replace('\n', ' ').strip()
        print(f"[*] 识别任务: {task_text}")
        
        # 截取九宫格
        payload_box = frame.locator('.rc-imageselect-payload')
        img_b64 = base64.b64encode(payload_box.screenshot()).decode('utf-8')
        
        indices = get_gemini_indices(img_b64, task_text)
        print(f"[*] AI 建议点击索引: {indices}")
        
        tiles = frame.locator('.rc-imageselect-tile')
        for idx in indices:
            if idx < tiles.count():
                tiles.nth(idx).click()
                time.sleep(0.5)
        
        # 点击验证
        frame.locator('#recaptcha-verify-button').click()
        time.sleep(3)
        return True
    except Exception as e:
        print(f"[-] 验证挑战执行失败: {e}")
        return False

def run_auto_renew():
    print(f"🚀 开始执行续期任务 | 用户: {USERNAME}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        try:
            page.goto(RENEW_URL, timeout=60000)
            time.sleep(5)

            # 冷却检测
            cooldown = page.locator('text=/can be renewed in/i')
            if cooldown.is_visible():
                print(f"⚠️ 冷却中: {cooldown.inner_text()}")
                return

            # 填写用户名
            page.locator('input[name="username"]').fill(USERNAME)
            time.sleep(1)

            # 触发验证
            print("[*] 正在触发 reCAPTCHA...")
            anchor_frame = page.frame_locator('iframe[title*="reCAPTCHA"][src*="anchor"]')
            anchor_frame.locator('#recaptcha-anchor').click()
            time.sleep(5)

            # 图片挑战
            challenge_frame = None
            for f in page.frames:
                if "api2/bframe" in f.url:
                    challenge_frame = f
                    break
            
            if challenge_frame:
                print("[*] 检测到图片验证，开始 AI 识别...")
                for r in range(6):
                    if not challenge_frame.locator('.rc-imageselect-instructions').is_visible(timeout=2000):
                        break
                    print(f"--- 轮次 {r+1} ---")
                    solve_captcha(challenge_frame)
                    time.sleep(2)

            # 续费按钮
            submit_btn = page.locator('#submit-button')
            # 增加超时容忍
            page.wait_for_function(
                "document.querySelector('#submit-button').value.includes('Renew') && !document.querySelector('#submit-button').disabled", 
                timeout=30000
            )
            
            submit_btn.click()
            print("[+] 已点击 Renew 按钮")
            time.sleep(8)

            # 结果截图
            res_path = SAVE_DIR / "final_result.png"
            page.screenshot(path=str(res_path))
            
            content = page.content().lower()
            if "renewed" in content or "success" in content:
                print("✅ 续期成功")
                send_telegram_photo(str(res_path), f"✅ {USERNAME} 续期成功！")
            else:
                print("⚠️ 结果不明确")
                send_telegram_photo(str(res_path), f"⚠️ {USERNAME} 操作完成，请看图确认")

        except Exception as e:
            print(f"[-] 运行报错: {e}")
            err_path = SAVE_DIR / "error.png"
            page.screenshot(path=str(err_path))
            send_telegram_photo(str(err_path), f"❌ {USERNAME} 报错: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_auto_renew()
