# 青禾知行 v1 — 阿里云部署 Runbook

## 资源清单

| 资源 | 规格建议 | 备注 |
|---|---|---|
| ECS | 2c4g（ecs.t6-c2m2.large 或同档），CentOS / AlmaLinux 8 | 安装 Docker 24+ |
| RDS PostgreSQL | 15.x，1c2g 起步 | 开内网访问 |
| OSS Bucket | 标准存储，私有读写 | 与 ECS 同地域，使用内网 endpoint |
| 域名 + ICP | qinghe.example.com | 备案完成后绑定 ECS 公网 IP |
| SSL 证书 | 阿里云免费证书或 Let's Encrypt | 放置 `deploy/certs/` |

## 一次性配置

### 1. RDS PostgreSQL
1. 控制台创建实例，选「PostgreSQL 15」，专有网络与 ECS 同 VPC。
2. 创建数据库 `qinghe`、账号 `qinghe`（强密码）。
3. 白名单加入 ECS 内网网段。
4. 记录内网连接串：`postgresql+asyncpg://qinghe:PWD@HOST:5432/qinghe`。

### 2. OSS Bucket
1. 创建 Bucket `qinghe-prod`，地域与 ECS 同；读写权限选「私有」。
2. 跨域规则：v1 不需要直传，留空。
3. 服务端加密：开启「OSS 完全托管 (SSE-OSS)」。
4. 生命周期：可选——为 `contents/` 前缀设置 365 天后转低频，降低成本。

### 3. RAM 子账号
1. 创建子账号 `qinghe-app`，仅程序访问。
2. 自定义策略 `qinghe-oss-rw`：

   ```json
   {
     "Version": "1",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["oss:PutObject", "oss:GetObject", "oss:DeleteObject", "oss:HeadObject"],
         "Resource": ["acs:oss:*:*:qinghe-prod/contents/*"]
       },
       {
         "Effect": "Allow",
         "Action": ["oss:ListObjects"],
         "Resource": ["acs:oss:*:*:qinghe-prod"],
         "Condition": { "StringLike": { "oss:Prefix": ["contents/*"] } }
       }
     ]
   }
   ```

3. 附加策略后生成 AK/SK，写入 `.env.prod`。

### 4. 安全组
- 入方向：80/443 对 0.0.0.0/0；22 仅运维 IP。
- 出方向：默认放行（需访问 RDS 内网与 OSS 内网 endpoint）。

## 部署步骤

```bash
# 0. ECS 安装 Docker
curl -fsSL https://get.docker.com | bash
systemctl enable --now docker

# 1. 拉取/上传镜像（CI 推到 ACR；或本地构建后 docker save / load）
# 推荐 ACR：在本地构建后 push 到 cr.cn-hangzhou.aliyuncs.com/qinghe/{backend,frontend}:vX.Y.Z
docker pull cr.cn-hangzhou.aliyuncs.com/qinghe/backend:v1.0.0
docker pull cr.cn-hangzhou.aliyuncs.com/qinghe/frontend:v1.0.0
docker tag cr.cn-hangzhou.aliyuncs.com/qinghe/backend:v1.0.0 qinghe-backend:latest
docker tag cr.cn-hangzhou.aliyuncs.com/qinghe/frontend:v1.0.0 qinghe-frontend:latest

# 2. 准备配置
cd /opt/qinghe
git clone <repo> .
cp deploy/.env.prod.example deploy/.env.prod
vim deploy/.env.prod   # 填实际值
mkdir -p deploy/certs && cp /path/to/{fullchain,privkey}.pem deploy/certs/

# 3. 数据库初始化
docker run --rm --env-file deploy/.env.prod qinghe-backend:latest \
  alembic upgrade head

# 4. 创建初始 admin
docker run --rm -it --env-file deploy/.env.prod qinghe-backend:latest \
  python -m app.cli.seed_admin --username admin --password 'INIT_PWD'

# 5. 启动
cd deploy && docker compose -f docker-compose.prod.yml up -d
docker compose ps
curl -fsS https://qinghe.example.com/health
```

## 升级流程

```bash
# 1. 更新镜像 tag
sed -i 's|qinghe-backend:latest|qinghe-backend:v1.x.y|' deploy/docker-compose.prod.yml
sed -i 's|qinghe-frontend:latest|qinghe-frontend:v1.x.y|' deploy/docker-compose.prod.yml

# 2. 拉取并重启
docker compose -f deploy/docker-compose.prod.yml pull
docker run --rm --env-file deploy/.env.prod qinghe-backend:v1.x.y alembic upgrade head
docker compose -f deploy/docker-compose.prod.yml up -d
```

## 备份

- **RDS**：开启自动备份，保留 7 天；每月手动快照一次留存 3 个月。
- **OSS**：开启版本控制 + 跨地域复制（可选）。
- **应用配置**：`deploy/.env.prod` 与证书加密备份至 OSS 私有 Bucket（独立的运维 Bucket）。

## 监控与日志

- 容器日志：`docker compose logs -f backend`；建议接入阿里云 SLS。
- 应用 `/health` 由 SLB 或云监控探活。
- Redis：可选接入云数据库 Redis 替代自建容器。

## 故障排查

| 现象 | 排查 |
|---|---|
| 502 | `docker compose logs nginx backend`，看 upstream 是否健康 |
| OSS 上传 403 | RAM 策略权限、AK/SK、bucket region 是否一致 |
| 分发链接 429 | Redis 限流计数；调整 `SHARE_RATE_LIMIT_PER_MIN` |
| 会话失效频繁 | 检查 Redis 持久化与 `SESSION_TTL_SECONDS` |
| HTML 加载白屏 | 浏览器 DevTools → Console，看 CSP/sandbox 报错 |
