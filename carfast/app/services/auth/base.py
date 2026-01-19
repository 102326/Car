# app/services/auth/base.py
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserAuth


class AuthStrategy(ABC):
    """认证策略基类 (Abstract Base Class)"""

    @abstractmethod
    async def authenticate(self, payload: dict, db: AsyncSession) -> UserAuth:
        """
        核心认证逻辑接口
        :param payload: 前端传来的参数字典
        :param db: 数据库会话 (用于查用户)
        :return: UserAuth 对象 (认证成功) 或抛出 HTTPException
        """
        pass