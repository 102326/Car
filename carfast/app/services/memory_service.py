"""
Memory Service for CarFast Agent.

Implements hybrid Redis/Postgres storage with:
- Write-Through: 同时写入 DB 和 Redis
- Graceful Degradation: 任何环节失败不阻断主流程

Part of Phase E: Agent Memory System.
"""

import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
import redis.asyncio as aioredis

from app.core.database import AsyncSessionLocal
from app.core.redis import pool as redis_pool
from app.models.agent_memory import AgentMemoryProfile

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

REDIS_KEY_PREFIX = "agent:memory:"
REDIS_TTL_SECONDS = 3600  # 1 hour


# ============================================================================
# Redis Helpers
# ============================================================================

def _redis_key(user_id: str) -> str:
    """Generate Redis key for user profile."""
    return f"{REDIS_KEY_PREFIX}{user_id}"


async def _get_redis_client() -> aioredis.Redis:
    """Get a Redis client from connection pool."""
    return aioredis.Redis(connection_pool=redis_pool)


# ============================================================================
# Public API
# ============================================================================

async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    获取用户 Agent 记忆画像。
    
    查询顺序: Redis (Hot) -> Postgres (Cold) -> Cache Backfill
    
    Graceful Degradation:
    - Redis 失败 -> 继续查 DB
    - DB 失败 -> 返回空 Profile
    - 所有失败仅记录日志，不抛出异常
    
    Args:
        user_id: 用户ID (字符串，兼容前端传递)
        
    Returns:
        用户画像字典。无数据时返回 {}。
    """
    if not user_id:
        return {}
    
    redis_key = _redis_key(user_id)
    
    # ========================================
    # Step 1: Try Redis (Hot Cache)
    # ========================================
    try:
        redis_client = await _get_redis_client()
        cached = await redis_client.get(redis_key)
        await redis_client.close()
        
        if cached:
            logger.debug(f"[MemoryService] Cache HIT for user={user_id}")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"[MemoryService] Redis GET failed for user={user_id}: {e}")
        # Continue to DB fallback
    
    # ========================================
    # Step 2: Try Postgres (Cold Storage)
    # ========================================
    profile_data: Dict[str, Any] = {}
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentMemoryProfile).where(
                    AgentMemoryProfile.user_id == int(user_id)
                )
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                profile_data = profile.to_dict()
                logger.debug(f"[MemoryService] DB HIT for user={user_id}")
            else:
                logger.debug(f"[MemoryService] No profile found for user={user_id}")
                return {}
                
    except (SQLAlchemyError, ValueError) as e:
        logger.error(f"[MemoryService] DB GET failed for user={user_id}: {e}")
        return {}  # Graceful degradation
    
    # ========================================
    # Step 3: Cache Backfill (Best Effort)
    # ========================================
    if profile_data:
        try:
            redis_client = await _get_redis_client()
            await redis_client.setex(
                redis_key,
                REDIS_TTL_SECONDS,
                json.dumps(profile_data, ensure_ascii=False, default=str)
            )
            await redis_client.close()
            logger.debug(f"[MemoryService] Cache BACKFILL for user={user_id}")
        except Exception as e:
            logger.warning(f"[MemoryService] Redis BACKFILL failed for user={user_id}: {e}")
            # Non-critical, continue
    
    return profile_data


async def update_user_profile(
    user_id: str,
    data: Dict[str, Any],
    expected_version: Optional[int] = None
) -> bool:
    """
    更新用户 Agent 记忆画像。
    
    Write-Through Pattern:
    1. 更新 Postgres (带乐观锁检查)
    2. 刷新 Redis (重置 TTL)
    
    Graceful Degradation:
    - DB 失败 -> 返回 False，不更新缓存
    - Redis 失败 -> 仅记录日志，返回 True (DB 已更新)
    
    Args:
        user_id: 用户ID
        data: 要更新的字段字典 (支持部分更新)
        expected_version: 期望的版本号 (用于乐观锁，None 表示不检查)
        
    Returns:
        True 如果更新成功，False 如果失败或版本冲突。
    """
    if not user_id or not data:
        return False
    
    try:
        user_id_int = int(user_id)
    except ValueError:
        logger.error(f"[MemoryService] Invalid user_id: {user_id}")
        return False
    
    # ========================================
    # Step 1: Update Postgres with Optimistic Lock
    # ========================================
    try:
        async with AsyncSessionLocal() as session:
            # Get current profile (or create if not exists)
            result = await session.execute(
                select(AgentMemoryProfile).where(
                    AgentMemoryProfile.user_id == user_id_int
                )
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                # Check version for optimistic locking
                if expected_version is not None and profile.version != expected_version:
                    logger.warning(
                        f"[MemoryService] Version conflict for user={user_id}: "
                        f"expected={expected_version}, actual={profile.version}"
                    )
                    return False
                
                # Update fields
                for key, value in data.items():
                    if hasattr(profile, key) and key not in ('user_id', 'created_at'):
                        setattr(profile, key, value)
                
                # Increment version
                profile.version += 1
                
            else:
                # Create new profile
                profile = AgentMemoryProfile(
                    user_id=user_id_int,
                    version=1,
                    **{k: v for k, v in data.items() 
                       if hasattr(AgentMemoryProfile, k) and k not in ('user_id', 'version')}
                )
                session.add(profile)
            
            await session.commit()
            await session.refresh(profile)
            
            profile_data = profile.to_dict()
            logger.info(f"[MemoryService] DB UPDATE success for user={user_id}, version={profile.version}")
            
    except SQLAlchemyError as e:
        logger.error(f"[MemoryService] DB UPDATE failed for user={user_id}: {e}")
        return False
    
    # ========================================
    # Step 2: Refresh Redis Cache (Best Effort)
    # ========================================
    redis_key = _redis_key(user_id)
    
    try:
        redis_client = await _get_redis_client()
        await redis_client.setex(
            redis_key,
            REDIS_TTL_SECONDS,
            json.dumps(profile_data, ensure_ascii=False, default=str)
        )
        await redis_client.close()
        logger.debug(f"[MemoryService] Cache REFRESH for user={user_id}")
    except Exception as e:
        logger.warning(f"[MemoryService] Redis REFRESH failed for user={user_id}: {e}")
        # Non-critical, DB already updated
    
    return True


async def get_user_profile_summary(user_id: str) -> str:
    """
    获取用户画像的自然语言摘要，用于注入 LLM Prompt。
    
    Args:
        user_id: 用户ID
        
    Returns:
        人类可读的用户画像描述。
    """
    if not user_id:
        return ""
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentMemoryProfile).where(
                    AgentMemoryProfile.user_id == int(user_id)
                )
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                return profile.to_natural_language()
            
    except Exception as e:
        logger.warning(f"[MemoryService] Get summary failed for user={user_id}: {e}")
    
    return ""


async def delete_user_profile(user_id: str) -> bool:
    """
    删除用户 Agent 记忆 (用于测试或用户请求遗忘)。
    
    Args:
        user_id: 用户ID
        
    Returns:
        True 如果删除成功。
    """
    if not user_id:
        return False
    
    redis_key = _redis_key(user_id)
    
    # Delete from Redis
    try:
        redis_client = await _get_redis_client()
        await redis_client.delete(redis_key)
        await redis_client.close()
    except Exception as e:
        logger.warning(f"[MemoryService] Redis DELETE failed for user={user_id}: {e}")
    
    # Delete from DB
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentMemoryProfile).where(
                    AgentMemoryProfile.user_id == int(user_id)
                )
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                await session.delete(profile)
                await session.commit()
                logger.info(f"[MemoryService] DELETE success for user={user_id}")
            
        return True
        
    except Exception as e:
        logger.error(f"[MemoryService] DB DELETE failed for user={user_id}: {e}")
        return False
