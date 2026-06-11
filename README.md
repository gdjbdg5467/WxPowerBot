# WxPowerBot — 独立 WeChat UOS 多功能机器人

基于 itchat-uos 协议的多功能微信群机器人，支持群授权管理、网盘资源搜索、Telegram 频道转发、CFTC 图床上传、LSPosed 模块更新追踪、公众号推文推送。

## 功能

- **微信登录** — itchat-uos 协议，QR 码扫码登录，自动重连看门狗
- **群授权系统** — 三级权限：全局管理员 → 群管理员 → 授权用户
- **盘搜** — 搜索夸克/115/百度/UC 网盘资源（对接 PanSou API）
- **TG 转发** — Telegram 频道消息自动转发到微信群
- **CFTC 上传** — 图片/文件上传到 CFTC 图床
- **WeRSS 推文推送** — 微信公众号文章自动推送到群
- **模块更新追踪** — LSPosed Xposed 模块更新监控推送
- **GID 自动迁移** — 处理 itchat 重连后群 ID 变化

## 快速开始

### Docker 部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/gdjbdg5467/WxPowerBot.git
cd WxPowerBot

# 创建数据目录
mkdir -p data/state data/tg_fwd data/lsposed data/werss data/cftc_media

# 配置（编辑 config.json）
vim data/state/config.json

# 启动
docker compose up -d

# 查看日志
docker compose logs -f
```

首次启动后访问 `http://<IP>:8646/` 查看二维码，用微信扫码登录。

### 直接运行

```bash
pip install -r requirements.txt
pip install "itchat-uos==1.5.0.dev0"
mkdir -p data/state
# 编辑 data/state/config.json
python3 main.py
```

## 配置

### 基础配置（data/state/config.json）

所有配置项也可通过 `WXPOWERBOT_<KEY>` 环境变量设置。

```json
{
  "admin_users": "昵称1,昵称2",
  "pansou_api": "http://192.168.1.100:850/api/search",
  "qr_http": true,
  "qr_port": 8646,
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
| `qr_http` | `WXPOWERBOT_QR_HTTP` | 开启 QR 码 HTTP 服务 | `true` |
| `qr_port` | `WXPOWERBOT_QR_PORT` | QR 服务端口 | `8646` |
| `pansou_api` | `WXPOWERBOT_PANSOU_API` | 盘搜 API 地址 | `""` |
| `cftc_url` | `WXPOWERBOT_CFTC_URL` | CFTC 图床地址 | `https://cftc.lliic.com` |
| `cftc_username` | `WXPOWERBOT_CFTC_USERNAME` | CFTC 用户名 | `""` |
| `cftc_password` | `WXPOWERBOT_CFTC_PASSWORD` | CFTC 密码 | `""` |
| `werss_base` | `WXPOWERBOT_WERSS_BASE` | WeRSS API 地址 | `""` |
| `werss_user` | `WXPOWERBOT_WERSS_USER` | WeRSS 用户名 | `""` |
| `werss_pass` | `WXPOWERBOT_WERSS_PASS` | WeRSS 密码 | `""` |

### TG 转发配置（data/tg_fwd/config.json）

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

### LSPosed 配置（data/lsposed/config.json）

```json
{
  "enabled": true,
  "target_groups": ["@@group_id"],
  "github_token": "ghp_xxx",
  "interval_seconds": 1800,
  "custom_repos": [
    {"owner": "mytv-android", "repo": "myDV", "name": "myTV/myDV"}
  ]
}
```

## 群聊命令

在微信群中 `@机器人` + 命令：

| 命令 | 说明 | 权限 |
|------|------|------|
| `开启授权` | 授权本群（首次发送=初始管理员） | 所有人 |
| `关闭授权` | 关闭本群 | 管理员 |
| `授权 昵称` | 授权成员使用盘搜 | 管理员 |
| `取消授权 昵称` | 取消成员权限 | 管理员 |
| `权限列表` | 查看本群权限 | 管理员 |
| `搜索 xxx` | 搜索网盘资源 | 已授权 |
| `开启盘搜`/`关闭盘搜` | 盘搜开关 | 管理员 |
| `开启转发`/`关闭转发` | TG 转发开关 | 管理员 |
| `开启上传`/`关闭上传` | 图床上传开关 | 管理员 |
| `开启更新`/`关闭更新` | 模块更新推送开关 | 管理员 |
| `开启推文`/`关闭推文` | 公众号推文推送开关 | 管理员 |
| `上传` | 上传最新媒体文件到图床 | 已授权 |
| `帮助` | 显示帮助菜单 | 所有人 |

## 文件结构

```
WxPowerBot/
├── bot.py          # 主机器人类（itchat 启动、消息分发、ACL）
├── handlers.py     # 命令处理器 Mixin（ACL、盘搜、TG转发的命令解析）
├── tg_forward.py   # TG 频道 → 微信群转发
├── cftc.py         # CFTC 图床上传
├── lsposed.py      # LSPosed 模块更新追踪
├── werss.py        # WeRSS 公众号推文推送
├── main.py         # 入口
├── config.yaml     # 配置模板
├── Dockerfile      # Docker 构建（含 itchat-uos 补丁）
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 注意事项

- itchat-uos 是逆向协议，建议使用备用微信号
- 群 ID (`@@...`) 可能随重连变化，系统会自动迁移
- 数据保存在 `data/` 目录，请定期备份
- Docker 部署时配置可通过环境变量覆盖，方便 docker-compose 管理
