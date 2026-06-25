# WxPowerBot — 独立 WeChat UOS 多功能机器人

基于 itchat-uos 协议的多功能微信群机器人，支持群授权管理、**网盘资源搜索**、**Telegram 频道→微信群转发**、**抖音/TikTok视频解析**、CFTC 图床上传、LSPosed 模块更新追踪、公众号推文推送。

> ⚠️ **重要说明：微信登录限制**
> 新注册的微信号（约2017年后）可能被限制使用网页/桌面协议（错误码 1203），建议使用老微信号。
> 管理后台提供扫码二维码，无需额外暴露端口。

## 功能

- **微信登录** — itchat-uos 协议，通过管理后台扫码登录，看门狗自动重连
- **管理后台** — FastAPI + Vue3 + Arco Design 的 Web 管理界面（端口 8645）
- **群授权系统** — 三级权限：全局管理员 → 群管理员 → 授权用户
- **盘搜（PanSou）** — 搜索夸克/115/百度/UC 网盘资源（对接 PanSou API）
- **TG 转发** — Telegram 频道消息自动转发到微信群（支持图文/视频/文件）
- **抖音解析** — 检测群内抖音/TikTok分享链接，自动解析无水印视频
- **CFTC 上传** — 图片/文件上传到 CFTC 图床
- **WeRSS 推文推送** — 微信公众号文章自动推送到群
- **LSPosed 模块更新追踪** — Xposed 模块更新监控推送
- **GID 自动迁移** — 处理 itchat 重连后群 ID 变化

## 快速开始

### Docker 部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/gdjbdg5467/WxPowerBot.git
cd WxPowerBot

# 创建数据目录
mkdir -p data/state data/tg_fwd data/lsposed/data/werss data/cftc_media

# 启动
docker compose up -d

# 查看日志
docker compose logs -f
```

首次启动后访问 `http://<IP>:8645/admin` 进入管理后台，默认账号 `admin/admin123456`。

在 **微信登录** 页面扫码登录微信。

### 直接运行

```bash
pip install -r requirements.txt
pip install "itchat-uos==1.4.1"
mkdir -p data/state

# 编辑 data/state/config.json
python3 main.py
```

## 管理后台

访问 `http://<IP>:8645/admin`，包含以下页面：

| 页面 | 功能 |
|------|------|
| **仪表盘** | 微信登录状态监控 |
| **微信登录** | 扫码登录、二维码刷新、退出 |
| **群授权** | 管理群组权限、管理员、成员 |
| **盘搜配置** | PanSou API 地址配置 |
| **TG转发配置** | Bot Token + 频道 + 目标群配置 |
| **CF图床配置** | CFTC 图床账号配置 |
| **模块推送配置** | LSPosed 模块更新监控 |
| **公众号推文** | WeRSS 推文推送配置 |
| **抖音解析配置** | 抖音API地址 + Cookie 配置 |
| **系统设置** | 登录页背景等 |

## 配置

### 基础配置（data/state/config.json）

所有配置项也可通过 `WXPOWERBOT_<KEY>` 环境变量设置。

```json
{
  "admin_users": "昵称1,昵称2",
  "pansou_api": "http://192.168.1.100:850/api/search",
  "respond_to_dms": false
}
```

完整配置项：

| 配置项 | 环境变量 | 说明 | 默认值 |
|--------|----------|------|--------|
| `admin_users` | `WXPOWERBOT_ADMIN_USERS` | 全局管理员昵称（逗号分隔） | `""` |
| `allowed_groups` | `WXPOWERBOT_ALLOWED_GROUPS` | 允许的群组（逗号分隔，留空=所有群） | `""` |
| `allowed_users` | `WXPOWERBOT_ALLOWED_USERS` | 允许的用户（逗号分隔） | `""` |
| `respond_to_dms` | `WXPOWERBOT_RESPOND_TO_DMS` | 是否响应私聊 | `false` |
| `pansou_api` | `WXPOWERBOT_PANSOU_API` | 盘搜 API 地址 | `""` |
| `cftc_url` | `WXPOWERBOT_CFTC_URL` | CFTC 图床地址 | `https://cftc.lliic.com` |
| `cftc_username` | `WXPOWERBOT_CFTC_USERNAME` | CFTC 用户名 | `""` |
| `cftc_password` | `WXPOWERBOT_CFTC_PASSWORD` | CFTC 密码 | `""` |
| `werss_base` | `WXPOWERBOT_WERSS_BASE` | WeRSS API 地址 | `""` |
| `werss_user` | `WXPOWERBOT_WERSS_USER` | WeRSS 用户名 | `""` |
| `werss_pass` | `WXPOWERBOT_WERSS_PASS` | WeRSS 密码 | `""` |

### TG 转发配置

通过管理后台 **TG转发配置** 页面设置，或直接编辑 `data/tg_fwd/config.json`：

```json
{
  "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "forward_rules": [
    {
      "tg_channel": "@channel_name",
      "wechat_groups": ["@@wechat_group_id1", "@@wechat_group_id2"]
    }
  ]
}
```

### 抖音解析配置

通过管理后台 **抖音解析配置** 页面设置：

1. 部署抖音解析 API（推荐 `evil0ctal/douyin_tiktok_download_api`）
2. 在管理后台填入 API 地址和 Cookie（从浏览器 douyin.com 获取）
3. 在群内开启「开启抖音解析」命令

## 群聊命令

在微信群中 `@机器人` + 命令：

| 命令 | 说明 | 权限 |
|------|------|------|
| `授权此群聊` | 授权本群（首次发送=初始管理员） | 所有人 |
| `关闭授权` | 关闭本群 | 管理员 |
| `授权@昵称` | 授权成员使用盘搜 | 管理员 |
| `取消授权@昵称` | 取消成员权限 | 管理员 |
| `权限列表` | 查看本群权限 | 管理员 |
| `搜索 xxx` | 搜索网盘资源 | 已授权 |
| `开启盘搜`/`关闭盘搜` | 盘搜开关 | 管理员 |
| `开启转发`/`关闭转发` | TG 转发开关 | 管理员 |
| `开启上传`/`关闭上传` | 图床上传开关 | 管理员 |
| `开启更新`/`关闭更新` | 模块更新推送开关 | 管理员 |
| `开启推文`/`关闭推文` | 公众号推文推送开关 | 管理员 |
| `开启抖音解析`/`关闭抖音解析` | 抖音链接解析开关 | 管理员 |
| `上传` | 上传最新媒体文件到图床 | 已授权 |
| `帮助` | 显示帮助菜单 | 所有人 |

## 文件结构

```
WxPowerBot/
├── bot.py           # 主机器人类（itchat 启动、消息分发、ACL）
├── handlers.py      # 命令处理器 Mixin（ACL、盘搜、TG转发的命令解析）
├── tg_forward.py    # TG 频道 → 微信群转发
├── douyin.py        # 抖音/TikTok 视频链接解析
├── cftc.py          # CFTC 图床上传
├── lsposed.py       # LSPosed 模块更新追踪
├── werss.py         # WeRSS 公众号推文推送
├── main.py          # 入口
├── config.yaml      # 配置模板
├── Dockerfile       # Docker 构建
├── docker-compose.yml
├── requirements.txt
├── admin/           # 管理后台（FastAPI + Vue3）
│   ├── server.py    # API 路由
│   ├── static/      # 前端编译产物
│   └── templates/   # 管理页面模板
└── README.md
```

## 注意事项

- itchat-uos 是逆向协议，部分微信号可能受限（错误码 1203）
- 群 ID (`@@...`) 可能随重连变化，系统会自动迁移
- 数据保存在 `data/` 目录，请定期备份
- Docker 部署时配置可通过环境变量覆盖
- 管理后台默认密码 `admin123456`，请及时修改