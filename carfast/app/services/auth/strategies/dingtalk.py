# app/services/auth/strategies/dingtalk.py
import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth.base import AuthStrategy
from app.models.user import UserAuth, UserProfile
from app.config import settings


class DingTalkStrategy(AuthStrategy):
    """
    钉钉 OAuth 2.0 登录策略 (v1.0 新版接口)
    文档: https://open.dingtalk.com/document/orgapp-server/obtain-user-token
    """

    async def authenticate(self, payload: dict, db: AsyncSession) -> UserAuth:
        # 1. 获取前端传来的临时授权码
        auth_code = payload.get("code")
        if not auth_code:
            raise HTTPException(status_code=400, detail="缺少钉钉授权码(code)")

        # 2. 用 Code 换 AccessToken (服务器端通信)
        token_data = await self._get_access_token(auth_code)
        access_token = token_data.get("accessToken")

        # 3. 用 AccessToken 换用户信息 (OpenID, Mobile, Nickname)
        ding_user = await self._get_user_info(access_token)

        # 4. 核心认证逻辑 (查库/注册)
        return await self._login_or_register(ding_user, db)

    async def _get_access_token(self, code: str) -> dict:
        """步骤1: 调用钉钉 v1.0 接口获取 Token"""
        url = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
        headers = {"Content-Type": "application/json"}
        body = {
            "clientId": settings.DINGTALK_CLIENT_ID,
            "clientSecret": settings.DINGTALK_CLIENT_SECRET,
            "code": code,
            "grantType": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers)
            data = resp.json()

            if resp.status_code != 200 or "accessToken" not in data:
                print(f"❌ [DingTalk] Token获取失败: {data}")
                raise HTTPException(status_code=401, detail="钉钉授权失效，请重新扫码")

            return data

    async def _get_user_info(self, access_token: str) -> dict:
        """步骤2: 调用 users/me 获取个人信息"""
        url = "https://api.dingtalk.com/v1.0/contact/users/me"
        # ⚠️ 注意: 钉钉新版要求 token 放在 header 的 x-acs-dingtalk-access-token 字段
        headers = {
            "x-acs-dingtalk-access-token": access_token
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            data = resp.json()

            if resp.status_code != 200:
                print(f"❌ [DingTalk] 用户信息获取失败: {data}")
                raise HTTPException(status_code=401, detail="获取钉钉用户信息失败")

            # 返回字段示例: { "nick": "张三", "openId": "...", "mobile": "138...", "unionId": "..." }
            return data

    async def _login_or_register(self, ding_data: dict, db: AsyncSession) -> UserAuth:
        """步骤3: 数据库逻辑"""
        # 优先使用 UnionId (跨应用唯一)，其次 OpenId
        ding_openid = ding_data.get("openId")
        phone = ding_data.get("mobile")  # 需在钉钉后台申请"手机号信息"权限
        nickname = ding_data.get("nick", "钉钉用户")

        if not phone:
            # 如果没申请到手机号权限，这步会卡住，建议去钉钉后台开通
            print("⚠️ 警告: 未获取到钉钉手机号，建议检查开发者后台权限")

        # A. 尝试通过 Phone 查找 (最通用)
        stmt = select(UserAuth).where(UserAuth.phone == phone)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # B. 自动注册
        if not user:
            print(f"🚀 [DingTalk] 新用户自动注册: {nickname} ({phone})")
            user = UserAuth(
                phone=phone,
                status=1,
                # wx_openid=ding_openid # 暂时借用这个字段存 ding_openid，或者你去改表结构
            )
            db.add(user)
            await db.flush()

            profile = UserProfile(
                user_id=user.id,
                nickname=nickname,
                avatar_url=ding_data.get("avatarUrl")
            )
            db.add(profile)
            await db.flush()

        if user.status != 1:
            raise HTTPException(status_code=403, detail="账号已被禁用")

        return user