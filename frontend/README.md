# 青禾知行 · 前端

Vue 3 + Vite + TS + Element Plus，苹果式简洁风。

## 开发

确保后端已起在 :8000。

```bash
pnpm install
pnpm dev
```

打开 `http://localhost:5173`，登录后可用。

## 构建

```bash
pnpm build
```

产物在 `dist/`，由 Plan 5 中的 Nginx 提供静态服务。

## 已实现页面

- /login
- /contents 公开库
- /contents/mine 我的上传（creator/admin）
- /contents/new 上传（creator/admin）
- /contents/:id 详情/观看 + 分发链接弹窗 / 列表 / 访问记录抽屉

管理后台与外部观看页见 Plan 5（外部观看页由后端直接渲染）。
