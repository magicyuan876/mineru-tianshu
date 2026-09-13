"""
MinerU Tianshu - Webhook 投递

webhook_deliveries 表 CRUD、SSRF 校验与带签名的 HTTP 投递。
与任务库共用同一个 SQLite 文件（DATABASE_PATH），PRAGMA 与 task_db._get_conn 保持一致。
"""

import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import socket
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

# 单次错误信息入库上限，避免超长堆栈撑爆记录
MAX_ERROR_LENGTH = 500

# 重试退避上限（秒）：30s 起指数翻倍，封顶 30 分钟
MAX_RETRY_DELAY = 1800
BASE_RETRY_DELAY = 30


def _now_str() -> str:
    """UTC 时间字符串，与 SQLite CURRENT_TIMESTAMP 格式一致，可直接做字符串比较"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _get_db_path() -> str:
    project_root = Path(__file__).parent.parent.parent
    default_db = project_root / "data" / "db" / "mineru_tianshu.db"
    db_path = os.getenv("DATABASE_PATH", str(default_db))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return str(Path(db_path).resolve())


def _get_conn():
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            delivery_id TEXT PRIMARY KEY,
            task_id TEXT,
            event TEXT NOT NULL,
            url TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            next_retry_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            delivered_at TEXT
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_pending ON webhook_deliveries (status, next_retry_at)"
    )


def validate_webhook_url(url: str) -> None:
    """投递目标校验（SSRF 防护）：仅允许 http/https，且解析出的所有 IP 必须为公网地址

    注意：校验通过后 httpx 建连时会再次进行 DNS 解析，仍存在 DNS 重绑定的残余风险，
    已通过"一次性解析校验 + follow_redirects=False"尽量收敛。
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a hostname")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addr_infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ValueError("Failed to resolve hostname") from e
    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("URL resolves to a non-public address")


def build_auth_headers(auth: dict) -> dict:
    """按 auth_type 构造出站鉴权头；none 或配置不完整时不附加任何头

    api_key 的自定义头名只放行字母数字和连字符，防止注入非法头名。
    """
    if not auth:
        return {}
    auth_type = auth.get("auth_type", "none")
    if auth_type == "bearer":
        token = (auth.get("auth_token") or "").strip()
        return {"Authorization": f"Bearer {token}"} if token else {}
    if auth_type == "basic":
        username = auth.get("auth_username") or ""
        password = auth.get("auth_password") or ""
        if not (username or password):
            return {}
        encoded = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        return {"Authorization": f"Basic {encoded}"}
    if auth_type == "api_key":
        name = (auth.get("auth_header_name") or "").strip()
        value = (auth.get("auth_header_value") or "").strip()
        if not value or not re.fullmatch(r"[A-Za-z0-9-]+", name):
            return {}
        return {name: value}
    return {}


def post_webhook(url: str, payload: dict, secret: str = "", timeout: int = 10, auth: dict = None) -> int:
    """同步投递一条 webhook，返回 HTTP 状态码；网络错误抛异常由调用方处理"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    timestamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-Tianshu-Event": payload.get("event", ""),
        "X-Tianshu-Delivery": payload.get("delivery_id", ""),
        "X-Tianshu-Timestamp": timestamp,
        **build_auth_headers(auth),
    }
    # 未配置密钥时省略签名头，签名串为 "{timestamp}.{body}"
    if secret:
        sig = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + body, hashlib.sha256).hexdigest()
        headers["X-Tianshu-Signature"] = f"sha256={sig}"
    # trust_env=False：不走环境/系统代理，代理会自行解析 DNS，使 SSRF 校验失效
    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        resp = client.post(url, content=body, headers=headers)
    return resp.status_code


def insert_delivery(task_id: Optional[str], event: str, url: str, payload: dict) -> str:
    """写入一条待投递记录，立即到期等待调度器扫描"""
    delivery_id = uuid.uuid4().hex
    payload = {**payload, "delivery_id": delivery_id}
    conn = _get_conn()
    try:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO webhook_deliveries
                (delivery_id, task_id, event, url, payload, status, attempts, next_retry_at, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?)
            """,
            (delivery_id, task_id, event, url, json.dumps(payload, ensure_ascii=False), _now_str(), _now_str()),
        )
        conn.commit()
    finally:
        conn.close()
    return delivery_id


def fetch_due_deliveries(limit: int = 50) -> list:
    conn = _get_conn()
    try:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT * FROM webhook_deliveries
            WHERE status = 'pending' AND next_retry_at <= ?
            ORDER BY created_at LIMIT ?
            """,
            (_now_str(), limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_delivered(delivery_id: str):
    conn = _get_conn()
    try:
        _ensure_table(conn)
        conn.execute(
            "UPDATE webhook_deliveries SET status = 'delivered', delivered_at = ? WHERE delivery_id = ?",
            (_now_str(), delivery_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_retry_or_dead(delivery_id: str, attempts: int, max_attempts: int, error: str):
    """失败：attempts 达到上限置 dead，否则指数退避等待下一次重试"""
    error = (error or "")[:MAX_ERROR_LENGTH]
    if attempts >= max_attempts:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            conn.execute(
                "UPDATE webhook_deliveries SET status = 'dead', attempts = ?, last_error = ? WHERE delivery_id = ?",
                (attempts, error, delivery_id),
            )
            conn.commit()
        finally:
            conn.close()
        return
    delay = min(BASE_RETRY_DELAY * (2**attempts), MAX_RETRY_DELAY)
    next_retry = (datetime.now(timezone.utc) + timedelta(seconds=delay)).strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    try:
        _ensure_table(conn)
        conn.execute(
            """
            UPDATE webhook_deliveries
            SET attempts = ?, last_error = ?, next_retry_at = ?
            WHERE delivery_id = ?
            """,
            (attempts, error, next_retry, delivery_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_dead(delivery_id: str, error: str):
    """直接置死（如 SSRF 校验失败，重试无意义）"""
    conn = _get_conn()
    try:
        _ensure_table(conn)
        conn.execute(
            "UPDATE webhook_deliveries SET status = 'dead', last_error = ? WHERE delivery_id = ?",
            ((error or "")[:MAX_ERROR_LENGTH], delivery_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_deliveries(page: int = 1, page_size: int = 20, status_filter: Optional[str] = None):
    """分页查询投递记录（最新的在前）"""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    conn = _get_conn()
    try:
        _ensure_table(conn)
        where = "WHERE status = ?" if status_filter else ""
        params = (status_filter,) if status_filter else ()
        total = conn.execute(f"SELECT COUNT(*) AS c FROM webhook_deliveries {where}", params).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT delivery_id, task_id, event, url, status, attempts, last_error, created_at, delivered_at
            FROM webhook_deliveries {where}
            ORDER BY created_at DESC LIMIT ? OFFSET ?
            """,
            (*params, page_size, (page - 1) * page_size),
        ).fetchall()
        return [dict(r) for r in rows], total
    finally:
        conn.close()
