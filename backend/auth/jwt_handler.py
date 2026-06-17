"""
MinerU Tianshu - JWT Token Handler
JWT Token 处理器

负责 JWT Token 的生成和验证
"""

import os
from datetime import datetime, timedelta
from typing import Optional
import jwt
from loguru import logger

from .models import TokenData, UserRole

# JWT 配置
# 安全：绝不使用硬编码默认密钥。HS256 为对称密钥，一旦为公开默认值，
# 任何人都能伪造任意用户（含 admin）的 token，完全绕过认证。
# 未配置或仍为旧默认值时直接拒绝启动。
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY or JWT_SECRET_KEY == "your-secret-key-change-in-production":
    raise RuntimeError(
        "JWT_SECRET_KEY 未设置或仍为默认占位值。请先生成强随机密钥再启动，例如：\n"
        "  export JWT_SECRET_KEY=$(openssl rand -hex 32)\n"
        "（绝不能使用公开默认密钥，否则可被伪造任意 admin token）"
    )
if len(JWT_SECRET_KEY) < 32:
    raise RuntimeError("JWT_SECRET_KEY 太短（至少 32 字符），存在被暴力破解的风险。")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 默认 24 小时


def create_access_token(user_id: str, username: str, role: UserRole, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Access Token

    Args:
        user_id: 用户ID
        username: 用户名
        role: 用户角色
        expires_delta: 过期时间增量 (None 则使用默认值)

    Returns:
        str: JWT Token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)

    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    验证 JWT Token

    Args:
        token: JWT Token

    Returns:
        TokenData: Token 数据，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role_str: str = payload.get("role")

        if user_id is None or username is None or role_str is None:
            return None

        return TokenData(user_id=user_id, username=username, role=UserRole(role_str))

    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidSignatureError:
        logger.debug("Invalid signature")
        return None
    except (jwt.DecodeError, jwt.InvalidTokenError) as e:
        logger.debug(f"JWT validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        return None
