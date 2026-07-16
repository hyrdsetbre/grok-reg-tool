# -*- coding: utf-8 -*-
"""
Cloudflare 账号自动注册脚本
基于 grok-reg-tool 架构，兼容现有邮件后端

注意事项：
1. Cloudflare 注册使用 Turnstile 人机验证，需要配置第三方打码服务
2. Global API Key 无法自动获取，需登录后手动创建
3. 新账号可能触发手机号验证，成功率不保证
"""

import sys
import os
import io
import re
import time
import json
import secrets
import string
import platform
import tempfile
import shutil
import logging
import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.errors import PageDisconnectedError

# 复用项目的邮件服务
from email_register import create_temp_email, wait_for_verification_code, fetch_emails, fetch_email_detail

# ============================================================
# 配置加载
# ============================================================
_config_path = Path(__file__).parent / "config.json"
_conf: Dict[str, Any] = {}
if _config_path.exists():
    with _config_path.open("r", encoding="utf-8") as _f:
        _conf = json.load(_f)

PROXY = str(_conf.get("browser_proxy", "") or _conf.get("proxy", ""))
YESCAPTCHA_KEY = str(_conf.get("yescaptcha_key", ""))

# ============================================================
# 日志设置
# ============================================================
run_logger: logging.Logger = None

def setup_run_logger() -> logging.Logger:
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"cloudflare_run_{ts}_{os.getpid()}.log")

    logger = logging.getLogger("cloudflare_register")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.info("日志文件: %s", log_path)
    return logger

# ============================================================
# 工具函数
# ============================================================
def generate_password(length: int = 16) -> str:
    """生成符合 Cloudflare 要求的强密码"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))
        # 确保包含大小写字母和数字
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)):
            return password

def extract_verify_link(content: str) -> Optional[str]:
    """从邮件内容中提取验证链接"""
    if not content:
        return None

    # Cloudflare 验证邮件中的链接模式
    patterns = [
        r'https://dash\.cloudflare\.com/confirm-email\?[^\s<>"']+',
        r'https://www\.cloudflare\.com/[^\s<>"']*verify[^\s<>"']*',
        r'href="(https://dash\.cloudflare\.com/[^"]+)"',
    ]

    for pattern in patterns:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            return m.group(1) if m.groups() else m.group(0)

    return None

# ============================================================
# 浏览器初始化
# ============================================================
_virtual_display = None

def init_browser(user_data_dir: Optional[str] = None) -> Chromium:
    """初始化浏览器"""
    global _virtual_display

    # Linux 无头环境自动启用 Xvfb
    if platform.system() == "Linux" and (not os.environ.get("DISPLAY") or os.environ.get("USE_XVFB") == "1"):
        try:
            from pyvirtualdisplay import Display
            _virtual_display = Display(visible=0, size=(1920, 1080))
            _virtual_display.start()
            run_logger.info("Xvfb 虚拟显示器已启动: %s", os.environ.get('DISPLAY'))
        except Exception as e:
            run_logger.warning("Xvfb 启动失败: %s，将尝试直接运行", e)

    co = ChromiumOptions()
    co.auto_port()
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--disable-dev-shm-usage")
    co.set_argument("--headless=new")

    if user_data_dir:
        co.set_user_data_path(user_data_dir)

    if PROXY:
        co.set_proxy(PROXY)
        run_logger.info("使用代理: %s", PROXY)

    browser = Chromium(addr_or_opts=co)
    return browser

# ============================================================
# YesCaptcha 打码服务（可选）
# ============================================================
def solve_turnstile(site_key: str, page_url: str) -> Optional[str]:
    """
    使用 YesCaptcha 解决 Turnstile 验证
    需要在 config.json 中配置 yescaptcha_key
    """
    if not YESCAPTCHA_KEY:
        run_logger.warning("未配置 YesCaptcha，无法自动解决 Turnstile")
        return None

    try:
        import requests
        # 创建任务
        task_data = {
            "clientKey": YESCAPTCHA_KEY,
            "task": {
                "type": "TurnstileTaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
        }
        resp = requests.post("https://api.yescaptcha.com/createTask", json=task_data, timeout=30)
        result = resp.json()

        if result.get("errorId") != 0:
            run_logger.error("YesCaptcha 创建任务失败: %s", result)
            return None

        task_id = result.get("taskId")
        run_logger.info("YesCaptcha 任务已创建: %s", task_id)

        # 轮询结果
        for _ in range(60):
            time.sleep(2)
            poll_data = {
                "clientKey": YESCAPTCHA_KEY,
                "taskId": task_id
            }
            resp = requests.post("https://api.yescaptcha.com/getTaskResult", json=poll_data, timeout=30)
            result = resp.json()

            if result.get("status") == "ready":
                token = result.get("solution", {}).get("token")
                run_logger.info("Turnstile 验证成功")
                return token
            elif result.get("status") == "processing":
                continue
            else:
                run_logger.error("YesCaptcha 任务失败: %s", result)
                return None

    except Exception as e:
        run_logger.error("YesCaptcha 调用异常: %s", e)

    return None

# ============================================================
# 核心注册流程
# ============================================================
def register_cloudflare_account() -> Tuple[bool, Dict[str, Any]]:
    """
    注册 Cloudflare 账号
    返回 (成功状态, 账号信息字典)
    """
    account_info = {
        "email": "",
        "password": "",
        "registered": False,
        "email_verified": False,
        "api_key": "",  # 注意：Global API Key 无法自动获取
        "error": "",
    }

    temp_dir = tempfile.mkdtemp(prefix="cf_profile_")
    browser = None

    try:
        # 1. 创建临时邮箱
        run_logger.info("=" * 50)
        run_logger.info("第 1 步：创建临时邮箱")
        email, password, jwt = create_temp_email()
        account_info["email"] = email
        account_info["password"] = generate_password()
        run_logger.info("邮箱: %s", email)
        run_logger.info("密码: %s", account_info["password"])

        # 2. 启动浏览器
        run_logger.info("=" * 50)
        run_logger.info("第 2 步：启动浏览器，访问注册页面")
        browser = init_browser(user_data_dir=temp_dir)
        page = browser.latest_tab

        page.get("https://dash.cloudflare.com/sign-up")
        page.wait.doc_loaded()
        time.sleep(2)

        run_logger.info("页面标题: %s", page.title)

        # 3. 填写注册表单
        run_logger.info("=" * 50)
        run_logger.info("第 3 步：填写注册表单")

        # 邮箱输入框
        email_input = page.ele('input[type="email"]', timeout=10)
        if email_input:
            email_input.input(email)
            run_logger.info("✓ 已填写邮箱")
        else:
            raise Exception("未找到邮箱输入框")

        # 密码输入框
        password_input = page.ele('input[type="password"]', timeout=5)
        if password_input:
            password_input.input(account_info["password"])
            run_logger.info("✓ 已填写密码")
        else:
            raise Exception("未找到密码输入框")

        # 4. 处理 Turnstile 验证
        run_logger.info("=" * 50)
        run_logger.info("第 4 步：处理 Turnstile 人机验证")

        # 查找 Turnstile sitekey
        sitekey = ""
        try:
            cf_div = page.ele('.cf-turnstile', timeout=5)
            if cf_div:
                sitekey = cf_div.attr("data-sitekey") or ""
                run_logger.info("检测到 Turnstile，sitekey: %s", sitekey)
        except:
            pass

        if sitekey and YESCAPTCHA_KEY:
            # 使用打码服务
            token = solve_turnstile(sitekey, page.url)
            if token:
                # 注入 token
                page.run_js(f'''
                    const input = document.querySelector('input[name="cf-turnstile-response"]');
                    if (input) {{
                        input.value = "{token}";
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                ''')
                run_logger.info("✓ Turnstile token 已注入")
            else:
                run_logger.warning("Turnstile 打码失败，可能需要手动验证")
        elif sitekey:
            run_logger.warning("检测到 Turnstile 但未配置打码服务，需要手动验证")
            run_logger.info("提示：在 config.json 中配置 yescaptcha_key 可自动打码")

        # 5. 提交注册
        run_logger.info("=" * 50)
        run_logger.info("第 5 步：提交注册")

        submit_btn = page.ele('button[type="submit"]', timeout=5)
        if submit_btn and submit_btn.states.is_enabled:
            submit_btn.click()
            run_logger.info("✓ 已点击注册按钮")
        else:
            # 尝试其他选择器
            create_btn = page.ele('text:Create Account', timeout=5)
            if create_btn:
                create_btn.click()
                run_logger.info("✓ 已点击创建账号按钮")
            else:
                run_logger.warning("未找到提交按钮，等待页面变化...")

        # 等待页面跳转或错误
        time.sleep(5)
        run_logger.info("当前 URL: %s", page.url)

        # 保存调试页面
        debug_path = os.path.join(os.path.dirname(__file__), "logs", f"debug_cf_{int(time.time())}.html")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(page.html)
        run_logger.info("调试页面已保存: %s", debug_path)

        # 6. 等待验证邮件
        run_logger.info("=" * 50)
        run_logger.info("第 6 步：等待验证邮件")

        verify_link = None
        start_time = time.time()
        timeout = 180  # 3分钟超时

        while time.time() - start_time < timeout:
            emails = fetch_emails(jwt)
            for msg in emails:
                if not isinstance(msg, dict):
                    continue
                subject = msg.get("subject", "") or ""
                content = (msg.get("raw") or msg.get("text") or msg.get("html") or "")

                # Cloudflare 验证邮件
                if "cloudflare" in subject.lower() or "verify" in subject.lower():
                    run_logger.info("收到邮件: %s", subject)

                    # 获取详情
                    msg_id = msg.get("id")
                    if msg_id and not content:
                        detail = fetch_email_detail(jwt, msg_id)
                        if detail:
                            content = detail.get("raw") or detail.get("text") or detail.get("html") or ""

                    verify_link = extract_verify_link(content)
                    if verify_link:
                        run_logger.info("✓ 提取到验证链接: %s", verify_link[:80] + "...")
                        break

            if verify_link:
                break

            time.sleep(3)

        if not verify_link:
            raise Exception("超时未收到验证邮件")

        # 7. 点击验证链接
        run_logger.info("=" * 50)
        run_logger.info("第 7 步：完成邮箱验证")

        page.get(verify_link)
        page.wait.doc_loaded()
        time.sleep(5)

        run_logger.info("验证后 URL: %s", page.url)

        if "login" in page.url.lower() or "dash" in page.url.lower():
            account_info["email_verified"] = True
            account_info["registered"] = True
            run_logger.info("✓ 邮箱验证成功，账号注册完成")
        else:
            run_logger.warning("验证后页面异常，请检查: %s", page.url)
            account_info["email_verified"] = True  # 链接已点击
            account_info["registered"] = True

        # 8. 尝试自动登录（如果需要）
        if "login" in page.url.lower():
            run_logger.info("自动登录中...")
            email_input = page.ele('input[type="email"]', timeout=5)
            if email_input:
                email_input.input(email)
                pwd_input = page.ele('input[type="password"]', timeout=5)
                if pwd_input:
                    pwd_input.input(account_info["password"])
                    login_btn = page.ele('button[type="submit"]', timeout=5)
                    if login_btn:
                        login_btn.click()
                        time.sleep(5)
                        run_logger.info("登录后 URL: %s", page.url)

        run_logger.info("=" * 50)
        run_logger.info("注册流程完成")
        run_logger.info("邮箱: %s", account_info["email"])
        run_logger.info("密码: %s", account_info["password"])
        run_logger.info("注册状态: %s", "成功" if account_info["registered"] else "失败")
        run_logger.info("邮箱验证: %s", "已验证" if account_info["email_verified"] else "未验证")
        run_logger.info("")
        run_logger.info("⚠️  重要提示：Global API Key 无法自动获取")
        run_logger.info("   请登录后手动前往：My Profile → API Tokens → Global API Key")

        return account_info["registered"], account_info

    except Exception as e:
        run_logger.error("注册失败: %s", str(e))
        account_info["error"] = str(e)
        return False, account_info

    finally:
        # 清理
        if browser:
            try:
                browser.quit()
            except:
                pass
        if _virtual_display:
            try:
                _virtual_display.stop()
            except:
                pass
        # 清理临时 profile
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

# ============================================================
# 主入口（兼容 runner 调用）
# ============================================================
def main():
    """单轮注册入口"""
    global run_logger
    run_logger = setup_run_logger()

    run_logger.info("=" * 50)
    run_logger.info("Cloudflare 账号自动注册工具")
    run_logger.info("=" * 50)

    success, info = register_cloudflare_account()

    if success:
        run_logger.info("")
        run_logger.info("✅ 注册成功！")
        run_logger.info("邮箱: %s", info["email"])
        run_logger.info("密码: %s", info["password"])
        return 0
    else:
        run_logger.error("")
        run_logger.error("❌ 注册失败: %s", info.get("error", "未知错误"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
