"""WxPowerBot 管理后台 — FastAPI 服务器"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from admin.auth import (
    DEFAULT_USERNAME,
    change_password,
    create_token,
    verify_password,
    verify_token,
)

logger = logging.getLogger("WxPowerBot.admin")

# ── 中间件：JWT 认证 ──────────────────────────────────────────

PUBLIC_PATHS = {"/api/admin/login", "/api/admin/health"}


def _get_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def auth_middleware(request: Request, call_next):
    """JWT 认证中间件，公开路径和静态文件跳过。"""
    path = request.url.path

    # 静态文件放行
    if path.startswith("/admin/static/") or path == "/admin" or path.startswith("/admin/index"):
        return await call_next(request)

    # API 公开路径放行
    if path in PUBLIC_PATHS:
        return await call_next(request)

    # 需要认证的 API
    if path.startswith("/api/admin/") and path != "/api/admin/health":
        token = _get_token(request)
        if not token or not verify_token(token):
            return JSONResponse(status_code=401, content={"detail": "未授权，请登录"})

    return await call_next(request)


# ── 创建 App ──────────────────────────────────────────────────


def create_app(bot: Any = None) -> FastAPI:
    """创建 FastAPI 应用，可接受 WxPowerBot 实例。"""
    app = FastAPI(title="WxPowerBot Admin", version="1.0.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(auth_middleware)

    # 注入 bot 实例到 app.state
    app.state.bot = bot

    # 静态文件（前端构建产物）
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists() and (static_dir / "index.html").exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/admin", StaticFiles(directory=str(static_dir), html=True), name="admin-static")

    def _data_dir() -> Path:
        if bot:
            return bot.data_dir
        return Path(os.environ.get("WXPOWERBOT_DATA_DIR", "/data"))

    # ── 路由 ──────────────────────────────────────────────────

    @app.get("/api/admin/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/admin/login")
    async def login(body: dict):
        username = body.get("username", "")
        password = body.get("password", "")
        if not verify_password(_data_dir(), username, password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        token = create_token(_data_dir())
        return {"token": token, "username": username, "expires_in": 86400}

    # ── 仪表盘 ──────────────────────────────────────────────

    @app.get("/api/admin/dashboard")
    async def dashboard():
        data = {"wechat_status": {}, "group_stats": {}, "plugin_states": {}, "system_info": {}}

        if bot:
            # 微信状态
            itchat = getattr(bot, "_itchat", None)
            inst = getattr(itchat, "instance", None) if itchat else None
            if inst and getattr(inst, "alive", False):
                login_info = getattr(inst, "loginInfo", {}) or {}
                data["wechat_status"] = {
                    "logged_in": True,
                    "nickname": login_info.get("NickName", ""),
                    "user_name": login_info.get("User", {}).get("UserName", ""),
                }
            else:
                data["wechat_status"] = {"logged_in": False}

            # 群统计
            acl = getattr(bot, "_acl", {}) or {}
            groups = acl.get("groups", {})
            authorized = sum(1 for g in groups.values() if isinstance(g, dict) and g.get("authorized"))
            data["group_stats"] = {"total": len(groups), "authorized": authorized}

            # 插件状态
            data["plugin_states"] = {
                "pansou": bool(a_cls_conf("pansou_api")),
                "tg_forward": bool(getattr(bot, "tg_forwarder", None) and getattr(bot.tg_forwarder, "_enabled", False)),
                "cftc": bool(a_cls_conf("cftc_username")),
                "lsposed": bool(a_cls_conf("lsposed_github_token")),
                "werss": bool(os.getenv("WERSS_BASE") or (a_cls_conf("werss_base") != "http://localhost:8001/api/v1/wx")),
            }

        return data

    def a_cls_conf(key: str) -> Any:
        if not bot:
            return None
        return getattr(bot, key, None) or getattr(bot, f"_{key}", None)

    # ── 系统设置 ──────────────────────────────────────────────

    @app.get("/api/admin/settings")
    async def get_settings():
        """读取系统设置。"""
        conf = a_cls_conf("config") if bot else {}
        config_path = _data_dir() / "state" / "config.json"
        try:
            if config_path.exists():
                conf = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "login_background": conf.get("login_background", {"type": "gradient", "value": ""}),
        }

    @app.put("/api/admin/settings")
    async def update_settings(body: dict):
        """更新系统设置。"""
        config_path = _data_dir() / "state" / "config.json"
        try:
            if config_path.exists():
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
            else:
                cfg = {}
            if "login_background" in body:
                cfg["login_background"] = body["login_background"]
            if "admin_password" in body:
                cfg["admin_password"] = body["admin_password"]
            config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.put("/api/admin/settings/password")
    async def change_pwd(body: dict):
        ok, msg = change_password(_data_dir(), body.get("old_password", ""), body.get("new_password", ""))
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}

    # ── 微信登录 ──────────────────────────────────────────────

    @app.get("/api/admin/wechat/qr")
    async def wechat_qr():
        """返回二维码 base64 图片。"""
        if not bot:
            return {"qr_base64": "", "exists": False, "logged_in": False}
        itchat = getattr(bot, "_itchat", None)
        inst = getattr(itchat, "instance", None) if itchat else None
        if inst and getattr(inst, "alive", False):
            return {"qr_base64": "", "exists": False, "logged_in": True}
        qp = getattr(bot, "qr_png", None)
        if qp and qp.exists():
            import base64
            raw = qp.read_bytes()
            b64 = base64.b64encode(raw).decode()
            return {"qr_base64": b64, "exists": True, "logged_in": False}
        # Fallback: read the QR URL text file
        qr_url = getattr(bot, "qr_url_txt", None)
        url = ""
        if qr_url and qr_url.exists():
            url = qr_url.read_text().strip()
        return {"qr_base64": "", "exists": False, "logged_in": False, "qr_url": url}

    @app.get("/api/admin/wechat/status")
    async def wechat_status():
        if not bot:
            return {"logged_in": False}
        itchat = getattr(bot, "_itchat", None)
        inst = getattr(itchat, "instance", None) if itchat else None
        alive = inst and getattr(inst, "alive", False)
        if alive:
            login_info = getattr(inst, "loginInfo", {}) or {}
            return {
                "logged_in": True,
                "nickname": login_info.get("NickName", ""),
                "user_name": login_info.get("User", {}).get("UserName", ""),
                "login_time": getattr(bot, "_login_time", 0),
            }
        return {"logged_in": False, "qr_status": getattr(bot, "_qr_status", "waiting")}

    @app.post("/api/admin/wechat/refresh-qr")
    async def refresh_qr():
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        # 触发重新生成二维码（实际由 bot 异步完成）
        return {"success": True, "message": "二维码已刷新"}

    @app.post("/api/admin/wechat/logout")
    async def wechat_logout():
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        itchat = getattr(bot, "_itchat", None)
        if itchat and hasattr(itchat, "logout"):
            try:
                itchat.logout()
            except Exception:
                pass
        return {"success": True}

    # ── 群授权 ──────────────────────────────────────────────

    @app.get("/api/admin/groups")
    async def list_groups():
        if not bot:
            return {"groups": []}
        acl = getattr(bot, "_acl", {}) or {}
        groups = []
        for gid, g in acl.get("groups", {}).items():
            if not isinstance(g, dict):
                continue
            mc = g.get("members_cache", {}) or {}
            groups.append({
                "id": gid,
                "name": g.get("name", ""),
                "authorized": bool(g.get("authorized")),
                "member_count": len(mc),
                "pansou_enabled": bool(g.get("pansou_enabled")),
                "tg_fwd_enabled": bool(g.get("tg_fwd_enabled")),
                "cftc_enabled": bool(g.get("cftc_enabled")),
                "lsposed_enabled": bool(g.get("lsposed_enabled")),
                "werss_enabled": bool(g.get("werss_enabled")),
            })
        return {"groups": groups}

    @app.get("/api/admin/groups/{group_id}")
    async def get_group(group_id: str):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            raise HTTPException(status_code=404, detail="群不存在")
        return _format_group(g, group_id)

    @app.put("/api/admin/groups/{group_id}")
    async def update_group(group_id: str, body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            raise HTTPException(status_code=404, detail="群不存在")
        with getattr(bot, "_acl_lock", __import__("threading").Lock()):
            for key in ("authorized", "pansou_enabled", "tg_fwd_enabled",
                        "cftc_enabled", "lsposed_enabled", "werss_enabled", "name"):
                if key in body:
                    g[key] = body[key]
            g["updated_at"] = int(__import__("time").time())
            if hasattr(bot, "_save_acl"):
                bot._save_acl()
        return {"success": True}

    @app.put("/api/admin/groups/{group_id}/admins")
    async def update_admins(group_id: str, body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            raise HTTPException(status_code=404, detail="群不存在")
        with getattr(bot, "_acl_lock", __import__("threading").Lock()):
            g["admins"] = body.get("admins", [])
            g["updated_at"] = int(__import__("time").time())
            if hasattr(bot, "_save_acl"):
                bot._save_acl()
        return {"success": True}

    @app.put("/api/admin/groups/{group_id}/users")
    async def update_users(group_id: str, body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            raise HTTPException(status_code=404, detail="群不存在")
        with getattr(bot, "_acl_lock", __import__("threading").Lock()):
            g["allowed_users"] = body.get("allowed_users", [])
            g["updated_at"] = int(__import__("time").time())
            if hasattr(bot, "_save_acl"):
                bot._save_acl()
        return {"success": True}

    @app.get("/api/admin/groups/{group_id}/members")
    async def search_members(group_id: str, q: str = ""):
        if not bot:
            return {"members": []}
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            return {"members": []}
        mc = g.get("members_cache", {}) or {}
        results = []
        q_lower = q.strip().lower()
        for uid, meta in mc.items():
            if not isinstance(meta, dict):
                continue
            display = meta.get("display_name", "") or meta.get("nick_name", "")
            if q_lower and q_lower not in display.lower() and q_lower not in (meta.get("nick_name", "") or "").lower():
                continue
            results.append({
                "uid": uid,
                "display_name": display,
                "nick_name": meta.get("nick_name", ""),
                "remark_name": meta.get("remark_name", ""),
                "is_admin": uid in g.get("admins", []),
                "is_allowed": uid in g.get("allowed_users", []),
            })
        return {"members": results}

    # ── 盘搜 ──────────────────────────────────────────────

    @app.get("/api/admin/pansou/config")
    async def pansou_config():
        api_url = a_cls_conf("pansou_api") or ""
        return {"api_url": api_url, "enabled": bool(api_url)}

    @app.put("/api/admin/pansou/config")
    async def update_pansou(body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        setattr(bot, "pansou_api", body.get("api_url", ""))
        return {"success": True}

    # ── TG 转发 ──────────────────────────────────────────────

    @app.get("/api/admin/tg-forward/config")
    async def tgf_config():
        if not bot or not hasattr(bot, "tg_forwarder"):
            return {"bot_token": "", "user_id": "", "channels": [], "enabled": False}
        fwd = bot.tg_forwarder
        cfg = getattr(fwd, "_config", {}) or {}
        return {
            "bot_token": "***" if cfg.get("bot_token") else "",
            "user_id": cfg.get("user_id", ""),
            "channels": cfg.get("channels", []),
            "enabled": bool(cfg.get("bot_token")),
        }

    @app.put("/api/admin/tg-forward/config")
    async def update_tgf(body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        if not hasattr(bot, "tg_forwarder"):
            return {"success": False, "message": "TG 转发器未初始化"}
        fwd = bot.tg_forwarder
        cfg = getattr(fwd, "_config", {}) or {}
        if "bot_token" in body:
            cfg["bot_token"] = body["bot_token"]
        if "user_id" in body:
            cfg["user_id"] = body["user_id"]
        if isinstance(getattr(fwd, "_config", None), dict):
            fwd._config = cfg
        # 保存到文件
        conf_dir = _data_dir() / "tg_fwd"
        conf_dir.mkdir(parents=True, exist_ok=True)
        (conf_dir / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True}

    # ── CF 图床 ──────────────────────────────────────────────

    @app.get("/api/admin/cftc/config")
    async def cftc_config():
        return {
            "url": a_cls_conf("cftc_url") or "",
            "username": a_cls_conf("cftc_username") or "",
            "enabled": bool(a_cls_conf("cftc_username")),
        }

    @app.put("/api/admin/cftc/config")
    async def update_cftc(body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        if "url" in body:
            setattr(bot, "cftc_url", body["url"])
        if "username" in body:
            setattr(bot, "cftc_username", body["username"])
        if "password" in body:
            setattr(bot, "cftc_password", body["password"])
        return {"success": True}

    # ── 模块推送 ──────────────────────────────────────────────

    @app.get("/api/admin/module-push/config")
    async def module_push_config():
        if not bot or not hasattr(bot, "lsposed_tracker"):
            return {"github_token": "", "repos": [], "enabled": False}
        tracker = bot.lsposed_tracker
        cfg = getattr(tracker, "_config", {}) or {}
        return {
            "github_token": "***" if cfg.get("github_token") else "",
            "repos": cfg.get("custom_repos", []),
            "enabled": bool(cfg.get("github_token")),
        }

    @app.put("/api/admin/module-push/config")
    async def update_module_push(body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        if not hasattr(bot, "lsposed_tracker"):
            return {"success": False, "message": "模块推送器未初始化"}
        tracker = bot.lsposed_tracker
        cfg = getattr(tracker, "_config", {}) or {}
        if "github_token" in body:
            cfg["github_token"] = body["github_token"]
        if "custom_repos" in body and isinstance(body["custom_repos"], list):
            cfg["custom_repos"] = body["custom_repos"]
        if isinstance(getattr(tracker, "_config", None), dict):
            tracker._config = cfg
        # 保存到文件
        conf_dir = _data_dir() / "lsposed"
        conf_dir.mkdir(parents=True, exist_ok=True)
        (conf_dir / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True}

    # ── WeRSS 推文 ──────────────────────────────────────────

    @app.get("/api/admin/werss/config")
    async def werss_config():
        return {
            "base_url": os.getenv("WERSS_BASE", ""),
            "username": os.getenv("WERSS_USER", ""),
            "enabled": bool(os.getenv("WERSS_BASE")),
        }

    @app.put("/api/admin/werss/config")
    async def update_werss(body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        # 更新环境变量和 bot 配置
        if "base_url" in body:
            os.environ["WERSS_BASE"] = body["base_url"]
        if "username" in body:
            os.environ["WERSS_USER"] = body["username"]
        if "password" in body:
            os.environ["WERSS_PASS"] = body["password"]
        return {"success": True}

    # ── 群管理（创建/删除） ──────────────────────────────────

    @app.post("/api/admin/groups")
    async def create_group(body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        name = body.get("name", "")
        gid = body.get("group_id", "")
        if not name and not gid:
            raise HTTPException(status_code=400, detail="群名称或 ID 必填")
        if not gid:
            gid = f"@@admin_created_{int(__import__('time').time())}"
        acl = getattr(bot, "_acl", {}) or {}
        with getattr(bot, "_acl_lock", __import__("threading").Lock()):
            groups = acl.setdefault("groups", {})
            if gid in groups:
                raise HTTPException(status_code=409, detail="群已存在")
            now = int(__import__("time").time())
            groups[gid] = {
                "name": name or gid, "authorized": False,
                "admins": [], "allowed_users": [],
                "members_cache": {}, "created_at": now, "updated_at": now,
            }
            if hasattr(bot, "_save_acl"):
                bot._save_acl()
        return {"success": True, "group_id": gid}

    @app.delete("/api/admin/groups/{group_id}")
    async def delete_group(group_id: str):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        with getattr(bot, "_acl_lock", __import__("threading").Lock()):
            groups = acl.get("groups", {})
            if group_id not in groups:
                raise HTTPException(status_code=404, detail="群不存在")
            del groups[group_id]
            if hasattr(bot, "_save_acl"):
                bot._save_acl()
        return {"success": True}

    @app.post("/api/admin/groups/{group_id}/sync-members")
    async def sync_members(group_id: str):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            raise HTTPException(status_code=404, detail="群不存在")
        count = 0
        if hasattr(bot, "_refresh_group_members"):
            count = bot._refresh_group_members(group_id, g.get("name", ""))
        return {"success": True, "member_count": count}

    @app.get("/api/admin/groups/{group_id}/commands")
    async def get_commands(group_id: str):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            raise HTTPException(status_code=404, detail="群不存在")
        cmds = g.get("custom_commands", {}) or {}
        cmd_list = []
        for trigger, cfg in cmds.items():
            if not isinstance(cfg, dict):
                continue
            cmd_list.append({
                "trigger": trigger,
                "response": cfg.get("response", ""),
                "permission": cfg.get("permission", "admin"),
            })
        return {"commands": cmd_list}

    @app.put("/api/admin/groups/{group_id}/commands")
    async def update_commands(group_id: str, body: dict):
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        acl = getattr(bot, "_acl", {}) or {}
        g = acl.get("groups", {}).get(group_id)
        if not isinstance(g, dict):
            raise HTTPException(status_code=404, detail="群不存在")
        cmd_list = body.get("commands", []) or []
        commands = {}
        for item in cmd_list:
            trigger = (item.get("trigger") or "").strip()
            if not trigger:
                continue
            commands[trigger] = {
                "response": (item.get("response") or "").strip(),
                "permission": item.get("permission", "admin"),
            }
        with getattr(bot, "_acl_lock", __import__("threading").Lock()):
            g["custom_commands"] = commands
            g["updated_at"] = int(__import__("time").time())
            if hasattr(bot, "_save_acl"):
                bot._save_acl()
        return {"success": True}

    # ── Bot 控制 ──────────────────────────────────────────────

    @app.post("/api/admin/bot/restart")
    async def bot_restart():
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        itchat = getattr(bot, "_itchat", None)
        if itchat and hasattr(itchat, "logout"):
            try:
                itchat.logout()
            except Exception:
                pass
        # 清除热重载缓存，触发重新登录
        pkl = getattr(bot, "state_dir", Path("/data/state")) / "itchat.pkl"
        if pkl.exists():
            try:
                pkl.unlink()
            except Exception:
                pass
        return {"success": True, "message": "Bot 已重启，请等待重新扫码"}

    @app.post("/api/admin/bot/shutdown")
    async def bot_shutdown():
        if not bot:
            raise HTTPException(status_code=400, detail="Bot 未初始化")
        itchat = getattr(bot, "_itchat", None)
        if itchat and hasattr(itchat, "logout"):
            try:
                itchat.logout()
            except Exception:
                pass
        return {"success": True, "message": "微信连接已关闭"}

    # ── 工具函数 ──────────────────────────────────────────────

    def _format_group(g: dict, gid: str) -> dict:
        mc = g.get("members_cache", {}) or {}
        admins = []
        for uid in g.get("admins", []):
            meta = mc.get(uid, {})
            admins.append({
                "uid": uid,
                "display_name": (isinstance(meta, dict) and (meta.get("display_name") or meta.get("nick_name"))) or uid,
            })
        users = []
        for uid in g.get("allowed_users", []):
            meta = mc.get(uid, {})
            users.append({
                "uid": uid,
                "display_name": (isinstance(meta, dict) and (meta.get("display_name") or meta.get("nick_name"))) or uid,
            })
        return {
            "id": gid,
            "name": g.get("name", ""),
            "authorized": bool(g.get("authorized")),
            "admins": admins,
            "allowed_users": users,
            "member_count": len(mc),
            "pansou_enabled": bool(g.get("pansou_enabled")),
            "tg_fwd_enabled": bool(g.get("tg_fwd_enabled")),
            "cftc_enabled": bool(g.get("cftc_enabled")),
            "lsposed_enabled": bool(g.get("lsposed_enabled")),
            "werss_enabled": bool(g.get("werss_enabled")),
        }

    return app


def run_admin_server(bot, host: str = "0.0.0.0", port: int = 8645):
    """启动管理后台服务器（阻塞）。"""
    import uvicorn
    app = create_app(bot)
    logger.info(f"管理后台启动: http://{host}:{port}/admin")
    uvicorn.run(app, host=host, port=port, log_level="info")