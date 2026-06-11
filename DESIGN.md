# WxPowerBot 管理后台设计文档

## 一、技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 前端框架 | **Vue 3** + **Vite** | 与参考页面 WeRss 一致，轻量高效 |
| UI 组件库 | **Arco Design (ByteDance)** | 参考页面使用，风格统一 |
| 后端框架 | **FastAPI** (Python 3.11) | 与现有 bot 同语言，可直接共享数据 |
| 认证 | JWT Token | 无状态，前端存储在 localStorage |
| 数据库 | **文件 JSON**（沿用现有 `data/state/config.json` + `data/state/acl.json`） | 无需额外数据库 |
| 部署 | Docker 内嵌，与 bot 同进程启动 | 不增加额外容器 |

---

## 二、页面结构总览

```
/admin
├── /login               # 登录页面
├── /dashboard            # 仪表盘首页
├── /wechat               # 微信登录管理
├── /groups               # 群授权系统
├── /pansou               # 盘搜配置
├── /tg-forward           # TG 转发配置
├── /cftc                 # CF 图床配置
├── /module-push          # 模块推送配置
├── /werss                # 公众号推文配置
└── /settings             # 系统设置
```

---

## 三、详细页面设计

### 3.1 登录页面 `/login`

**布局：** 左 55% 介绍区 + 右 45% 登录卡片（参考 WeRss 页面）

**左区 - 介绍区：**
- 大标题：`WxPowerBot 管理后台`
- 副标题介绍文字
- 功能特性列表（微信扫码登录、群授权管理、插件配置）
- 底部 GitHub 链接

**右区 - 登录表单：**
- WxPowerBot Logo（顶部）
- 账号输入框（默认 placeholder：`admin`）
- 密码输入框（默认 placeholder：`••••••••`，类型 password）
- 登录按钮（蓝色渐变）
- 登录底部显示版本号

**自定义背景设置（系统设置页面配置）：**
```typescript
interface LoginBackground {
  type: 'gradient' | 'image' | 'color' | 'api';
  value: string; // 渐变 CSS / 图片URL / 颜色值 / API URL
}
```
- `gradient`：默认蓝紫渐变 `linear-gradient(135deg, rgba(59,130,246,.95), rgba(168,85,247,.9))`
- `image`：自定义图片 URL → 设为 `background-image: url(...)`
- `color`：纯色背景
- `api`：调用外部 API 返回图片 URL（定时刷新）

**API：**
```
POST /api/admin/login
Body: { "username": "admin", "password": "admin123456" }
Response: { "token": "jwt...", "expires_in": 86400 }
```

---

### 3.2 仪表盘 `/dashboard`

**卡片布局（4 行）：**

| 卡片 | 内容 |
|------|------|
| **微信状态** | 登录状态（已登录/未登录/二维码待扫）、微信号昵称、头像、上次登录时间 |
| **群聊概览** | 已授权群数量、总群成员数 |
| **插件状态** | 各插件启用/禁用状态（盘搜/TG转发/CF图床/模块推送/推文） |
| **系统信息** | 运行时间、Python 版本、Docker 状态、内存使用 |

**快捷操作区：**
- 一键重启机器人
- 一键退出微信登录
- 清除所有缓存

**底部：** 最近操作日志（5 条）

**API：**
```
GET /api/admin/dashboard
Headers: Authorization: Bearer <token>
Response: { "wechat_status": {...}, "group_stats": {...},
            "plugin_states": {...}, "system_info": {...},
            "recent_logs": [...] }
```

---

### 3.3 微信登录管理 `/wechat`

**页面布局：** 居中卡片

**未登录状态：**
- 大号二维码（每 30 秒自动刷新，页面倒计时显示）
- 二维码下方文字提示：
  ```
  ⚠️ 风险提示
  使用 itchat-uos 协议存在封号风险，建议使用备用微信号。
  二维码每 30 秒自动刷新，超时请重新扫码。
  ```
- 状态指示：`等待扫码` / `已扫码，请在手机上确认` / `登录成功`
- 刷新按钮（手动刷新二维码）
- 状态历史记录（下方表格：时间、状态、IP）

**已登录状态：**
- 微信头像 + 昵称
- 登录时长
- 退出登录按钮（红色，需确认弹窗）
- 重新扫码按钮（蓝色）

**API：**
```
GET  /api/admin/wechat/qr          → { "qr_base64": "...", "expires_in": 30, "status": "waiting" }
GET  /api/admin/wechat/status      → { "logged_in": true/false, "nickname": "...", "avatar": "...", "login_time": 12345 }
POST /api/admin/wechat/logout      → { "success": true }
POST /api/admin/wechat/refresh-qr  → { "qr_base64": "...", "expires_in": 30 }
```

---

### 3.4 群授权系统 `/groups`

**页面布局：** 左侧群列表 + 右侧详情面板

**左侧 - 已授权群列表：**
- 展开卡片，每个群显示：群名称、ID（截断）、成员数、授权状态开关
- 搜索/过滤框
- 添加群按钮（弹窗输入群名称，自动匹配）

**右侧 - 选中群的详情面板，Tab 切页：**

**Tab 1: 基础信息**
- 群名称（可编辑）
- 群 ID（只读）
- 授权开关
- 各插件开关（盘搜/TG转发/CF图床/模块推送/推文），每个开关灰色标注「未配置则不启用」
- 同步成员按钮

**Tab 2: 管理员管理**
- 当前管理员列表（卡片式，显示昵称 + 头像）
- 添加管理员输入框：输入群成员昵称 → 自动从 `members_cache` 匹配 ID
- 删除管理员（带确认）

**Tab 3: 授权成员管理**
- 当前授权成员列表
- 添加成员输入框：输入群成员昵称 → 自动匹配 ID
- 删除成员

**Tab 4: 群聊命令配置**
- 每条命令可自定义文本（表格形式）
  | 默认命令 | 自定义命令 | 说明 |
  |---------|-----------|------|
  | 开启授权 | [可编辑] | 授权本群 |
  | 关闭授权 | [可编辑] | 关闭授权 |
  | 授权 [昵称] | [可编辑] | 添加管理员 |
  | 取消授权 [昵称] | [可编辑] | 移除管理员 |
  | 搜索 [关键词] | [可编辑] | 盘搜 |
  | 开启转发 | [可编辑] | TG转发开关 |
  | ... | ... | ... |
- 「恢复默认」按钮

**API：**
```
GET    /api/admin/groups                     → { "groups": [{id, name, member_count, authorized, ...}] }
GET    /api/admin/groups/:id                 → { ...group_detail }
PUT    /api/admin/groups/:id                 → update group settings
PUT    /api/admin/groups/:id/admins          → { "admins": ["uid1", "uid2"] }
PUT    /api/admin/groups/:id/users           → { "allowed_users": ["uid1"] }
PUT    /api/admin/groups/:id/commands        → { "commands": { "enable_auth": "开启授权", ... } }
POST   /api/admin/groups/:id/sync-members    → { "count": 42 }
DELETE /api/admin/groups/:id                 → delete group
POST   /api/admin/groups                     → { "name": "群名称", "group_id": "@@" }
```

---

### 3.5 盘搜配置 `/pansou`

**页面布局：** 设置表单 + 权限管理 Tab

**设置区 - 盘搜地址：**
- 填写盘搜 API 地址（支持内网 IP 和自定义网址）
  - 文本框：`http://192.168.1.168:850/api/search`
  - 测试连接按钮（发一条测试请求）
- 状态指示：`已连接 ✔` / `连接失败 ✘`
- 开关：启用/禁用盘搜

> ⚠️ 勾选提示：未填写盘搜地址则所有群不启用该功能

**权限管理（与 3.4 复用组件）：**
- 选择要管理的群（下拉搜索框）
- 该群的管理员列表（自动匹配）
- 添加/移除管理员
- 添加/移除授权使用成员
- 添加/删除群（多群管理）

**群聊配置：**
- 可给不同群独立开关盘搜功能（开关列表）

**API：**
```
GET  /api/admin/pansou/config        → { "api_url": "...", "enabled": true/false, "status": "connected"/"failed" }
PUT  /api/admin/pansou/config        → { "api_url": "...", "enabled": true/false }
POST /api/admin/pansou/test          → { "success": true, "message": "..." }
```

---

### 3.6 TG 转发配置 `/tg-forward`

**设置区：**
- **Bot Token** 输入框（密码模式）
- **用户 ID** 输入框
- ⚠️ 使用说明卡片：
  ```
  使用前需要在 Telegram 中：
  1. 向 @BotFather 申请 Token
  2. 新建一个频道
  3. 将 Bot 加入频道并设置为管理员
  4. 将频道 ID 填入下方配置
  ```

**源频道配置（可添加多个）：**
- 频道 ID 输入框
- 频道名称（可自定义）
- 添加频道按钮
- 频道列表（可删除）

**权限管理（与 3.5 同组件复用）：**
- 选择群 → 管理TG转发管理员/授权成员
- 独立开关每个群的TG转发

> ⚠️ 未填写 Bot Token 和用户 ID 则不启用

**API：**
```
GET  /api/admin/tg-forward/config      → { "bot_token": "***", "user_id": "...", "channels": [...], "enabled": true/false }
PUT  /api/admin/tg-forward/config      → update config
POST /api/admin/tg-forward/test        → test bot token
```

---

### 3.7 CF 图床配置 `/cftc`

**设置区：**
- **CF 图床网址** 输入框（示例：`https://cftc.lliic.com`）
- **用户名** 输入框
- **密码** 输入框（密码模式）
- 测试连接按钮

> ⚠️ 说明卡片：
> ```
> 需要自行搭建 CF 图床服务：
> GitHub: https://github.com/iawooo/cftc
> 按照仓库说明部署后，填入你的服务地址和账号密码。
> ```

**权限管理（与 3.5 同组件复用）：**
- 选择群 → 管理CF图床管理员/授权成员
- 独立开关每个群的CF图床上传功能

> ⚠️ 未填写图床网址和账号密码则不启用

**API：**
```
GET  /api/admin/cftc/config      → { "url": "...", "username": "...", "enabled": true/false }
PUT  /api/admin/cftc/config      → { "url": "...", "username": "...", "password": "..." }
POST /api/admin/cftc/test        → test connection
```

---

### 3.8 模块推送配置 `/module-push`

**设置区：**
- **GitHub API Token** 输入框（密码模式）
- 自定义推送源列表（可添加多个）：
  | 字段 | 说明 | 示例 |
  |-----|------|------|
  | owner | 仓库所有者 | `mytv-android` |
  | repo | 仓库名 | `myDV` |
  | name | 显示名称 | `myTV/myDV` |
- 添加/删除推送源

**权限管理（与 3.5 同组件复用）：**
- 选择群 → 管理模块推送管理员/授权成员
- 独立开关每个群的模块推送

> ⚠️ 未填写 GitHub Token 则不启用

**API：**
```
GET  /api/admin/module-push/config      → { "github_token": "***", "repos": [...], "enabled": true/false }
PUT  /api/admin/module-push/config      → update config
```

---

### 3.9 公众号推文配置 `/werss`

**设置区：**
- **WeRSS 地址** 输入框（支持内网 IP 和自定义网址）
- **用户名** 输入框
- **密码** 输入框（密码模式）
- 测试连接按钮

> ⚠️ 说明卡片：
> ```
> 需要自行搭建 WeRSS 服务：
> GitHub: https://github.com/rachelos/we-mp-rss
> 按照仓库说明部署后，填入你的服务地址和账号密码。
> ```

**权限管理（与 3.5 同组件复用）：**
- 选择群 → 管理推文推送管理员/授权成员
- 独立开关每个群的推文推送

> ⚠️ 未填写 WeRSS 地址和账号密码则不启用

**API：**
```
GET  /api/admin/werss/config      → { "base_url": "...", "enabled": true/false }
PUT  /api/admin/werss/config      → { "base_url": "...", "username": "...", "password": "..." }
POST /api/admin/werss/test        → test connection
```

---

## 四、通用组件设计

### 4.1 侧边导航栏（左侧）

```
┌──────────────────┐
│    WxPowerBot     │  ← Logo + 标题
├──────────────────┤
│  📊 仪表盘       │
│  💬 微信登录     │
│  👥 群授权系统   │
│  🔍 盘搜配置     │
│  📨 TG转发配置   │
│  🖼️ CF图床配置   │
│  📦 模块推送     │
│  📰 推文配置     │
│  ⚙️ 系统设置     │
├──────────────────┤
│  👤 admin         │  ← 用户信息 + 退出按钮
└──────────────────┘
```

- 可折叠（移动端自动收起）
- 当前选中项高亮
- 未配置的插件显示灰色禁用状态

### 4.2 群权限管理组件（复用）

所有插件的权限管理使用同一个组件：

```
┌──────────────────────────────────────────┐
│  选择群聊: [下拉搜索框 ▼]                │
├──────────────────────────────────────────┤
│  ┌─ 当前管理员 ──────────────────────┐   │
│  │  [昵称1 ✕]  [昵称2 ✕]  [昵称3 ✕] │   │
│  │  添加: [输入昵称自动匹配ID] [添加] │   │
│  └────────────────────────────────────┘   │
│  ┌─ 授权使用成员 ────────────────────┐   │
│  │  [成员A ✕]  [成员B ✕]             │   │
│  │  添加: [输入昵称自动匹配ID] [添加] │   │
│  └────────────────────────────────────┘   │
│  ┌─ 群聊列表 ────────────────────────┐   │
│  │  ☑ 群A (已启用)                    │   │
│  │  ☑ 群B (已启用)                    │   │
│  │  ☐ 群C (未启用)                    │   │
│  │  [添加群] [删除群]                  │   │
│  └────────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

### 4.3 配置状态指示

每个插件设置页顶部显示配置状态栏：

```
[⚡ 已配置] [测试连接 ✔] [✓ 当前生效]
[⚠️ 未配置 - 功能未启用]
[❌ 配置错误 - 请检查设置]
```

---

## 五、后端架构设计

### 5.1 文件结构

```
wxpowerbot/
├── admin/
│   ├── __init__.py
│   ├── server.py           # FastAPI 应用 + 路由注册
│   ├── auth.py             # JWT 认证
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py         # 登录接口
│   │   ├── wechat.py       # 微信管理接口
│   │   ├── groups.py       # 群授权接口
│   │   ├── pansou.py       # 盘搜接口
│   │   ├── tg_forward.py   # TG转发接口
│   │   ├── cftc.py         # CF图床接口
│   │   ├── module_push.py  # 模块推送接口
│   │   ├── werss.py        # 推文接口
│   │   └── settings.py     # 系统设置接口
│   ├── models/
│   │   ├── __init__.py
│   │   ├── acl.py          # ACL 读写操作（复用 bot.py 的数据）
│   │   └── config.py       # 配置读写
│   └── static/             # 前端构建产物
│       ├── index.html
│       ├── assets/
│       └── ...
├── bot.py                  # 主机器人（注入 admin server）
├── main.py                 # 入口（同时启动 bot 和 admin server）
├── DESIGN.md               # 本设计文档
└── ...
```

### 5.2 数据共享机制

```
WxPowerBot 实例
    │
    ├── self._acl          → admin/routes/groups.py 直接读取/写入
    ├── self.config        → admin/routes/*.py 读取配置数据
    ├── self._itchat       → admin/routes/wechat.py 控制登录状态
    │
    └── AdminServer (FastAPI)
         ├── 注入 WxPowerBot 实例引用
         ├── 操作 ACL 和配置需加 self._acl_lock
         └── 回调通知 bot 重新加载配置
```

### 5.3 核心 API 汇总

```
POST   /api/admin/login               # 登录获取 JWT
GET    /api/admin/dashboard            # 仪表盘数据
POST   /api/admin/bot/restart          # 重启机器人
POST   /api/admin/bot/shutdown         # 关闭微信连接

# 微信
GET    /api/admin/wechat/qr            # 获取二维码
GET    /api/admin/wechat/status        # 登录状态
POST   /api/admin/wechat/logout        # 退出登录
POST   /api/admin/wechat/refresh-qr    # 刷新二维码

# 群授权
GET    /api/admin/groups
GET    /api/admin/groups/:id
PUT    /api/admin/groups/:id
PUT    /api/admin/groups/:id/admins
PUT    /api/admin/groups/:id/users
PUT    /api/admin/groups/:id/commands
POST   /api/admin/groups/:id/sync-members
DELETE /api/admin/groups/:id
POST   /api/admin/groups

# 盘搜
GET    /api/admin/pansou/config
PUT    /api/admin/pansou/config
POST   /api/admin/pansou/test

# TG转发
GET    /api/admin/tg-forward/config
PUT    /api/admin/tg-forward/config
POST   /api/admin/tg-forward/test

# CF图床
GET    /api/admin/cftc/config
PUT    /api/admin/cftc/config
POST   /api/admin/cftc/test

# 模块推送
GET    /api/admin/module-push/config
PUT    /api/admin/module-push/config

# WeRSS推文
GET    /api/admin/werss/config
PUT    /api/admin/werss/config
POST   /api/admin/werss/test

# 系统设置
GET    /api/admin/settings
PUT    /api/admin/settings              # 含登录背景配置
PUT    /api/admin/settings/password     # 修改登录密码

# 群成员搜索（通用，用于权限管理组件中的自动匹配）
GET    /api/admin/groups/:id/members?q=关键词
```

---

## 六、前端组件目录

```
src/
├── App.vue                    # 根组件（路由容器）
├── router/
│   └── index.ts               # Vue Router 配置
├── store/
│   ├── auth.ts                # 认证状态（token, user）
│   └── dashboard.ts           # 仪表盘数据
├── api/
│   ├── client.ts              # Axios 实例（拦截器注入 token）
│   ├── auth.ts                # 登录 API
│   ├── wechat.ts
│   ├── groups.ts
│   ├── pansou.ts
│   ├── tgForward.ts
│   ├── cftc.ts
│   ├── modulePush.ts
│   ├── werss.ts
│   └── settings.ts
├── layouts/
│   └── AdminLayout.vue        # 侧边栏 + 顶栏 + 内容区布局
├── views/
│   ├── Login.vue              # 登录页
│   ├── Dashboard.vue          # 仪表盘
│   ├── WeChatManagement.vue   # 微信登录管理
│   ├── GroupsManagement.vue   # 群授权系统
│   ├── PanSouConfig.vue       # 盘搜配置
│   ├── TGForwardConfig.vue    # TG转发配置
│   ├── CFTCConfig.vue         # CF图床配置
│   ├── ModulePushConfig.vue   # 模块推送配置
│   ├── WeRSSConfig.vue        # 推文配置
│   └── Settings.vue           # 系统设置
└── components/
    ├── Sidebar.vue            # 侧边导航栏
    ├── GroupPermission.vue    # 群权限管理通用组件（复用）
    ├── GroupSelector.vue      # 群选择下拉框
    ├── QRCodeDisplay.vue      # 二维码显示组件
    ├── ConfigStatus.vue       # 配置状态指示组件
    ├── CommandEditor.vue      # 命令自定义编辑器
    └── ConfirmModal.vue       # 确认弹窗
```

---

## 七、关键数据流

### 7.1 微信登录流程

```
用户在前端点击「获取二维码」
    → GET /api/admin/wechat/qr
    → 后端调用 itchat.get_QR() 生成二维码
    → 返回 base64 图片 + 过期时间(30s)
    → 前端显示二维码 + 倒计时

前端每 2 秒轮询 GET /api/admin/wechat/status
    → 后端检查 itchat.loginInfo
    → 状态：
      - 'waiting'     → 继续轮询
      - 'scanned'     → 前端显示「已扫码，请在手机上确认」
      - 'logged_in'   → 跳转到仪表盘，显示登录成功
      - 'timeout'     → 二维码过期，前端自动刷新

倒计时结束 → 自动调用 refresh-qr 重新获取二维码
```

### 7.2 群成员自动匹配流程

```
用户在权限管理页面输入「群成员昵称」
    → 输入停止 300ms 后触发搜索
    → GET /api/admin/groups/:id/members?q=昵称
    → 后端在 groups[n].members_cache 中模糊匹配
    → 返回匹配列表 [{uid, display_name, nick_name}]
    → 前端显示下拉候选列表
    → 用户选择一条 → 自动填充 uid
    → 保存时发送 uid 而非昵称
```

### 7.3 插件启用/禁用流程

```
用户打开插件设置页
    → GET /api/admin/pansou/config
    → 如果 api_url 为空 → 前端显示「⚠️ 未配置 - 功能未启用」
    → 如果已配置 → 显示「⚡ 已配置 ✓」

用户在权限管理 Tab 选择某个群
    → 显示该群当前 pansou_enabled 状态
    → 切换开关 → PUT /api/admin/groups/:id
    → 后端更新 acl.json 中该群的 pansou_enabled
    → bot.py 的 CommandHandlers 读取该字段决定是否响应盘搜命令
```

---

## 八、TODO 清单（按开发顺序）

### Phase 1：后端骨架
- [ ] 创建 `admin/` 目录结构
- [ ] 实现 JWT 认证模块 `admin/auth.py`
- [ ] 实现 FastAPI 服务器 + CORS 中间件
- [ ] 实现登录 API
- [ ] 在 `main.py` 中启动 admin server（端口 8645 或可配置）
- [ ] 更新 Dockerfile 安装 FastAPI + uvicorn + PyJWT

### Phase 2：API 实现
- [ ] Dashboard API
- [ ] 微信登录管理 API（QR生成、状态轮询、登出）
- [ ] 群授权 API（CRUD、成员匹配）
- [ ] 盘搜配置 API
- [ ] TG转发配置 API
- [ ] CF图床配置 API
- [ ] 模块推送配置 API
- [ ] WeRSS推文配置 API
- [ ] 系统设置 API（含背景配置）

### Phase 3：前端开发
- [ ] 初始化 Vue 3 + Vite + Arco Design 项目
- [ ] 登录页面（含自定义背景支持）
- [ ] 仪表盘页面
- [ ] 微信登录管理页面
- [ ] 群授权系统页面（含通用权限组件）
- [ ] 各插件配置页面（盘搜/TG转发/CF图床/模块推送/推文）
- [ ] 系统设置页面
- [ ] 侧边导航栏 + 路由守卫

### Phase 4：集成与测试
- [ ] 前端构建产物放入 `admin/static/`
- [ ] 后端正确 serve 静态文件
- [ ] 完整功能测试
- [ ] 更新 docker-compose.yml 暴露管理端口
- [ ] 更新 README 文档

---

## 九、注意事项

1. **ACL 锁竞争**：管理后台和 bot.py 共享 `_acl_lock`，写操作必须加锁
2. **itchat 状态同步**：itchat 进程内只有唯一实例，管理后端的微信操作必须通过 WxPowerBot 实例方法进行
3. **密码安全**：管理后台密码存储在 `data/state/config.json`（bcrypt 哈希），非明文
4. **JWT 过期**：默认 24 小时过期
5. **端口规划**：管理后台使用独立端口 8645（不与 QR 页 8646 冲突）
