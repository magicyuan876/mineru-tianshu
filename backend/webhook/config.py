"""
MinerU Tianshu - Webhook 通知配置

配置存 system_config 表（webhook_* 键），读取端带默认值兜底，兼容未配置过的存量部署。
"""

from auth.system_config import SystemConfig

# webhook_secret 的掩码占位符：接口不返回真实密钥，前端未修改时原样发回
WEBHOOK_SECRET_MASK = "********"

DEFAULT_ENABLED = "false"
DEFAULT_URL = ""
DEFAULT_SECRET = ""
DEFAULT_EVENTS = "task.completed,task.failed"
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_ATTEMPTS = 8
DEFAULT_AUTH_TYPE = "none"
DEFAULT_AUTH_HEADER_NAME = "X-API-Key"

# 投递鉴权的敏感字段：接口只回显掩码，前端发回掩码表示不修改
AUTH_SENSITIVE_KEYS = ("webhook_auth_token", "webhook_auth_password", "webhook_auth_header_value")


def get_webhook_config() -> dict:
    """读取 webhook 配置（含默认值兜底）"""
    raw = SystemConfig().get_all_configs()

    def get(key: str, default: str) -> str:
        value = raw.get(key)
        return value if value is not None else default

    def get_int(key: str, default: int) -> int:
        try:
            return int(get(key, str(default)))
        except (ValueError, TypeError):
            return default

    events = [e.strip() for e in get("webhook_events", DEFAULT_EVENTS).split(",") if e.strip()]

    auth_type = get("webhook_auth_type", DEFAULT_AUTH_TYPE).strip() or DEFAULT_AUTH_TYPE
    if auth_type not in ("none", "bearer", "basic", "api_key"):
        auth_type = DEFAULT_AUTH_TYPE

    return {
        "enabled": get("webhook_enabled", DEFAULT_ENABLED) == "true",
        "url": get("webhook_url", DEFAULT_URL).strip(),
        "secret": get("webhook_secret", DEFAULT_SECRET),
        "events": events,
        "timeout": get_int("webhook_timeout", DEFAULT_TIMEOUT),
        "max_attempts": get_int("webhook_max_attempts", DEFAULT_MAX_ATTEMPTS),
        "auth_type": auth_type,
        "auth_token": get("webhook_auth_token", ""),
        "auth_username": get("webhook_auth_username", ""),
        "auth_password": get("webhook_auth_password", ""),
        "auth_header_name": get("webhook_auth_header_name", DEFAULT_AUTH_HEADER_NAME).strip()
        or DEFAULT_AUTH_HEADER_NAME,
        "auth_header_value": get("webhook_auth_header_value", ""),
    }
