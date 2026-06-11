"""WxPowerBot 管理后台 — JWT 认证模块"""

import json
import time
from pathlib import Path
from typing import Optional

import jwt as pyjwt

# 默认密码（首次使用）
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123456"
SECRET_KEY = "wxpowerbot-admin-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 86400  # 24 小时


def _get_config_path(data_dir: Path) -> Path:
    return data_dir / "state" / "config.json"


def _load_admin_password(data_dir: Path) -> str:
    """从配置中读取 admin 密码，不存在则返回默认值。"""
    config_path = _get_config_path(data_dir)
    try:
        if config_path.exists():
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            return cfg.get("admin_password", DEFAULT_PASSWORD)
    except Exception:
        pass
    return DEFAULT_PASSWORD


def _save_admin_password(data_dir: Path, password: str) -> None:
    """保存 admin 密码到配置。"""
    config_path = _get_config_path(data_dir)
    try:
        if config_path.exists():
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
        else:
            cfg = {}
        cfg["admin_password"] = password
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        raise RuntimeError(f"保存密码失败: {e}")


def verify_password(data_dir: Path, username: str, password: str) -> bool:
    """验证用户名密码。"""
    if username != DEFAULT_USERNAME:
        return False
    stored = _load_admin_password(data_dir)
    return password == stored


def create_token(data_dir: Path) -> str:
    """创建 JWT token。"""
    payload = {
        "username": DEFAULT_USERNAME,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS,
    }
    return pyjwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """验证 JWT token，返回 username 或 None。"""
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("username")
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None


def change_password(data_dir: Path, old_pw: str, new_pw: str) -> tuple[bool, str]:
    """修改密码。"""
    if old_pw != _load_admin_password(data_dir):
        return False, "原密码错误"
    if len(new_pw) < 6:
        return False, "新密码长度至少6位"
    _save_admin_password(data_dir, new_pw)
    return True, "密码修改成功"
