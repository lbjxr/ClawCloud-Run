#!/usr/bin/env python3
"""
ClawCloud 自动登录脚本
- 等待设备验证批准（30秒）
- 每次登录后自动更新 Cookie
- Telegram 通知
"""

import os
import sys
import time
import base64
import re
import requests
from playwright.sync_api import sync_playwright

# ==================== 配置 ====================
CLAW_CLOUD_URL = "https://ap-northeast-1.run.claw.cloud"
SIGNIN_URL = f"{CLAW_CLOUD_URL}/signin"
DEVICE_VERIFY_WAIT = 30  # Mobile验证 默认等 30 秒
TWO_FACTOR_WAIT = int(os.environ.get("TWO_FACTOR_WAIT", "120"))  # 2FA验证 默认等 120 秒


class Telegram:
    """Telegram 通知"""
    
    def __init__(self):
        self.token = os.environ.get('TG_BOT_TOKEN')
        self.chat_id = os.environ.get('TG_CHAT_ID')
        self.ok = bool(self.token and self.chat_id)
    
    def send(self, msg):
        if not self.ok:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                data={"chat_id": self.chat_id, "text": msg, "parse_mode": "HTML"},
                timeout=30
            )
        except:
            pass
    
    def photo(self, path, caption=""):
        if not self.ok or not os.path.exists(path):
            return
        try:
            with open(path, 'rb') as f:
                requests.post(
                    f"https://api.telegram.org/bot{self.token}/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": caption[:1024]},
                    files={"photo": f},
                    timeout=60
                )
        except:
            pass
    
    def flush_updates(self):
        """刷新 offset 到最新，避免读到旧消息"""
        if not self.ok:
            return 0
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{self.token}/getUpdates",
                params={"timeout": 0},
                timeout=10
            )
            data = r.json()
            if data.get("ok") and data.get("result"):
                return data["result"][-1]["update_id"] + 1
        except:
            pass
        return 0
    
    def wait_code(self, timeout=120):
        """
        等待你在 TG 里发 /code 123456
        只接受来自 TG_CHAT_ID 的消息
        """
        if not self.ok:
            return None
        
        # 先刷新 offset，避免读到旧的 /code
        offset = self.flush_updates()
        deadline = time.time() + timeout
        pattern = re.compile(r"^/code\s+(\d{6,8})$")  # 6位TOTP 或 8位恢复码也行
        
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{self.token}/getUpdates",
                    params={"timeout": 20, "offset": offset},
                    timeout=30
                )
                data = r.json()
                if not data.get("ok"):
                    time.sleep(2)
                    continue
                
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    msg = upd.get("message") or {}
                    chat = msg.get("chat") or {}
                    if str(chat.get("id")) != str(self.chat_id):
                        continue
                    
                    text = (msg.get("text") or "").strip()
                    m = pattern.match(text)
                    if m:
                        return m.group(1)
            
            except Exception:
                pass
            
            time.sleep(2)
        
        return None


class SecretUpdater:
    """GitHub Secret 更新器"""
    
    def __init__(self):
        self.token = os.environ.get('REPO_TOKEN')
        self.repo = os.environ.get('GITHUB_REPOSITORY')
        self.ok = bool(self.token and self.repo)
        if self.ok:
            print("✅ Secret 自动更新已启用")
        else:
            print("⚠️ Secret 自动更新未启用（需要 REPO_TOKEN）")
    
    def update(self, name, value):
        if not self.ok:
            return False
        try:
            from nacl import encoding, public
            
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 获取公钥
            r = requests.get(
                f"https://api.github.com/repos/{self.repo}/actions/secrets/public-key",
                headers=headers, timeout=30
            )
            if r.status_code != 200:
                return False
            
            key_data = r.json()
            pk = public.PublicKey(key_data['key'].encode(), encoding.Base64Encoder())
            encrypted = public.SealedBox(pk).encrypt(value.encode())
            
            # 更新 Secret
            r = requests.put(
                f"https://api.github.com/repos/{self.repo}/actions/secrets/{name}",
                headers=headers,
                json={"encrypted_value": base64.b64encode(encrypted).decode(), "key_id": key_data['key_id']},
                timeout=30
            )
            return r.status_code in [201, 204]
        except Exception as e:
            print(f"更新 Secret 失败: {e}")
            return False


class AutoLogin:
    """自动登录"""
    
    def __init__(self):
        self.username = os.environ.get('GH_USERNAME')
        self.password = os.environ.get('GH_PASSWORD')
        self.gh_session = os.environ.get('GH_SESSION', '').strip()
        self.tg = Telegram()
        self.secret = SecretUpdater()
        self.shots = []
        self.logs = []
        self.n = 0
        
    def log(self, msg, level="INFO"):
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️", "STEP": "🔹"}
        line = f"{icons.get(level, '•')} {msg}"
        print(line)
        self.logs.append(line)
    
    def shot(self, page, name):
        self.n += 1
        f = f"{self.n:02d}_{name}.png"
        try:
            page.screenshot(path=f)
            self.shots.append(f)
        except:
            pass
        return f
    
    def click(self, page, sels, desc=""):
        for s in sels:
            try:
                el = page.locator(s).first
                if el.is_visible(timeout=3000):
                    el.click()
                    self.log(f"已点击: {desc}", "SUCCESS")
                    return True
            except:
                pass
        return False
    
    def get_session(self, context):
        """提取 Session Cookie"""
        try:
            for c in context.cookies():
                if c['name'] == 'user_session' and 'github' in c.get('domain', ''):
                    return c['value']
        except:
            pass
        return None
    
    def save_cookie(self, value):
        """保存新 Cookie"""
        if not value:
            return
        
        self.log(f"新 Cookie: {value[:15]}...{value[-8:]}", "SUCCESS")
        
        # 自动更新 Secret
        if self.secret.update('GH_SESSION', value):
            self.log("已自动更新 GH_SESSION", "SUCCESS")
            self.tg.send("🔑 <b>Cookie 已自动更新</b>\n\nGH_SESSION 已保存")
        else:
            # 通过 Telegram 发送
            self.tg.send(f"""🔑 <b>新 Cookie</b>

请更新 Secret <b>GH_SESSION</b>:
<code>{value}</code>""")
            self.log("已通过 Telegram 发送 Cookie", "SUCCESS")
    
    def wait_device(self, page):
        """等待设备验证"""
        self.log(f"需要设备验证，等待 {DEVICE_VERIFY_WAIT} 秒...", "WARN")
        self.shot(page, "设备验证")
        
        self.tg.send(f"""⚠️ <b>需要设备验证</b>

请在 {DEVICE_VERIFY_WAIT} 秒内批准：
1️⃣ 检查邮箱点击链接
2️⃣ 或在 GitHub App 批准""")
        
        if self.shots:
            self.tg.photo(self.shots[-1], "设备验证页面")
        
        for i in range(DEVICE_VERIFY_WAIT):
            time.sleep(1)
            if i % 5 == 0:
                self.log(f"  等待... ({i}/{DEVICE_VERIFY_WAIT}秒)")
                url = page.url
                if 'verified-device' not in url and 'device-verification' not in url:
                    self.log("设备验证通过！", "SUCCESS")
                    self.tg.send("✅ <b>设备验证通过</b>")
                    return True
                try:
                    page.reload(timeout=10000)
                    page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    pass
        
        if 'verified-device' not in page.url:
            return True
        
        self.log("设备验证超时", "ERROR")
        self.tg.send("❌ <b>设备验证超时</b>")
        return False
    
    def wait_two_factor_mobile(self, page):
        """等待 GitHub Mobile 两步验证批准，并把数字截图提前发到电报"""
        self.log(f"需要两步验证（GitHub Mobile），等待 {TWO_FACTOR_WAIT} 秒...", "WARN")
        
        # 先截图并立刻发出去（让你看到数字）
        shot = self.shot(page, "两步验证_mobile")
        self.tg.send(f"""⚠️ <b>需要两步验证（GitHub Mobile）</b>

请打开手机 GitHub App 批准本次登录（会让你确认一个数字）。
等待时间：{TWO_FACTOR_WAIT} 秒""")
        if shot:
            self.tg.photo(shot, "两步验证页面（数字在图里）")
        
        # 不要频繁 reload，避免把流程刷回登录页
        for i in range(TWO_FACTOR_WAIT):
            time.sleep(1)
            
            url = page.url
            
            # 如果离开 two-factor 流程页面，认为通过
            if "github.com/sessions/two-factor/" not in url:
                self.log("两步验证通过！", "SUCCESS")
                self.tg.send("✅ <b>两步验证通过</b>")
                return True
            
            # 如果被刷回登录页，说明这次流程断了（不要硬等）
            if "github.com/login" in url:
                self.log("两步验证后回到了登录页，需重新登录", "ERROR")
                return False
            
            # 每 10 秒打印一次，并补发一次截图（防止你没看到数字）
            if i % 10 == 0 and i != 0:
                self.log(f"  等待... ({i}/{TWO_FACTOR_WAIT}秒)")
                shot = self.shot(page, f"两步验证_{i}s")
                if shot:
                    self.tg.photo(shot, f"两步验证页面（第{i}秒）")
            
            # 只在 30 秒、60 秒... 做一次轻刷新（可选，频率很低）
            if i % 30 == 0 and i != 0:
                try:
                    page.reload(timeout=30000)
                    page.wait_for_load_state('domcontentloaded', timeout=30000)
                except:
                    pass
        
        self.log("两步验证超时", "ERROR")
        self.tg.send("❌ <b>两步验证超时</b>")
        return False
    
    def handle_2fa_code_input(self, page):
        """处理 TOTP 验证码输入 (针对 Passkey 优先界面优化)"""
        self.log("检测到两步验证界面", "WARN")
        code = None  # 初始化 code，防止 NameError
        time.sleep(2)
        self.shot(page, "2FA_1_初始页面")

        # 1. 尝试展开 "More options"
        try:
            # 这里的 selector 兼容 summary 标签或普通的 More options 文字
            more_options = page.locator('summary:has-text("More options"), button:has-text("More options"), .Button-label:has-text("More options")').first
            if more_options.is_visible(timeout=3000):
                more_options.click()
                self.log("已展开 More options 菜单", "INFO")
                time.sleep(1.5)
        except:
            self.log("More options 可能已经展开或不存在", "INFO")

        # 2. 点击 "Authenticator app" 链接 (根据你提供的 HTML 精确匹配)
        try:
            # 优先使用你提供的那个 unique selector
            auth_link = page.locator('a[data-test-selector="totp-app-link"]').first
            if auth_link.is_visible(timeout=3000):
                auth_link.click()
                self.log("✅ 已点击 Authenticator app 切换链接", "SUCCESS")
                time.sleep(2)
            else:
                # 备选方案：通过文字匹配
                auth_link_alt = page.locator('a:has-text("Authenticator app")').first
                if auth_link_alt.is_visible(timeout=2000):
                    auth_link_alt.click()
                    self.log("✅ 已点击 Authenticator app (文字匹配)", "SUCCESS")
                    time.sleep(2)
        except Exception as e:
            self.log(f"切换验证模式失败: {e}", "ERROR")

        # 3. 检查输入框是否出现，并请求验证码
        input_selector = 'input#app_totp, input[name="app_otp"]'
        try:
            page.wait_for_selector(input_selector, timeout=5000)
            self.log("验证码输入框已就绪", "SUCCESS")
        except:
            self.log("尚未检测到输入框，可能还在加载", "WARN")

        # 截图并通知 TG
        shot = self.shot(page, "2FA_即将输入验证码")
        self.tg.send("🔐 <b>GitHub 验证码模式已开启</b>\n请发送：<code>/code 123456</code>")
        if shot:
            self.tg.photo(shot)

        # 4. 等待用户从 TG 发送验证码
        self.log(f"等待用户发送验证码 (限时 {TWO_FACTOR_WAIT} 秒)...", "WARN")
        code = self.tg.wait_code(timeout=TWO_FACTOR_WAIT)

        if not code:
            self.log("❌ 超时未收到验证码", "ERROR")
            return False

        # 5. 填入验证码并处理跳转
        try:
            self.log(f"正在填入验证码: {code}", "INFO")
            
            # 使用 type 模拟一位一位输入，触发 GitHub 的自动提交
            page.fill(input_selector, code)
            
            # --- 核心改进：等待页面跳转而不是死等点击 ---
            self.log("验证码已填入，等待页面跳转...", "INFO")
            
            try:
                # 等待 URL 发生变化（离开 github.com）
                # timeout 设短一点，因为自动提交通常很快
                page.wait_for_url(lambda url: "github.com/sessions/two-factor" not in url, timeout=10000)
                self.log("检测到页面已自动跳转，验证成功", "SUCCESS")
                return True
            except:
                # 如果 10 秒内没跳转，尝试手动点击提交按钮
                self.log("页面未自动跳转，尝试手动点击 Verify 按钮", "WARN")
                submit_btn = page.locator('button:has-text("Verify"), button[type="submit"]').first
                if submit_btn.is_visible():
                    submit_btn.click()
                    # 再次等待最终跳转
                    time.sleep(5)
            
            # 最终检查
            if "github.com" not in page.url or "two-factor" not in page.url:
                self.log("两步验证最终确认通过", "SUCCESS")
                return True
            else:
                self.log(f"验证似乎未通过，当前 URL: {page.url}", "ERROR")
                return False

        except Exception as e:
            # 如果是因为页面跳转导致的异常，其实不算错误
            if "navigation" in str(e).lower() or "detached" in str(e).lower():
                self.log("提交过程中页面发生跳转 (正常现象)", "SUCCESS")
                return True
            self.log(f"填充验证码过程出错: {e}", "ERROR")
            return False

    
    def login_github(self, page, context):
        """登录 GitHub"""
        self.log("登录 GitHub...", "STEP")
        self.shot(page, "github_登录页")
        
        try:
            page.locator('input[name="login"]').fill(self.username)
            page.locator('input[name="password"]').fill(self.password)
            self.log("已输入凭据")
        except Exception as e:
            self.log(f"输入失败: {e}", "ERROR")
            return False
        
        self.shot(page, "github_已填写")
        
        try:
            page.locator('input[type="submit"], button[type="submit"]').first.click()
        except:
            pass
        
        time.sleep(3)
        page.wait_for_load_state('networkidle', timeout=30000)
        self.shot(page, "github_登录后")
        
        url = page.url
        self.log(f"当前: {url}")
        
        # 设备验证
        if 'verified-device' in url or 'device-verification' in url:
            if not self.wait_device(page):
                return False
            time.sleep(2)
            page.wait_for_load_state('networkidle', timeout=30000)
            self.shot(page, "验证后")
        
        # 2FA
        if 'two-factor' in page.url:
            self.log("需要两步验证！", "WARN")
            self.shot(page, "两步验证")
            
            # GitHub Mobile：等待你在手机上批准
            if 'two-factor/mobile' in page.url:
                if not self.wait_two_factor_mobile(page):
                    return False
                # 通过后等页面稳定
                try:
                    page.wait_for_load_state('networkidle', timeout=30000)
                    time.sleep(2)
                except:
                    pass
            
            else:
                # 其它两步验证方式（TOTP/恢复码等），尝试通过 Telegram 输入验证码
                if not self.handle_2fa_code_input(page):
                    return False
                # 通过后等页面稳定
                try:
                    page.wait_for_load_state('networkidle', timeout=30000)
                    time.sleep(2)
                except:
                    pass
        
        # 错误
        try:
            err = page.locator('.flash-error').first
            if err.is_visible(timeout=2000):
                self.log(f"错误: {err.inner_text()}", "ERROR")
                return False
        except:
            pass
        
        return True
    
    def oauth(self, page):
        """处理 OAuth"""
        if 'github.com/login/oauth/authorize' in page.url:
            self.log("处理 OAuth...", "STEP")
            self.shot(page, "oauth")
            self.click(page, ['button[name="authorize"]', 'button:has-text("Authorize")'], "授权")
            time.sleep(3)
            page.wait_for_load_state('networkidle', timeout=30000)
    
    def wait_redirect(self, page, wait=60):
        """等待重定向"""
        self.log("等待重定向...", "STEP")
        for i in range(wait):
            url = page.url
            if 'claw.cloud' in url and 'signin' not in url.lower():
                self.log("重定向成功！", "SUCCESS")
                return True
            if 'github.com/login/oauth/authorize' in url:
                self.oauth(page)
            time.sleep(1)
            if i % 10 == 0:
                self.log(f"  等待... ({i}秒)")
        self.log("重定向超时", "ERROR")
        return False
    
    def keepalive(self, page):
        """保活"""
        self.log("保活...", "STEP")
        for url, name in [(f"{CLAW_CLOUD_URL}/", "控制台"), (f"{CLAW_CLOUD_URL}/apps", "应用")]:
            try:
                page.goto(url, timeout=30000)
                page.wait_for_load_state('networkidle', timeout=15000)
                self.log(f"已访问: {name}", "SUCCESS")
                time.sleep(2)
            except:
                pass
        self.shot(page, "完成")
    
    def notify(self, ok, err=""):
        if not self.tg.ok:
            return
        
        msg = f"""<b>🤖 ClawCloud 自动登录</b>

<b>状态:</b> {"✅ 成功" if ok else "❌ 失败"}
<b>用户:</b> {self.username}
<b>时间:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}"""
        
        if err:
            msg += f"\n<b>错误:</b> {err}"
        
        msg += "\n\n<b>日志:</b>\n" + "\n".join(self.logs[-6:])
        
        self.tg.send(msg)
        
        if self.shots:
            if not ok:
                for s in self.shots[-3:]:
                    self.tg.photo(s, s)
            else:
                self.tg.photo(self.shots[-1], "完成")
    
    def is_session_valid(self, page):
        """校验当前 Session 是否仍然有效"""
        try:
            self.log("正在校验 Cookie 有效性...", "INFO")
            # 访问一个必须登录后才能看到的页面
            page.goto("https://run.claw.cloud/dashboard", wait_until="networkidle", timeout=15000)
            
            # 逻辑判定：
            # 1. 检查 URL 是否包含 login 关键字
            if "login" in page.url.lower():
                return False
            
            # 2. 检查页面是否包含特定的登录后元素（比如“退出”按钮或“控制台”字样）
            # 根据你观察到的 Claw 界面修改这个选择器
            logout_btn = page.locator('text="Logout", :has-text("Sign Out")').first
            if logout_btn.is_visible(timeout=5000):
                return True
            
            # 3. 兜底判定
            if "dashboard" in page.url:
                return True
                
            return False
        except Exception as e:
            self.log(f"校验过程出错，默认判定为失效: {e}", "WARN")
            return False

    def clear_cookies(self):
        """物理删除保存的 Cookie 文件"""
        cookie_path = "state.json"  # 确保这个路径和你保存 context 的路径一致
        if os.path.exists(cookie_path):
            try:
                os.remove(cookie_path)
                self.log(f"✅ 已删除失效的 Cookie 文件: {cookie_path}", "SUCCESS")
            except Exception as e:
                self.log(f"❌ 删除 Cookie 文件失败: {e}", "ERROR")


    def run(self):
        print("\n" + "="*50)
        print("🚀 ClawCloud 自动登录脚本")
        print("="*50 + "\n")
        
        # 定义全局统一的存储文件名
        STATE_FILE = "state.json"
        
        self.log(f"用户名: {self.username}")
        
        if not self.username or not self.password:
            self.log("缺少凭据", "ERROR")
            self.notify(False, "凭据未配置")
            sys.exit(1)
        
        with sync_playwright() as p:
            # --- 启动浏览器 ---
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            
            # 【关键改动 1】启动时如果文件存在，则加载 state.json
            storage_state = STATE_FILE if os.path.exists(STATE_FILE) else None
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                storage_state=storage_state  # 自动注入之前保存的所有 Cookie 和 LocalStorage
            )
            page = context.new_page()
            
            try:
                # --- 步骤 1: 校验 Session ---
                is_valid = False
                # 如果 state.json 存在，先尝试访问后台
                if os.path.exists(STATE_FILE):
                    self.log("步骤1: 检测到 state.json，尝试快速核验...", "STEP")
                    try:
                        # 访问一个必须登录后才有权查看的 URL
                        page.goto("https://run.claw.cloud/dashboard", timeout=30000)
                        page.wait_for_load_state('networkidle')
                        
                        if 'signin' not in page.url.lower() and 'dashboard' in page.url.lower():
                            self.log("✅ Cookie 仍然有效，跳过登录流程", "SUCCESS")
                            is_valid = True
                        else:
                            self.log("⚠️ Cookie 已失效，准备清理并重新登录", "WARN")
                            self.clear_cookies() # 调用你之前写的清理函数，删除旧的 state.json
                    except Exception as e:
                        self.log(f"快速校验失败: {e}", "WARN")

                # --- 步骤 2: 执行登录流程 (如果 Session 无效) ---
                if not is_valid:
                    self.log("步骤2: 开始新鲜登录流程...", "STEP")
                    page.goto(SIGNIN_URL, timeout=60000)
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    if 'signin' not in page.url.lower():
                        self.log("检测到已是登录状态", "SUCCESS")
                    else:
                        self.log("点击 GitHub 登录按钮...", "INFO")
                        page.wait_for_selector('button:has-text("GitHub")', timeout=10000)
                        if not self.click(page, ['button:has-text("GitHub")', 'a:has-text("GitHub")'], "GitHub"):
                            self.log("找不到 GitHub 按钮", "ERROR")
                            sys.exit(1)
                        
                        time.sleep(3)
                        if 'github.com/login' in page.url or 'github.com/session' in page.url:
                            if not self.login_github(page, context):
                                self.notify(False, "GitHub 登录失败")
                                sys.exit(1)
                        elif 'github.com/login/oauth/authorize' in page.url:
                            self.oauth(page)

                    # 等待重定向回主站
                    if not self.wait_redirect(page):
                        sys.exit(1)

                # --- 步骤 3: 最终验证与【保存状态】 ---
                self.log("步骤3: 最终验证与保活", "STEP")
                if 'claw.cloud' not in page.url or 'signin' in page.url.lower():
                    self.log("页面验证失败", "ERROR")
                    sys.exit(1)
                
                self.keepalive(page) 
                
                # 【关键改动 2】任务成功后，提取当前所有 Cookie/Session 存入 state.json
                self.log("步骤4: 正在持久化最新的登录状态到 state.json", "STEP")
                context.storage_state(path=STATE_FILE)
                self.log("✅ 状态保存成功", "SUCCESS")

                # 兼容你原来的 save_cookie 函数（可选）
                new_s = self.get_session(context)
                if new_s: self.save_cookie(new_s)
                
                self.notify(True)
                print("\n✅ 执行成功！\n")
                
            except Exception as e:
                self.log(f"运行异常: {e}", "ERROR")
                self.shot(page, "exception")
                self.notify(False, str(e))
                sys.exit(1)
            finally:
                browser.close()




if __name__ == "__main__":
    AutoLogin().run()
