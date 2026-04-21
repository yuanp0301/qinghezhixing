# OSS 使用方法（面向本项目）

本文档描述在“知识可视化站点”中如何使用阿里云 OSS 完成文件存储与下载能力。

## 1. 使用目标

在当前 `互动动画管理` 菜单中，OSS 负责：

- 保存用户上传的 HTML 原文件。
- 基于业务 key 下载对应文件。
- 提供受控访问能力（私有存储 + 签名 URL 或后端代理）。

## 2. 接入原则

- 生产环境优先使用官方 OSS SDK，不建议手写签名请求。
- 使用 AccessKey（或 RAM 角色）进行鉴权，签名版本采用 V4（推荐）。
- 请求必须使用 Bucket 所在地域的 Endpoint。
- Bucket 建议设置为 `private`，避免公开读带来的泄漏风险。

## 3. 关键配置项

需要在服务端配置以下信息：

- `OSS_REGION`：地域（例如 `cn-hangzhou`）
- `OSS_ENDPOINT`：地域对应 Endpoint
- `OSS_BUCKET`：Bucket 名称
- `OSS_ACCESS_KEY_ID`
- `OSS_ACCESS_KEY_SECRET`
- `OSS_OBJECT_PREFIX`：对象路径前缀（例如 `interactive-animations/`）

建议：

- 将密钥放入环境变量，不要写入代码库。
- 使用 RAM 最小权限策略，仅放行本项目必需操作。

## 4. 对象路径规划

建议对象路径按日期与业务 ID 分层，便于管理和排障：

`interactive-animations/{yyyy}/{mm}/{dd}/{file_id}.html`

可选扩展：

- 在路径中增加租户或用户名目录。
- 将原始文件名记录在数据库，不直接作为对象 key（避免特殊字符问题）。

## 5. 上传流程（对应上传接口）

1. 接收用户上传文件（仅 `.html`）。
2. 服务端校验：
   - 文件类型（MIME + 扩展名双校验）
   - 文件大小（例如不超过 10MB）
3. 生成业务 `file_id` 和 OSS `object_key`。
4. 调用 OSS `PutObject` 上传文件内容。
5. 可选：调用 `HeadObject` 复核对象存在与元信息。
6. 将以下信息写入数据库：
   - `file_id`
   - `oss_bucket`
   - `oss_object_key`
   - `size_bytes`
   - `content_type`
   - `etag`（可选）

## 6. 下载流程（对应 /d/{key}）

1. 根据业务规则校验 `key`（格式、存在性、未使用）。
2. 查询到 `oss_bucket + oss_object_key` 后执行下载。
3. 下载方式二选一：
   - 方式 A：生成短时效签名 URL，302 重定向给用户下载。
   - 方式 B：后端调用 `GetObject`，代理流式返回给用户。
4. 下载成功后：
   - 将 key 标记为 `used`
   - 写入 `key_usage_logs`

推荐：

- v1 优先采用“302 到签名 URL”，实现简单且性能较好。
- 如需更细粒度审计或内容改写，再改为后端代理下载。

## 7. 常用 OSS 操作映射

本项目常用到的 OSS 能力：

- `PutObject`：上传对象
- `GetObject`：下载对象（代理方式）
- `HeadObject`：查询对象元信息
- 预签名 URL 生成：用于受控下载
- `DeleteObject`（可选）：配合后续清理策略

## 8. 错误处理规范

OSS 请求失败通常返回 4xx/5xx，并带错误码和错误信息。

服务端建议统一处理：

- 记录 `x-oss-request-id`（关键排障字段）
- 错误分类：
  - 鉴权失败（密钥、签名、权限问题）
  - 对象不存在
  - 限流或服务异常
- 对外返回业务可理解错误，不直接透传底层细节

## 9. 安全与风控建议

- Bucket 使用私有读，不开公共读。
- 下载必须先过业务 key 校验，再触发 OSS 下载。
- 对下载接口增加限流，防止 key 枚举。
- 对上传和下载行为保留审计日志（用户、时间、IP、结果）。
- 对密钥定期轮换，避免长期凭证风险。

## 10. 与本项目数据表关系

`files` 表建议保存：

- `oss_bucket`
- `oss_object_key`
- `content_type`
- `size_bytes`
- `key` / `key_status`

`key_usage_logs` 表建议保存：

- `key`
- `used_at`
- `result`
- `client_ip`
- `user_agent`

## 11. 参考文档

- https://help.aliyun.com/zh/oss/developer-reference/list-of-operations-by-function
- https://help.aliyun.com/zh/oss/developer-reference/recommend-to-use-signature-version-4
- https://help.aliyun.com/zh/oss/user-guide/regions-and-endpoints
- https://help.aliyun.com/zh/oss/user-guide/overview-14
