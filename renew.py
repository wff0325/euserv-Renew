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

# 强制设置 UTF-8 编码，防止 GitHub 日志乱码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 从系统环境变量获取配置 (在 GitHub Secrets 中设置) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# 如果变量里没填，默认使用你指定的 gemini-2.5-flash
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
RENEW_URL = os.getenv("RENEW_URL")
USERNAME = os.getenv("MC_USERNAME")
TELEGRAM_API = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

# 截图保存目录
SAVE_DIR = Path("./screenshots")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

def send_telegram_photo(photo_path, caption):
    """通过 Telegram Bot 推送带图片的通知"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_API}/sendPhoto"
        with open(photo_path, "rb") as photo:
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files={"photo": photo}, timeout=30)
    except Exception as e:
        print(f"[!] Telegram 发送失败: {e}")

def get_gemini_indices(image_base64, task_text):
    """调用 Gemini AI 视觉识别验证码九宫格"""
    # 动态拼接模型名称
    url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
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
        content = res_json['candidates'][0]['content']['parts'][0]['text']
        print(f"[*] AI ({GEMINI_MODEL}) 回复: {content.strip()}")
        # 提取数组中的数字
        return [int(n) for n in re.findall(r'\d+', content)]
    except Exception as e:
        print(f"[-] AI 识别异常: {e}")
        return []

def solve_captcha(challenge_frame):
    """处理图片验证码流程"""
    try:
        instr = challenge_frame.locator('.rc-imageselect-instructions')
        if not instr.is_visible(timeout=3000): return False
        
        task_text = instr.inner_text().replace('\n', ' ').strip()
        print(f"[*] 当前任务: {task_text}")
        
        # 截取验证码图片区域
        payload_box = challenge_frame.locator('.rc-imageselect-payload')
        img_b64 = base64.b64encode(payload_box.screenshot()).decode('utf-8')
        
        indices = get_gemini_indices(img_b64, task_text)
        print(f"[*] AI 选择点击索引: {indices}")
        
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
    print(f"🚀 启动自动化续期任务 | 模式: 每小时运行 | 模型: {GEMINI_MODEL}")
    with sync_playwright() as p:
        # GitHub 环境必须开启 headless=True
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        try:
            print(f"[*] 访问目标: {RENEW_URL}")
            page.goto(RENEW_URL, timeout=60000)
            time.sleep(5)

            # 1. 冷却时间检测 (是否已经到了可以续期的时候)
            cooldown = page.locator('text=/can be renewed in/i')
            if cooldown.is_visible():
                msg = cooldown.inner_text()
                print(f"⚠️ 尚未到期: {msg}")
                path = SAVE_DIR / "cooldown.png"
                page.screenshot(path=str(path))
                send_telegram_photo(str(path), f"⚠️ {USERNAME} 尚未到续期时间\n状态: {msg}")
                return

            # 2. 填写用户名
            page.locator('input[name="username"]').fill(USERNAME)
            time.sleep(1)

            # 3. 触发验证码
            print("[*] 正在触发 reCAPTCHA...")
            anchor_frame = page.frame_locator('iframe[title*="reCAPTCHA"][src*="anchor"]')
            anchor_frame.locator('#recaptcha-anchor').click()
            time.sleep(5)

            # 4. 图片挑战处理 (bframe)
            challenge_frame = next((f for f in page.frames if "api2/bframe" in f.url), None)
            if challenge_frame:
                print("[*] 检测到图片验证码，开始 AI 破解...")
                for r in range(6): # 最多尝试 6 轮
                    if not challenge_frame.locator('.rc-imageselect-instructions').is_visible(timeout=2000):
                        print("[+] 挑战框已消失")
                        break
                    print(f"--- 轮次 {r+1} ---")
                    solve_captcha(challenge_frame)
                    time.sleep(2)
            
            # 5. 点击 Renew 按钮
            print("[*] 正在检查按钮状态...")
            submit_btn = page.locator('#submit-button')
            # 这里的 JS 脚本确保按钮可点击且文字正确
            page.wait_for_function(
                "document.querySelector('#submit-button').value.includes('Renew') && !document.querySelector('#submit-button').disabled", 
                timeout=30000
            )
            
            submit_btn.click()
            print("[+] 已点击 Renew，等待结果加载...")
            time.sleep(8)

            # 6. 最终结果确认与截图
            res_path = SAVE_DIR / "final_result.png"
            page.screenshot(path=str(res_path))
            
            content = page.content().lower()
            if "renewed" in content or "success" in content:
                print("✅ 确认续期成功！")
                send_telegram_photo(str(res_path), f"✅ {USERNAME} 续期成功！\n请查看截图。")
            else:
                print("⚠️ 操作已完成，但结果不明确，请人工确认")
                send_telegram_photo(str(res_path), f"⚠️ {USERNAME} 续期操作已完成，结果不明确")

        except Exception as e:
            print(f"[-] 异常报错: {e}")
            err_path = SAVE_DIR / "error.png"
            page.screenshot(path=str(err_path))
            send_telegram_photo(str(err_path), f"❌ {USERNAME} 续期运行报错: {str(e)[:100]}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_auto_renew()
