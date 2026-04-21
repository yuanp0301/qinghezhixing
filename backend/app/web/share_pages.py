from datetime import datetime, timezone
from html import escape


_BASE_CSS = """
:root {
  color-scheme: light;
  --bg: #f7f8fa;
  --text: #1d1d1f;
  --muted: #6e6e73;
  --brand: #06b6a4;
  --divider: #ebedf0;
}
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Helvetica Neue", "Segoe UI", sans-serif;
  color: var(--text);
  background: var(--bg);
  font-size: 14px;
  line-height: 1.5;
}
header.bar {
  height: 56px;
  background: #ffffff;
  border-bottom: 1px solid var(--divider);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
}
header.bar .brand { font-weight: 500; }
header.bar .meta { color: var(--muted); font-size: 13px; }
main.viewer {
  height: calc(100% - 56px);
  display: flex; align-items: stretch; justify-content: center;
  background: #000;
}
main.viewer iframe {
  width: 100%; height: 100%; border: 0;
}
.actions { position: fixed; top: 72px; right: 24px; }
.actions a {
  text-decoration: none; color: #fff; background: rgba(0,0,0,.5);
  padding: 6px 12px; border-radius: 8px; font-size: 13px;
}
.empty {
  height: 100%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 24px; text-align: center;
}
.empty h1 { font-size: 22px; margin: 8px 0; font-weight: 500; }
.empty p  { color: var(--muted); max-width: 420px; }
.empty .brand { margin-top: 48px; color: var(--muted); font-size: 12px; }
"""


def _remaining(expires_at: datetime) -> str:
    now = datetime.now(timezone.utc)
    delta = expires_at - now
    secs = int(delta.total_seconds())
    if secs <= 0:
        return "已过期"
    days = secs // 86400
    if days >= 1:
        return f"剩 {days} 天"
    hours = secs // 3600
    mins = (secs % 3600) // 60
    return f"剩 {hours}h {mins:02d}m"


def render_valid_page(
    *, token: str, expires_at: datetime, allow_download: bool
) -> str:
    remain = escape(_remaining(expires_at))
    download_html = (
        f'<div class="actions">'
        f'<a href="/d/{escape(token)}">下载原文件</a></div>'
        if allow_download
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>青禾知行</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<header class="bar">
  <div class="brand">青禾知行</div>
  <div class="meta">剩余有效期：{remain}</div>
</header>
<main class="viewer">
  <iframe sandbox="allow-scripts" src="/view-share/{escape(token)}"></iframe>
</main>
{download_html}
</body></html>
"""


def render_invalid_page() -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>链接已失效 · 青禾知行</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="empty">
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
       stroke="#6e6e73" stroke-width="1.5" stroke-linecap="round"
       stroke-linejoin="round">
    <circle cx="12" cy="12" r="9"></circle>
    <path d="M9 9l6 6M15 9l-6 6"></path>
  </svg>
  <h1>链接已失效</h1>
  <p>此链接可能已过期、被撤销，或从未存在。请联系发送方获取新链接。</p>
  <div class="brand">由 青禾知行 提供</div>
</div>
</body></html>
"""


def render_rate_limited_page() -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8" />
<title>访问过于频繁 · 青禾知行</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="empty">
  <h1>访问过于频繁</h1>
  <p>请稍后再试。</p>
  <div class="brand">由 青禾知行 提供</div>
</div>
</body></html>
"""
