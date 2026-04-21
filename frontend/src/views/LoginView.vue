<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login } from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import { toastError } from "@/utils/feedback";
import BrandLogo from "@/components/BrandLogo.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const username = ref("");
const password = ref("");
const submitting = ref(false);
const errorBanner = ref("");

async function onSubmit() {
  errorBanner.value = "";
  if (!username.value || !password.value) {
    errorBanner.value = "请输入用户名与密码";
    return;
  }
  submitting.value = true;
  try {
    const u = await login(username.value, password.value);
    auth.setUser(u);
    const next = (route.query.next as string) || "/contents";
    router.push(next);
  } catch (e: any) {
    const status = e?.response?.status;
    if (status === 401) errorBanner.value = "用户名或密码错误";
    else if (status === 403) errorBanner.value = "账号已被禁用，请联系管理员";
    else toastError("登录失败，请稍后重试");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <BrandLogo />
      <h1>欢迎登录</h1>
      <el-alert
        v-if="errorBanner"
        :title="errorBanner"
        type="error"
        :closable="false"
        show-icon
      />
      <el-form @submit.prevent="onSubmit" label-position="top">
        <el-form-item label="用户名">
          <el-input
            v-model="username"
            autocomplete="username"
            placeholder="请输入用户名"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            show-password
            autocomplete="current-password"
            placeholder="请输入密码"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button
          type="primary"
          :loading="submitting"
          @click="onSubmit"
          style="width: 100%; height: var(--control-h-primary)"
        >
          登录
        </el-button>
      </el-form>
      <p class="hint">如需账号，请联系管理员。</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-bg-soft);
}
.card {
  width: 400px; padding: 32px;
  background: var(--color-bg);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  display: flex; flex-direction: column; gap: 16px;
}
h1 {
  font-size: var(--font-size-h2);
  font-weight: 500; margin: 0;
}
.hint {
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
  margin: 0; text-align: center;
}
</style>
