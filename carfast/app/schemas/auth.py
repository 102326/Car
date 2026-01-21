# app/schemas/auth.py
from pydantic import BaseModel, Field
from typing import Dict, Any, Literal

class LoginRequest(BaseModel):
    # 限制 login_type 只能是这几种，防止乱传
    login_type: Literal["password", "sms", "dingtalk"] = Field(
        ...,
        description="登录方式: password=密码, sms=短信, dingtalk=钉钉"
    )
    # payload 是一个字典，策略内部自己去解析（比如密码登录要 username，短信登录要 phone）
    payload: Dict[str, Any] = Field(
        ...,
        description="登录参数负载，例如 {'phone': '...', 'code': '...'}"
    )