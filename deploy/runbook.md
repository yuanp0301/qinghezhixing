# 青禾知行 v1 — 阿里云资源与运维说明

**应用部署（ECS 裸机、Python 3.11、SQLite）请以 [`ECS部署指南.md`](./ECS部署指南.md) 为准。**

---

## 资源清单

| 资源 | 规格建议 | 备注 |
|------|----------|------|
| ECS | 2c4g 或更高 | 安装 Python **3.11**、Nginx、Node（前端构建） |
| OSS Bucket | 标准存储，私有读写 | 与 ECS 同地域；服务端访问用 RAM 子账号 AK |
| 域名与备案 | 按监管要求 | 解析至 ECS 公网 IP |
| SSL 证书 | 阿里云证书或 Let’s Encrypt | 配置于 Nginx `listen 443 ssl` |

---

## 一次性配置

### 1. OSS Bucket

1. 控制台创建 Bucket，地域与 ECS 一致；读写权限选「私有」。
2. 可选：为 `contents/` 前缀配置生命周期以降低成本。

### 2. RAM 子账号

1. 创建子账号，仅用于应用访问 OSS。
2. 自定义策略示例（按需替换 Bucket 名）：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["oss:PutObject", "oss:GetObject", "oss:DeleteObject", "oss:HeadObject"],
      "Resource": ["acs:oss:*:*:your-bucket/contents/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["oss:ListObjects"],
      "Resource": ["acs:oss:*:*:your-bucket"],
      "Condition": { "StringLike": { "oss:Prefix": ["contents/*"] } }
    }
  ]
}
```

3. 附加策略后创建 AccessKey，写入服务器上的 `backend/.env` 或 `deploy/init_qinghe.env`，**勿提交 Git**。

### 3. 安全组

- 入方向：**80** / **443** 对公网；**22** 建议仅运维 IP。
- 后端若仅监听 `127.0.0.1:8000`，无需对公网开放 **8000**。

---

## 备份建议

- **SQLite**：定期备份 `backend/data/qinghe.db`（及相关 WAL 文件，需在服务短时停止或一致快照策略下进行）。
- **OSS**：重要对象可开启版本控制；关键配置与证书单独加密备份。

---

## 监控与日志

- 应用探活：`GET /health`（经 Nginx 或直连本机端口）。
- 后端：`journalctl -u qinghe-backend -f`（服务名以 systemd 单元为准）。
- Nginx：`/var/log/nginx/`。

---

## 故障排查

| 现象 | 排查 |
|------|------|
| 502 / 504 | `systemctl status` 后端与 nginx；`curl -sS http://127.0.0.1:8000/health` |
| OSS 上传失败 | RAM 策略、AK/SK、endpoint 与 region、Bucket 名是否一致 |
| 静态页白屏 | 浏览器控制台；确认 `frontend/dist` 已构建且 Nginx `root` 路径正确 |
| 登录后跨域失败 | `PUBLIC_BASE_URL`、`CORS_ORIGINS` 与浏览器访问域名一致 |
