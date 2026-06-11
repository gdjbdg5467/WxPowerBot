"""
WxPowerBot — WeRSS 公众号文章推送模块

从 WeRSS 服务拉取订阅的微信公众号新文章，推送到已授权且开启推文的微信群。
"""
import json
import logging
import os
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode as _urlencode

logger = logging.getLogger("WxPowerBot.werss")

WERSS_POLL_INTERVAL = 300  # 5 分钟轮询一次


class WeRSSPoller:
    """WeRSS 公众号文章轮询推送器。"""

    def __init__(self, data_dir: Path):
        self.werss_dir = data_dir / "werss"
        self.werss_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.werss_dir / "state.json"

        # 配置：优先从 config.json 读取，其次环境变量
        self.config_file = data_dir / "state" / "config.json"
        self._base_url = ""
        self._username = ""
        self._password = ""
        self._load_config()

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._itchat = None
        self._acl_getter: Optional[Callable[[], Dict[str, Any]]] = None

    def _load_config(self) -> None:
        """从 config.json 或环境变量加载 WeRSS 配置。"""
        config = {}
        try:
            if self.config_file.exists():
                config = json.loads(self.config_file.read_text())
        except Exception:
            pass

        self._base_url = (
            os.getenv("WERSS_BASE") if os.getenv("WERSS_BASE") else None
        ) or config.get("werss_base", "http://localhost:8001/api/v1/wx")
        self._username = (
            os.getenv("WERSS_USER") if os.getenv("WERSS_USER") else None
        ) or config.get("werss_user", "admin")
        self._password = (
            os.getenv("WERSS_PASS") if os.getenv("WERSS_PASS") else None
        ) or config.get("werss_pass", "admin123")

    def reload_config(self) -> None:
        self._load_config()

    def start(self, itchat, acl_getter: Callable[[], Dict[str, Any]]) -> None:
        """启动 WeRSS 轮询线程。"""
        if self._thread and self._thread.is_alive():
            return
        self._itchat = itchat
        self._acl_getter = acl_getter
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="werss-poll",
            daemon=True,
        )
        self._thread.start()
        logger.info("WeRSS: poller started (interval=%ds)", WERSS_POLL_INTERVAL)

    def stop(self) -> None:
        self._stop.set()

    # ── API 调用 ─────────────────────────────────────────────────────

    def _api_login(self) -> Optional[str]:
        """登录 WeRSS 获取 token。"""
        url = f"{self._base_url}/auth/login"
        data = _urlencode({
            "username": self._username,
            "password": self._password,
        }).encode()
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
            return body.get("data", {}).get("access_token")
        except Exception:
            logger.warning("WeRSS: login failed (server unreachable or config missing)")
            return None

    def _api_articles(self, token: str) -> List[Dict[str, Any]]:
        """获取最新文章列表。"""
        url = f"{self._base_url}/articles?page=1&page_size=10"
        try:
            req = urllib.request.Request(
                url, headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
            return body.get("data", {}).get("list", [])
        except Exception:
            logger.warning("WeRSS: fetch articles failed (will retry in %ds)", WERSS_POLL_INTERVAL)
            return []

    # ── 状态管理 ─────────────────────────────────────────────────────

    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                pass
        return {"seen_ids": []}

    def _save_state(self, state: Dict[str, Any]) -> None:
        self.werss_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.state_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        tmp.replace(self.state_file)

    # ── 推送 ─────────────────────────────────────────────────────────

    def _enabled_groups(self) -> List[str]:
        """返回已授权且开启推文的群 ID 列表。"""
        if not self._acl_getter:
            return []
        acl = self._acl_getter()
        groups = acl.get("groups", {})
        return [
            gid for gid, g in groups.items()
            if g.get("authorized") and g.get("werss_enabled", True)
        ]

    def _push_article(self, article: Dict[str, Any]) -> None:
        """推送单篇文章到所有开启推文的群。"""
        mp_name = article.get("mp_name", "未知公众号")
        title = article.get("title", "无标题")
        url = article.get("url", "")
        desc = article.get("description", "")

        msg = f"📰 {mp_name}\n{title}"
        if desc:
            msg += f"\n{desc[:200]}"
        if url:
            msg += f"\n{url}"

        if self._itchat is None:
            return
        for gid in self._enabled_groups():
            try:
                self._itchat.send(msg, toUserName=gid)
                time.sleep(0.3)
            except Exception:
                logger.exception("WeRSS: push to %s failed", gid[:16])
            logger.info("WeRSS: pushed '%s' to %s", title[:30], gid[:16])

    def _push_articles_batch(self, articles: List[Dict[str, Any]]) -> None:
        """将同一公众号的多篇文章合并为一条消息推送。"""
        if not articles:
            return
        mp_name = articles[0].get("mp_name", "未知公众号")
        lines = [f"📰 {mp_name}"]
        for i, art in enumerate(articles, 1):
            title = art.get("title", "无标题")
            url = art.get("url", "")
            desc = art.get("description", "")
            lines.append("")
            lines.append(f"─── {i} ───")
            lines.append(title)
            if desc:
                lines.append(desc[:200])
            if url:
                lines.append(url)
        msg = "\n".join(lines)

        if self._itchat is None:
            return
        for gid in self._enabled_groups():
            try:
                self._itchat.send(msg, toUserName=gid)
                time.sleep(0.3)
            except Exception:
                logger.exception("WeRSS: batch push to %s failed", gid[:16])

    # ── 轮询循环 ─────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        logger.info("WeRSS: poll loop started")
        self.werss_dir.mkdir(parents=True, exist_ok=True)
        seen_ids: set = set()
        state = self._load_state()
        seen_ids = set(state.get("seen_ids", []))

        while not self._stop.is_set():
            try:
                self._load_config()  # 热重载配置
                token = self._api_login()
                if not token:
                    time.sleep(60)
                    continue

                articles = self._api_articles(token)
                if not articles:
                    self._stop.wait(WERSS_POLL_INTERVAL)
                    continue

                # 过滤出未看过的文章
                new_articles = [a for a in articles if a.get("id") not in seen_ids]
                if not new_articles:
                    self._stop.wait(WERSS_POLL_INTERVAL)
                    continue

                fresh_ids = set()
                # 集客之家文章批量推送（合并3条）
                jk_articles = [a for a in new_articles if a.get("mp_name", "") == "集客之家"]
                other_articles = [a for a in new_articles if a.get("mp_name", "") != "集客之家"]

                for a in other_articles:
                    fresh_ids.add(a.get("id", ""))
                    try:
                        self._push_article(a)
                    except Exception:
                        logger.exception("WeRSS: push single failed")

                if jk_articles:
                    jk_articles.sort(key=lambda a: a.get("publish_time", 0) or a.get("id", ""), reverse=True)
                    batch = jk_articles[:3]
                    for a in batch:
                        fresh_ids.add(a.get("id", ""))
                    try:
                        self._push_articles_batch(batch)
                    except Exception:
                        logger.exception("WeRSS: push batch failed")

                seen_ids |= fresh_ids
                # 只保存最近 200 条 ID
                if len(seen_ids) > 200:
                    seen_ids = set(sorted(seen_ids, reverse=True)[:200])

                self._save_state({
                    "seen_ids": sorted(seen_ids),
                    "updated_at": int(time.time()),
                })

            except Exception:
                logger.exception("WeRSS: poll loop error")

            self._stop.wait(WERSS_POLL_INTERVAL)

        logger.info("WeRSS: poll loop stopped")
