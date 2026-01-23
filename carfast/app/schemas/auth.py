from pydantic import BaseModel, Field
from typing import Optional, Literal

# --- 登录请求参数 ---
class LoginParam(BaseModel):
    login_type: Literal["password", "sms", "dingtalk"] = Field(
        ..., 
        description="登录方式: password(密码), sms(短信), dingtalk(钉钉)"
    )
    # 策略模式通用参数
    # 如果是密码登录：需要 account, password
    # 如果是短信登录：需要 phone, code
    # 如果是钉钉登录：需要 code
    account: Optional[str] = Field(None, description="账号(手机/邮箱)")
    password: Optional[str] = Field(None, description="密码")
    phone: Optional[str] = Field(None, description="手机号")
    code: Optional[str] = Field(None, description="验证码/钉钉Code")

# --- 登录成功响应 ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user_name: str

# --- 用户信息响应 ---
class UserInfo(BaseModel):
    id: int
    username: Optional[str]
    nickname: Optional[str]
    avatar: Optional[str]
    roles: list[str] = []