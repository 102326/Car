"""
密码加密工具模块
使用 Argon2 算法进行密码哈希（比 bcrypt 更安全）
"""
from passlib.context import CryptContext
from typing import Optional


# ==========================================
# 密码上下文配置
# ==========================================
# 使用 Argon2 算法（2015年密码哈希竞赛冠军）
# 优势：抗GPU/ASIC攻击，内存硬度高
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",  # 自动标记旧算法为过时
    argon2__memory_cost=65536,  # 64MB 内存消耗
    argon2__time_cost=3,  # 迭代次数
    argon2__parallelism=4  # 并行度
)


# ==========================================
# 密码工具函数
# ==========================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码和数据库哈希是否匹配
    
    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的哈希密码
        
    Returns:
        bool: True=密码正确，False=密码错误
        
    Example:
        ```python
        user = await get_user_by_phone(phone, db)
        if not verify_password(password, user.password_hash):
            raise HTTPException(401, "密码错误")
        ```
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # 如果哈希格式损坏，返回 False
        return False


def get_password_hash(password: str) -> str:
    """
    生成密码哈希值
    
    Args:
        password: 明文密码
        
    Returns:
        str: Argon2 哈希字符串
        
    Example:
        ```python
        user = UserAuth(
            phone="13800138000",
            password_hash=get_password_hash(request.password)
        )
        ```
    """
    return pwd_context.hash(password)


def check_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    检查密码强度
    
    规则：
    - 长度至少8位
    - 包含大小写字母、数字
    - 可选：包含特殊字符
    
    Args:
        password: 明文密码
        
    Returns:
        tuple[bool, Optional[str]]: (是否合格, 错误提示)
        
    Example:
        ```python
        is_valid, error = check_password_strength(password)
        if not is_valid:
            raise HTTPException(400, detail=error)
        ```
    """
    if len(password) < 8:
        return False, "密码长度至少8位"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        return False, "密码必须包含大小写字母和数字"
    
    return True, None


# ==========================================
# 测试用例（开发环境）
# ==========================================
if __name__ == "__main__":
    # 生成测试密码哈希
    test_password = "Test@1234"
    hashed = get_password_hash(test_password)
    print(f"明文: {test_password}")
    print(f"哈希: {hashed}")
    print(f"验证: {verify_password(test_password, hashed)}")
    
    # 测试密码强度
    is_valid, error = check_password_strength("weak")
    print(f"弱密码: {is_valid}, {error}")
    
    is_valid, error = check_password_strength("Strong@1234")
    print(f"强密码: {is_valid}, {error}")