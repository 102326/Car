from passlib.context import CryptContext

# 使用 bcrypt 算法
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    print(plain_password, hashed_password)
    """验证明文密码和数据库哈希是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """生成密码哈希值"""
    return pwd_context.hash(password)

# print(get_password_hash("123456"))