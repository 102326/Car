import time
import logging
import random
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


# --- 任务 1: 发送短信 (之前讨论的 P1 任务) ---

def _sync_send_sms_via_provider(phone: str, code: str) -> bool:
    """[模拟] 同步发送短信的底层函数"""
    logger.info(f"📡 [Network] 正向运营商网关发送请求: {phone}...")
    time.sleep(0.5)
    # 模拟 10% 的概率网络失败
    if random.random() < 0.1:
        logger.warning("💥 [Network] 模拟网络抖动失败！")
        raise ConnectionError("模拟的运营商连接超时")
    print(f"📨 [SMS] 验证码 {code} 已发送至 {phone}")
    return True


@celery_app.task(name="auth.send_sms_code")
def send_sms_code_task(phone: str, code: str):
    """P1 级任务：发送验证码"""
    logger.info(f"▶️ [Celery] 开始处理短信任务: {phone}")
    try:
        success = _sync_send_sms_via_provider(phone, code)
        if success:
            logger.info(f"✅ [Celery] 任务完成: {phone}")
            return {"status": "sent", "phone": phone}
    except Exception as e:
        logger.error(f"❌ [Celery] 发生异常 (准备自动重试): {e}")
        raise e


# --- 任务 2: 登录通知 (你的 auth.py 需要导入这个) ---

@celery_app.task(name="auth.send_login_notification")
def send_login_notification(user_id: int, login_type: str, ip: str):
    """P2 级任务：发送登录通知"""
    logger.info(f"📧 [Email Worker] 正在给用户 {user_id} 发送登录通知...")
    # 模拟耗时
    time.sleep(0.5)
    print(f"   └─ 登录方式: {login_type}, IP来源: {ip}")
    print("   ✅ 邮件发送成功")
    return f"Notification sent to {user_id}"


# --- 任务 3: 风控分析 (你的 auth.py 需要导入这个) ---

@celery_app.task(name="auth.analyze_login_risk")
def analyze_login_risk(user_id: int, ip: str):
    """P1 级任务：风控安全分析"""
    logger.info(f"🛡️ [Risk Worker] 正在分析用户 {user_id} 的登录环境...")

    # 模拟简单的风控逻辑
    if ip in ["127.0.0.1", "localhost", "::1"]:
        risk_level = "LOW"
    else:
        risk_level = "MEDIUM"

    print(f"   └─ 登录IP: {ip}, 风险等级: {risk_level}")

    if risk_level == "HIGH":
        print("   ⚠️ 警告：检测到异地登录，建议冻结账户！")

    return {"risk": risk_level}