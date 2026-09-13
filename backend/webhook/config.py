"""
MinerU Tianshu - Webhook 投递策略配置

回调地址与密钥按 API Key 维度配置（见 auth/routes.py 的 Key 级端点）；
这里只保留全局投递策略（超时、最大重试次数），读取端带默认值兜底。
"""

from auth.system_config import SystemConfig

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_ATTEMPTS = 8


def get_webhook_config() -> dict:
    """读取 webhook 投递策略（含默认值兜底）"""
    raw = SystemConfig().get_all_configs()

    def get_int(key: str, default: int) -> int:
        try:
            return int(raw.get(key) or default)
        except (ValueError, TypeError):
            return default

    return {
        "timeout": get_int("webhook_timeout", DEFAULT_TIMEOUT),
        "max_attempts": get_int("webhook_max_attempts", DEFAULT_MAX_ATTEMPTS),
    }
