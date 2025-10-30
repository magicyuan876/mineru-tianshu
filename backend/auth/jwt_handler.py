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
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
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
    except jwt.JWTError as e:
        logger.debug(f"JWT validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        return None
