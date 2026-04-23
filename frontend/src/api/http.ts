import axios, { AxiosError } from "axios";
import { toastError } from "@/utils/feedback";

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "",
  withCredentials: true,
  timeout: 30_000,
});

let isRedirectingToLogin = false;

http.interceptors.response.use(
  (r) => r,
  (err: AxiosError<any>) => {
    const status = err.response?.status;
    if (
      status === 401 &&
      !isRedirectingToLogin &&
      !location.pathname.startsWith("/login")
    ) {
      isRedirectingToLogin = true;
      const next = encodeURIComponent(location.pathname + location.search);
      location.assign(`/login?next=${next}`);
      return Promise.reject(err);
    }
    if (status === 403) {
      toastError("无权限");
    } else if (status === 429) {
      toastError("访问过于频繁，请稍后再试");
    } else if (!err.response) {
      toastError("网络异常，请重试");
    }
    return Promise.reject(err);
  },
);
