"""
MinerU Tianshu - Authentication & Authorization Module
天枢认证授权模块

企业级用户认证和权限控制系统
支持本地注册、JWT Token、API Key、SSO 集成
"""

from .models import User, UserRole, Permission, APIKey
from .auth_db import AuthDB
from .jwt_handler import create_access_token, verify_token
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    require_permission,
    require_role,
    get_api_key_user,
)
from .sso import SSOProvider, OIDCProvider, SAMLProvider

__all__ = [
    "User",
    "UserRole",
    "Permission",
    "APIKey",
    "AuthDB",
    "create_access_token",
    "verify_token",
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    "require_permission",
    "require_role",
    "get_api_key_user",
    "SSOProvider",
    "OIDCProvider",
    "SAMLProvider",
]
