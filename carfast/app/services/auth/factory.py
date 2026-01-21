# app/services/auth/factory.py
from app.services.auth.base import AuthStrategy
from app.services.auth.strategies.dingtalk import DingTalkStrategy
from app.services.auth.strategies.password import PasswordStrategy
from app.services.auth.strategies.sms import SmsStrategy

class AuthFactory:
    # 注册表
    _strategies = {
        "password": PasswordStrategy(),
        "sms": SmsStrategy(),
        "dingtalk": DingTalkStrategy(),
        # 后续还要加 "dingtalk": DingTalkStrategy()
    }

    @classmethod
    def get_strategy(cls, login_type: str) -> AuthStrategy:
        strategy = cls._strategies.get(login_type)
        if not strategy:
            raise ValueError(f"暂不支持该登录方式: {login_type}")
        return strategy