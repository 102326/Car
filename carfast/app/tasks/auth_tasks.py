# app/tasks/auth_tasks.py
import asyncio
from app.core.celery_app import celery_app
from datetime import datetime


# 模拟发送通知 (邮件/短信)
@celery_app.task(name="tasks.send_login_notification")
def send_login_notification(user_id: int, login_type: str, ip: str):
    """
    副作用1：发送登录通知 (P2级业务，允许延迟)
    """
    # 模拟耗时操作 (比如调第三方短信接口)
    # time.sleep(1)
    print(f"📧 [Email Worker] 正在给用户 {user_id} 发送登录通知...")
    print(f"   └─ 登录方式: {login_type}, IP来源: {ip}, 时间: {datetime.now()}")
    print("   ✅ 邮件发送成功")
    return f"Notification sent to {user_id}"


# 模拟风控分析
@celery_app.task(name="tasks.analyze_login_risk")
def analyze_login_risk(user_id: int, ip: str):
    """
    副作用2：风控安全分析 (P1级业务，失败需记录)
    """
    print(f"🛡️ [Risk Worker] 正在分析用户 {user_id} 的登录环境...")

    # 模拟逻辑：如果 IP 是内网 IP，视为安全
    if ip in ["127.0.0.1", "localhost", "::1"]:
        risk_level = "LOW"
    else:
        risk_level = "MEDIUM"

    print(f"   └─ 登录IP: {ip}, 风险等级: {risk_level}")

    if risk_level == "HIGH":
        print("   ⚠️ 警告：检测到异地登录，已冻结账户！")
        # 可以在这里调用数据库把 user.status 改为 0

    return {"risk": risk_level}