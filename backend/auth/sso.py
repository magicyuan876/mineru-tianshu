"""
MinerU Tianshu - SSO Integration
SSO 集成

支持 OIDC (OpenID Connect) 和 SAML 企业级单点登录
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Optional
from loguru import logger

# 尝试导入 OIDC 库
try:
    from authlib.integrations.starlette_client import OAuth

    OIDC_AVAILABLE = True
except ImportError:
    OIDC_AVAILABLE = False
    logger.warning("⚠️  authlib not installed, OIDC SSO will be disabled")

# 尝试导入 SAML 库
try:
    import importlib.util

    SAML_AVAILABLE = importlib.util.find_spec("onelogin.saml2.auth") is not None
except ImportError:
    SAML_AVAILABLE = False
    logger.warning("⚠️  python3-saml not installed, SAML SSO will be disabled")


class SSOProvider(ABC):
    """SSO 提供者基类"""

    @abstractmethod
    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        获取 SSO 授权 URL

        Args:
            redirect_uri: 回调 URI
            state: 状态参数 (防 CSRF)

        Returns:
            str: 授权 URL
        """
        pass

    @abstractmethod
    async def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        """
        从授权码获取用户信息

        Args:
            code: 授权码
            redirect_uri: 回调 URI

        Returns:
            dict: 用户信息
        """
        pass


class OIDCProvider(SSOProvider):
    """OIDC (OpenID Connect) 提供者"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        issuer_url: str,
        redirect_uri: str,
    ):
        """
        初始化 OIDC 提供者

        Args:
            client_id: OIDC 客户端 ID
            client_secret: OIDC 客户端密钥
            issuer_url: OIDC Issuer URL (如 https://auth.example.com/realms/myrealm)
            redirect_uri: 回调 URI
        """
        if not OIDC_AVAILABLE:
            raise RuntimeError("authlib is required for OIDC SSO. Install: pip install authlib")

        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer_url = issuer_url
        self.redirect_uri = redirect_uri

        # 配置 OAuth 客户端
        self.oauth = OAuth()
        self.oauth.register(
            name="oidc",
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url=f"{issuer_url}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """获取 OIDC 授权 URL"""
        # authlib 自动处理授权 URL 生成
        # 这里返回一个模板,实际使用时需要在路由中调用 oauth.oidc.authorize_redirect()
        return f"{self.issuer_url}/protocol/openid-connect/auth"

    async def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        """
        从授权码获取用户信息

        Args:
            code: 授权码
            redirect_uri: 回调 URI

        Returns:
            dict: 用户信息 (sub, email, name, preferred_username, etc.)
        """
        # 在实际使用中,这个方法应该在 FastAPI 路由中调用
        # token = await oauth.oidc.authorize_access_token(request)
        # user_info = token.get('userinfo')
        # 这里提供一个占位实现
        raise NotImplementedError("This method should be called from FastAPI route handler")


class SAMLProvider(SSOProvider):
    """SAML 2.0 提供者"""

    def __init__(
        self,
        entity_id: str,
        sso_url: str,
        x509_cert: str,
        sp_entity_id: str,
        sp_acs_url: str,
    ):
        """
        初始化 SAML 提供者

        Args:
            entity_id: IdP Entity ID
            sso_url: IdP SSO URL
            x509_cert: IdP 签名证书
            sp_entity_id: SP Entity ID (本服务)
            sp_acs_url: SP Assertion Consumer Service URL
        """
        if not SAML_AVAILABLE:
            raise RuntimeError("python3-saml is required for SAML SSO. Install: pip install python3-saml")

        self.settings = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": sp_entity_id,
                "assertionConsumerService": {
                    "url": sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            },
            "idp": {
                "entityId": entity_id,
                "singleSignOnService": {
                    "url": sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": x509_cert,
            },
        }

    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """获取 SAML 授权 URL (SSO URL)"""
        # SAML 使用 IdP-Initiated 或 SP-Initiated 流程
        # 这里返回 SSO URL,实际使用时需要构造 SAML 请求
        return self.settings["idp"]["singleSignOnService"]["url"]

    async def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        """
        处理 SAML Response 并获取用户信息

        Args:
            code: SAML Response (not authorization code)
            redirect_uri: 回调 URI

        Returns:
            dict: 用户信息
        """
        # 在实际使用中,这个方法需要解析 SAML Response
        # auth = OneLogin_Saml2_Auth(request_data, self.settings)
        # auth.process_response()
        # attributes = auth.get_attributes()
        raise NotImplementedError("This method should be called from FastAPI route handler")


def create_sso_provider(sso_type: str, config: Dict) -> Optional[SSOProvider]:
    """
    创建 SSO 提供者工厂方法

    Args:
        sso_type: SSO 类型 (oidc/saml)
        config: SSO 配置

    Returns:
        SSOProvider: SSO 提供者实例,配置不完整返回 None
    """
    if sso_type == "oidc":
        if not OIDC_AVAILABLE:
            logger.error("OIDC SSO requested but authlib is not installed")
            return None

        required_fields = ["client_id", "client_secret", "issuer_url", "redirect_uri"]
        if not all(config.get(field) for field in required_fields):
            logger.error(f"OIDC configuration incomplete, required: {required_fields}")
            return None

        return OIDCProvider(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            issuer_url=config["issuer_url"],
            redirect_uri=config["redirect_uri"],
        )

    elif sso_type == "saml":
        if not SAML_AVAILABLE:
            logger.error("SAML SSO requested but python3-saml is not installed")
            return None

        required_fields = ["entity_id", "sso_url", "x509_cert", "sp_entity_id", "sp_acs_url"]
        if not all(config.get(field) for field in required_fields):
            logger.error(f"SAML configuration incomplete, required: {required_fields}")
            return None

        return SAMLProvider(
            entity_id=config["entity_id"],
            sso_url=config["sso_url"],
            x509_cert=config["x509_cert"],
            sp_entity_id=config["sp_entity_id"],
            sp_acs_url=config["sp_acs_url"],
        )

    else:
        logger.error(f"Unknown SSO type: {sso_type}")
        return None


# 从环境变量加载 SSO 配置
def get_sso_config() -> Optional[Dict]:
    """
    从环境变量读取 SSO 配置

    Environment Variables:
        SSO_ENABLED: true/false
        SSO_TYPE: oidc/saml
        SSO_CLIENT_ID: OIDC Client ID
        SSO_CLIENT_SECRET: OIDC Client Secret
        SSO_ISSUER_URL: OIDC Issuer URL
        SSO_REDIRECT_URI: 回调 URI
        ... (SAML 相关变量)

    Returns:
        dict: SSO 配置,未启用返回 None
    """
    if os.getenv("SSO_ENABLED", "false").lower() != "true":
        return None

    sso_type = os.getenv("SSO_TYPE", "oidc").lower()

    if sso_type == "oidc":
        return {
            "type": "oidc",
            "client_id": os.getenv("SSO_CLIENT_ID"),
            "client_secret": os.getenv("SSO_CLIENT_SECRET"),
            "issuer_url": os.getenv("SSO_ISSUER_URL"),
            "redirect_uri": os.getenv("SSO_REDIRECT_URI"),
        }
    elif sso_type == "saml":
        return {
            "type": "saml",
            "entity_id": os.getenv("SSO_ENTITY_ID"),
            "sso_url": os.getenv("SSO_SSO_URL"),
            "x509_cert": os.getenv("SSO_X509_CERT"),
            "sp_entity_id": os.getenv("SSO_SP_ENTITY_ID"),
            "sp_acs_url": os.getenv("SSO_SP_ACS_URL"),
        }
    else:
        logger.error(f"Invalid SSO_TYPE: {sso_type}")
        return None
