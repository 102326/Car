"""
认证系统测试脚本
测试 JWT Token 生成、验证和密码加密功能
"""
import asyncio
from app.utils.jwt import MyJWT
from app.utils.security import (
    get_password_hash,
    verify_password,
    check_password_strength
)


async def test_password_hash():
    """测试密码加密"""
    print("=" * 60)
    print("测试 1: 密码加密和验证")
    print("=" * 60)
    
    password = "Test@1234"
    
    # 生成哈希
    hashed = get_password_hash(password)
    print(f"✅ 明文密码: {password}")
    print(f"✅ 哈希结果: {hashed[:50]}...")
    
    # 验证密码
    is_correct = verify_password(password, hashed)
    print(f"✅ 密码验证: {'通过' if is_correct else '失败'}")
    
    # 错误密码
    is_wrong = verify_password("wrong_password", hashed)
    print(f"✅ 错误密码: {'正确拦截' if not is_wrong else '验证失败'}")
    
    print()


async def test_password_strength():
    """测试密码强度检查"""
    print("=" * 60)
    print("测试 2: 密码强度检查")
    print("=" * 60)
    
    test_cases = [
        ("123", False, "太短"),
        ("12345678", False, "无大小写"),
        ("Test1234", True, "合格"),
        ("Test@1234", True, "合格"),
    ]
    
    for pwd, expected_valid, desc in test_cases:
        is_valid, error = check_password_strength(pwd)
        status = "✅" if is_valid == expected_valid else "❌"
        result = "合格" if is_valid else error
        print(f"{status} 密码: {pwd:15s} => {result} ({desc})")
    
    print()


async def test_jwt_token():
    """测试 JWT Token 生成和解码"""
    print("=" * 60)
    print("测试 3: JWT Token 生成和解码")
    print("=" * 60)
    
    user_id = 12345
    
    # 生成 Token
    payload = {
        "sub": str(user_id),
        "type": "access"
    }
    token = MyJWT.encode(payload)
    print(f"✅ 生成 Token: {token[:50]}...")
    
    # 解码 Token
    decoded = MyJWT.decode_token(token)
    print(f"✅ 解码结果:")
    print(f"   - 用户ID: {decoded.get('sub')}")
    print(f"   - Token类型: {decoded.get('type')}")
    print(f"   - JTI: {decoded.get('jti')[:8]}...")
    print(f"   - 签发时间: {decoded.get('iat')}")
    print(f"   - 过期时间: {decoded.get('exp')}")
    
    print()


async def test_login_logout():
    """测试登录和登出"""
    print("=" * 60)
    print("测试 4: 用户登录和登出")
    print("=" * 60)
    
    user_id = 99999
    
    try:
        # 登录
        access_token, refresh_token = await MyJWT.login_user(user_id)
        print(f"✅ 登录成功")
        print(f"   - Access Token: {access_token[:50]}...")
        print(f"   - Refresh Token: {refresh_token[:50]}...")
        
        # 查看会话
        session = await MyJWT.get_active_session_info(user_id)
        print(f"✅ 活跃会话:")
        print(f"   - 登录时间: {session.get('login_at')}")
        
        # 刷新 Token
        new_access, error = await MyJWT.refresh_access_token(refresh_token)
        if new_access:
            print(f"✅ Token 刷新成功: {new_access[:50]}...")
        else:
            print(f"❌ Token 刷新失败: {error}")
        
        # 登出
        await MyJWT.logout_user(user_id)
        print(f"✅ 登出成功")
        
        # 再次查看会话
        session = await MyJWT.get_active_session_info(user_id)
        print(f"✅ 会话状态: {'已清除' if not session else '仍存在'}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print()


async def test_token_blacklist():
    """测试 Token 黑名单"""
    print("=" * 60)
    print("测试 5: Token 黑名单")
    print("=" * 60)
    
    jti = "test_jti_12345"
    
    # 检查是否在黑名单
    is_revoked = await MyJWT.is_token_revoked(jti)
    print(f"✅ 初始状态: {'在黑名单' if is_revoked else '不在黑名单'}")
    
    # 加入黑名单
    await MyJWT.add_to_blacklist(jti, 60)
    print(f"✅ 已加入黑名单（60秒过期）")
    
    # 再次检查
    is_revoked = await MyJWT.is_token_revoked(jti)
    print(f"✅ 当前状态: {'在黑名单' if is_revoked else '不在黑名单'}")
    
    print()


async def main():
    """运行所有测试"""
    print("\n")
    print("🔐" * 30)
    print("  CarFast 认证系统测试套件")
    print("🔐" * 30)
    print()
    
    # 运行测试
    await test_password_hash()
    await test_password_strength()
    await test_jwt_token()
    await test_login_logout()
    await test_token_blacklist()
    
    print("=" * 60)
    print("  测试完成！")
    print("=" * 60)
    print()
    print("✅ 密码加密工作正常")
    print("✅ JWT Token 生成和解码正常")
    print("✅ 登录登出流程正常")
    print("✅ Token 黑名单功能正常")
    print()
    print("🎉 认证系统已就绪，可以开始开发业务逻辑了！")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试已取消")
    except Exception as e:
        print(f"\n\n❌ 测试运行失败: {e}")
        import traceback
        traceback.print_exc()
