import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import "dayjs/locale/zh-cn";

dayjs.locale("zh-cn");
dayjs.extend(relativeTime);

export function formatAbs(iso: string): string {
  return dayjs(iso).format("YYYY-MM-DD HH:mm");
}
export function formatRel(iso: string): string {
  const d = dayjs(iso);
  if (d.isAfter(dayjs().subtract(1, "day"))) return d.fromNow();
  return d.format("YYYY-MM-DD");
}
export function remainingText(expIso: string): string {
  const exp = dayjs(expIso);
  const now = dayjs();
  if (!exp.isAfter(now)) return "已过期";
  const mins = exp.diff(now, "minute");
  if (mins < 60) return `剩 ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) {
    const m = mins % 60;
    return `剩 ${hours}h ${m.toString().padStart(2, "0")}m`;
  }
  return `剩 ${Math.floor(hours / 24)} 天`;
}
export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}
