"""
MinerU Tianshu - Authentication Routes
认证路由

提供用户注册、登录、API Key 管理、SSO 等接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from typing import List
from datetime import timedelta
from loguru import logger

from .models import (
    User,
    UserCreate,
    UserUpdate,
    UserLogin,
    Token,
    APIKeyCreate,
    APIKeyResponse,
    Permission,
)
from .auth_db import AuthDB
from .jwt_handler import create_access_token, JWT_EXPIRE_MINUTES
from .dependencies import (
    get_auth_db,
    get_current_active_user,
    require_permission,
)
from .sso import get_sso_config, create_sso_provider, OIDC_AVAILABLE

# 创建路由
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, auth_db: AuthDB = Depends(get_auth_db)):
    """
    用户注册

    创建新用户账户。默认角色为 'user'，需要管理员才能创建其他角色。
    """
    try:
        user = auth_db.create_user(user_data)
        logger.info(f"✅ User registered: {user.username} ({user.email})")
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, auth_db: AuthDB = Depends(get_auth_db)):
    """
    用户登录

    使用用户名和密码登录，返回 JWT Access Token。
    """
    user = auth_db.authenticate_user(credentials.username, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    # 生成 JWT Token
    access_token = create_access_token(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        expires_delta=timedelta(minutes=JWT_EXPIRE_MINUTES),
    )

    logger.info(f"✅ User logged in: {user.username}")

    return Token(access_token=access_token, token_type="bearer", expires_in=JWT_EXPIRE_MINUTES * 60)


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    获取当前登录用户信息

    需要认证。返回当前用户的详细信息。
    """
    return current_user


@router.patch("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    更新当前用户信息

    用户可以更新自己的邮箱和全名，不能更新角色。
    """
    # 用户不能更改自己的角色
    if user_update.role is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change your own role")

    update_data = user_update.model_dump(exclude_unset=True, exclude={"role", "is_active"})

    if not update_data:
        return current_user

    success = auth_db.update_user(current_user.user_id, **update_data)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update user")

    updated_user = auth_db.get_user_by_id(current_user.user_id)
    logger.info(f"✅ User updated: {updated_user.username}")
    return updated_user


# ==================== API Key 管理 ====================


@router.post("/apikeys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(require_permission(Permission.APIKEY_CREATE)),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    创建 API Key

    为当前用户创建一个新的 API Key。API Key 只会在创建时返回一次，请妥善保管。
    """
    key_info = auth_db.create_api_key(
        user_id=current_user.user_id,
        name=key_data.name,
        expires_days=key_data.expires_days,
    )

    logger.info(f"✅ API Key created: {key_info['prefix']}... for user {current_user.username}")

    return APIKeyResponse(
        key_id=key_info["key_id"],
        api_key=key_info["api_key"],
        prefix=key_info["prefix"],
        name=key_data.name,
        created_at=key_info["created_at"],
        expires_at=key_info["expires_at"],
    )


@router.get("/apikeys")
async def list_api_keys(
    current_user: User = Depends(require_permission(Permission.APIKEY_LIST_OWN)),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    列出当前用户的所有 API Key

    返回 API Key 列表，不包含完整的 key，只显示前缀。
    """
    keys = auth_db.list_api_keys(current_user.user_id)
    return {"success": True, "count": len(keys), "api_keys": keys}


@router.delete("/apikeys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(require_permission(Permission.APIKEY_DELETE)),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    删除 API Key

    删除指定的 API Key。只能删除自己的 API Key。
    """
    success = auth_db.delete_api_key(key_id, current_user.user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

    logger.info(f"✅ API Key deleted: {key_id} by user {current_user.username}")
    return {"success": True, "message": "API Key deleted successfully"}


# ==================== 用户管理 (需要管理员权限) ====================


@router.get("/users", response_model=List[User])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_permission(Permission.USER_LIST)),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    列出所有用户

    需要管理员权限。返回用户列表。
    """
    users = auth_db.list_users(limit=limit, offset=offset)
    return users


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission(Permission.USER_CREATE)),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    创建用户 (管理员)

    管理员可以创建任意角色的用户。
    """
    try:
        user = auth_db.create_user(user_data)
        logger.info(f"✅ User created by admin: {user.username} (role: {user.role.value})")
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(require_permission(Permission.USER_UPDATE)),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    更新用户信息 (管理员)

    管理员可以更新任意用户的信息，包括角色和状态。
    """
    update_data = user_update.model_dump(exclude_unset=True)

    if not update_data:
        user = auth_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    success = auth_db.update_user(user_id, **update_data)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated_user = auth_db.get_user_by_id(user_id)
    logger.info(f"✅ User updated by admin: {updated_user.username}")
    return updated_user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.USER_DELETE)),
    auth_db: AuthDB = Depends(get_auth_db),
):
    """
    删除用户 (管理员)

    管理员可以删除用户。不能删除自己。
    """
    if user_id == current_user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    success = auth_db.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info(f"✅ User deleted by admin: {user_id}")
    return {"success": True, "message": "User deleted successfully"}


# ==================== SSO 集成 ====================


@router.get("/sso/enabled")
async def sso_status():
    """
    检查 SSO 是否启用

    返回 SSO 配置状态。
    """
    sso_config = get_sso_config()
    return {
        "enabled": sso_config is not None,
        "type": sso_config.get("type") if sso_config else None,
    }


if OIDC_AVAILABLE:
    # 只有在 authlib 可用时才注册 SSO 路由

    @router.get("/sso/login")
    async def sso_login(request: Request):
        """
        SSO 登录入口

        重定向到 SSO 提供者进行认证。
        """
        sso_config = get_sso_config()
        if not sso_config:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO not configured")

        provider = create_sso_provider(sso_config["type"], sso_config)
        if not provider:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to initialize SSO")

        # 对于 OIDC,使用 authlib 的 OAuth 客户端
        if sso_config["type"] == "oidc":
            from authlib.integrations.starlette_client import OAuth

            oauth = OAuth()
            oauth.register(
                name="oidc",
                client_id=sso_config["client_id"],
                client_secret=sso_config["client_secret"],
                server_metadata_url=f"{sso_config['issuer_url']}/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )

            redirect_uri = sso_config["redirect_uri"]
            return await oauth.oidc.authorize_redirect(request, redirect_uri)

        # SAML 实现类似
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SAML not implemented yet")

    @router.get("/sso/callback")
    async def sso_callback(request: Request, auth_db: AuthDB = Depends(get_auth_db)):
        """
        SSO 回调接口

        处理 SSO 提供者的回调，创建或获取用户，返回 JWT Token。
        """
        sso_config = get_sso_config()
        if not sso_config:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SSO not configured")

        if sso_config["type"] == "oidc":
            from authlib.integrations.starlette_client import OAuth

            oauth = OAuth()
            oauth.register(
                name="oidc",
                client_id=sso_config["client_id"],
                client_secret=sso_config["client_secret"],
                server_metadata_url=f"{sso_config['issuer_url']}/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )

            # 获取 access token 和用户信息
            token = await oauth.oidc.authorize_access_token(request)
            user_info = token.get("userinfo")

            if not user_info:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get user info from SSO")

            # 获取或创建 SSO 用户
            sso_subject = user_info.get("sub")
            user = auth_db.get_or_create_sso_user(
                sso_subject=sso_subject,
                provider="oidc",
                user_info={
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "preferred_username": user_info.get("preferred_username"),
                },
            )

            # 生成 JWT Token
            access_token = create_access_token(
                user_id=user.user_id,
                username=user.username,
                role=user.role,
                expires_delta=timedelta(minutes=JWT_EXPIRE_MINUTES),
            )

            logger.info(f"✅ SSO user logged in: {user.username} (provider: oidc)")

            # 重定向到前端，携带 token
            frontend_url = request.url_for("root").replace("/api/v1/auth/sso/callback", "")
            return RedirectResponse(url=f"{frontend_url}?token={access_token}")

        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="SAML not implemented yet")
