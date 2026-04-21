import { ElMessage, ElMessageBox } from "element-plus";

export function toastSuccess(msg: string) {
  ElMessage({ type: "success", message: msg, duration: 3000 });
}
export function toastError(msg: string) {
  ElMessage({ type: "error", message: msg, duration: 5000 });
}
export function toastInfo(msg: string) {
  ElMessage({ type: "info", message: msg });
}
export async function confirm(
  title: string,
  message: string,
  confirmText = "确认",
  type: "warning" | "danger" = "warning",
): Promise<boolean> {
  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText: confirmText,
      cancelButtonText: "取消",
      type: type === "danger" ? "warning" : "warning",
      confirmButtonClass:
        type === "danger" ? "el-button--danger" : undefined,
    });
    return true;
  } catch {
    return false;
  }
}
