# 青禾知行（v1）

日期：2026-04-20
状态：设计已确认，待实现

本文件是对 `docs/方案v1.md` 与 `docs/产品方案v1.md` 的修订版。与原方案的关键偏离已在第 3 节列出。

## 1. 产品形态

知识可视化站点。登录用户可浏览站内公开的互动动画库；制作者可对外生成带时效的分发链接，站外访客凭链接在浏览器内观看 HTML，链接过期或被撤销后失效。

三类角色：

- **管理员（admin）**：管理用户、所有内容、标签体系；可下架/删除任意内容。
- **制作者（creator）**：上传/编辑/删除自己上传的内容；为自己内容生成对外分发链接。
- **浏览者（viewer，登录用户）**：浏览公开库、在线观看；不能上传。
- **站外访客**：无账号，仅能通过分发链接在有效期内观看；可选下载。

v1 仅交付一个一级菜单 `互动动画管理`，后续菜单平级扩展。

## 2. 信息架构

```
站点
├── 登录页
├── 互动动画管理（v1 唯一菜单）
│   ├── 公开库（列表 + 标签筛选 + 搜索 + 分页）
│   │   └── 详情/观看页
│   ├── 我的上传（creator/admin）
│   │   ├── 上传页
│   │   └── 分发链接管理（查看、生成、撤销、使用记录）
│   └── 管理后台（admin）
│       ├── 全部内容
│       ├── 用户管理
│       └── 标签管理
└── 外部观看页（/s/{token}，无需登录，带时效校验）
```

设计要点：

- "公开库"对全体登录用户可见，与"我的上传"隔离，避免制作者越权编辑他人内容。
- 对外分发走独立路径 `/s/{token}`，与站内路径彻底隔离。

## 3. 核心流程

### 3.1 上传 → 入库

1. 制作者在"上传页"填：标题、标签（多选/新建）、简介（可选）、HTML 文件。
2. 后端校验：登录态、MIME/扩展名、大小上限（10MB）、内容首字节真实类型检测。
3. 存 OSS（私有读），写 `contents` 记录，初始 `visibility=public_in_site`。

### 3.2 站内观看

1. 浏览者在公开库点条目进详情页。
2. 详情页用 `<iframe sandbox="allow-scripts">` 嵌入 `/view/{content_id}`；该路径由后端代理读 OSS 并以 `text/html` 返回，附加严格 CSP。
3. 每次访问落 `view_logs`。

### 3.3 对外分发

1. 制作者在"我的上传"为某条内容点"生成分发链接"，填：有效期（预设 1h/24h/7d/自定义）、是否允许下载原文件（默认否）。
2. 后端生成 `share_token`（密码学随机 22+ 字符），写 `share_links`。
3. 返回 `https://site/s/{token}`。
4. 制作者可在列表里**撤销**（提前失效）、**查看访问次数**。

### 3.4 站外访问

1. `/s/{token}` → 后端校验 token 存在、未撤销、未过期 → 渲染观看页（仍走 iframe 代理 `/view-share/{token}`）。
2. 每次访问落 `share_access_logs`。
3. 过期/撤销/不存在：统一返回失效页，不泄漏原因差异。

### 3.5 与原 v1 方案的关键偏离

- 去掉 `SHA256(username:file_id)` 的 key 规则——改用密码学随机 token。原规则可枚举、不可撤销、改用户名会变。
- 去掉"一次性成功"原子语义——改时效 + 撤销。原语义在在线观看场景下接收方刷新即失效，体验不可接受。
- 文件不再是"下载后本地打开"，而是浏览器内沙箱观看为主、下载为可选。
- 仍保留访问日志审计；OSS 私有读、后端代理的安全模型不变。

## 4. 数据模型（PostgreSQL 15+）

```
users
  id BIGSERIAL PK,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','creator','viewer')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()

contents                                -- 内容主表（替代原 files）
  id BIGSERIAL PK,
  uploader_id BIGINT REFERENCES users(id),
  title TEXT NOT NULL,
  description TEXT,
  oss_bucket TEXT NOT NULL,
  oss_object_key TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  sha256 TEXT NOT NULL,                 -- 内容指纹，仅用于查重/审计
  visibility TEXT NOT NULL DEFAULT 'public_in_site'
    CHECK (visibility IN ('public_in_site','private')),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active','deleted')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()

  INDEX(uploader_id, created_at)
  INDEX(visibility, created_at)
  INDEX(sha256)

tags
  id BIGSERIAL PK,
  name TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()

content_tags                             -- 多对多
  content_id BIGINT REFERENCES contents(id) ON DELETE CASCADE,
  tag_id BIGINT REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (content_id, tag_id),
  INDEX(tag_id)

share_links
  id BIGSERIAL PK,
  token TEXT UNIQUE NOT NULL,            -- secrets.token_urlsafe(22)
  content_id BIGINT REFERENCES contents(id),
  created_by BIGINT REFERENCES users(id),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  allow_download BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()

  INDEX(content_id, created_at)
  INDEX(created_by, created_at)

view_logs
  id BIGSERIAL PK,
  content_id BIGINT,
  user_id BIGINT,
  viewed_at TIMESTAMPTZ DEFAULT now(),
  client_ip INET,
  user_agent TEXT

share_access_logs
  id BIGSERIAL PK,
  token TEXT NOT NULL,
  content_id BIGINT,
  viewed_at TIMESTAMPTZ DEFAULT now(),
  client_ip INET,
  user_agent TEXT,
  result TEXT CHECK (result IN ('success','expired','revoked','not_found'))

audit_logs                               -- 操作审计
  id BIGSERIAL PK,
  actor_id BIGINT,
  action TEXT,                           -- login/upload/create_share/revoke_share/delete_content/...
  target_type TEXT,
  target_id BIGINT,
  detail JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
```

设计要点：

- `sha256` 只是内容指纹，不参与安全控制。
- `share_links` 与 `contents` 是 1:N，一条内容可并行发多个不同有效期的链接。
- `token` 用 `secrets.token_urlsafe(22)`（约 176 bit），不可枚举、与用户名解耦。
- 撤销=写 `revoked_at`，不删记录，便于审计。

## 5. 接口草案

### 5.1 鉴权

```
POST   /api/auth/login            {username, password} → {token, user}
POST   /api/auth/logout
GET    /api/auth/me
```

### 5.2 内容（站内）

```
GET    /api/contents              ?tag=&q=&page=&size=    公开库列表
GET    /api/contents/{id}         详情（登录）
POST   /api/contents              multipart: file, title, description, tags[]
PATCH  /api/contents/{id}         改标题/标签/简介（本人或 admin）
DELETE /api/contents/{id}         软删（本人或 admin）
GET    /api/contents/mine         ?page=&size=            我的上传
GET    /view/{id}                 iframe 代理读 OSS（登录校验）
```

### 5.3 分发链接

```
POST   /api/contents/{id}/shares  {expires_in, allow_download} → {token, url, expires_at}
GET    /api/contents/{id}/shares  列表（本人或 admin）
DELETE /api/shares/{token}        撤销
GET    /api/shares/{token}/logs   访问记录
```

### 5.4 站外访问（无需登录）

```
GET    /s/{token}                 渲染外部观看页
GET    /view-share/{token}        iframe 代理读 OSS（校验 token 时效）
GET    /d/{token}                 下载原文件（仅当 allow_download=true）
```

### 5.5 管理员

```
GET/PATCH/DELETE /api/admin/users/...
GET    /api/admin/contents        全部内容
CRUD   /api/admin/tags
```

### 5.6 标签

```
GET    /api/tags                  下拉补全
```

## 6. 安全与关键技术点

### 6.1 沙箱隔离

- 所有 HTML 内容只能通过 `<iframe sandbox="allow-scripts">` 加载，**不加** `allow-same-origin`。即使 HTML 带恶意脚本也无法读主站 cookie/localStorage 或发同源请求。
- 推荐把 `/view/*` 与 `/view-share/*` 挂在独立子域（如 `content.example.com`），与主站域 cookie 隔离。v1 若只用单域名，则强制依赖 sandbox + CSP。
- 响应头：
  - `Content-Security-Policy: sandbox; default-src 'self' data:;`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: no-referrer`

### 6.2 Token 与时效

- `token = secrets.token_urlsafe(22)`，不可猜测、不可枚举。
- 校验顺序：格式 → 查库 → `revoked_at IS NULL` → `expires_at > now()` → 放行。
- 失败统一返回"链接已失效"，不区分 expired/revoked/not_found 文案，防止侧信道。
- 速率限制：按 IP + token 前缀做限流，防爆破。

### 6.3 上传校验

- 白名单：扩展名 `.html`、MIME `text/html`、大小 ≤ 10MB。
- 读首 512 字节检测真实类型，拒绝伪装。
- 计算 sha256 后写入。

### 6.4 OSS

- Bucket 私有读，Object key 规则：`contents/{yyyy}/{mm}/{uuid}.html`，不含用户名。
- v1 走后端代理（`GetObject` 流式转发），**不发签名 URL 给前端**——避免绕过登录/时效校验。
- 记录每次 OSS 调用的 `x-oss-request-id` 用于排障。

### 6.5 审计

- 登录、上传、生成链接、撤销、删除内容都落 `audit_logs`。
- 站内浏览落 `view_logs`，站外访问落 `share_access_logs`。

### 6.6 会话

- HttpOnly + Secure + SameSite=Lax 的会话 cookie，session 存 Redis。
- v1 不做 SSO/第三方登录。

## 7. 技术栈与部署

- **后端**：Python + FastAPI。优点：类型注解、自动 OpenAPI、异步流式响应方便代理 OSS。
- **数据库**：PostgreSQL 15+，driver 用 `psycopg[binary]` 或 `asyncpg`。
- **ORM**：SQLAlchemy 2.x。
- **OSS SDK**：阿里云 `oss2`，固定签名 V4。
- **前端**：Vue 3 + Element Plus 或 React + Antd（团队熟悉度优先）。
- **会话存储**：Redis。
- **部署**：阿里云 ECS（单台起步） + Nginx 反代 + Gunicorn/Uvicorn；数据库强烈建议用**阿里云 RDS PostgreSQL**，备份高可用省心；OSS 同地域部署，走内网 endpoint。
- **网络**：安全组只开 80/443 + 运维端口；DB/Redis 不对公网暴露。
- **时区**：ECS、PostgreSQL 统一 `Asia/Shanghai`，时间字段全链路 +08（v1 简单起见）。
- **日志**：应用日志落文件，附 OSS request_id；v1 不引入 APM。
- **Nginx**：`client_max_body_size 12m;`。

### 7.1 后端目录建议

```
app/
  api/         路由
  services/    业务逻辑（upload, share, view）
  models/      ORM
  oss/         OSS 客户端封装
  security/    csp、sandbox、ratelimit
  audit/       日志
  deps.py      依赖注入（当前用户、db session）
main.py
```

## 8. v1 验收标准

- 管理员可创建 creator/viewer 账号；三类角色权限边界正确。
- 制作者可上传 HTML（类型/大小校验通过），失败时返回清晰原因。
- 公开库列表可按标签筛选、按标题搜索、分页。
- 详情页可在 iframe sandbox 中正常观看 HTML 互动内容。
- 制作者可为自己内容生成分发链接，设定 1h/24h/7d 有效期；可撤销；可查看访问次数。
- 站外访客通过 `/s/{token}` 在有效期且未撤销时可观看；过期/撤销/无效统一返回失效页。
- 上传、生成链接、撤销、删除动作有审计日志；站内浏览与站外访问有访问记录。
- OSS 对象私有读，不存在可直接访问的长期 URL。

## 9. v1 边界与后续

- v1 **不做**：评论、收藏、内容编辑（仅元信息编辑）、内容版本管理、团队/空间、SSO、统计报表、CDN 加速。
- 后续可扩展：资源库与多级分类、模板管理、统计分析、权限分组、CDN/边缘缓存、Webhook 通知。
