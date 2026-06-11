#!/usr/bin/env python3
"""WxPowerBot — 独立 WeChat UOS 多功能机器人入口。"""

import os
import sys
import threading

# 确保在项目目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from bot import WxPowerBot
from admin.server import run_admin_server


def main():
    data_dir = os.environ.get("WXPOWERBOT_DATA_DIR", "/data")
    bot = WxPowerBot(data_dir=data_dir)

    # 启动管理后台 (独立线程)
    admin_port = int(os.environ.get("WXPOWERBOT_ADMIN_PORT", "8645"))
    admin_thread = threading.Thread(
        target=run_admin_server,
        args=(bot,),
        kwargs={"host": "0.0.0.0", "port": admin_port},
        name="admin-server",
        daemon=True,
    )
    admin_thread.start()

    # 启动主机器人 (阻塞)
    bot.start()


if __name__ == "__main__":
    main()