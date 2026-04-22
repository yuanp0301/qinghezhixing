<script setup lang="ts">
import { ref } from "vue";
import { resetUserPassword } from "@/api/admin";
import { toastError, toastSuccess } from "@/utils/feedback";
import type { UserAdmin } from "@/types/models";

const props = defineProps<{ visible: boolean; user: UserAdmin | null }>();
const emit = defineEmits<{ (e: "update:visible", v: boolean): void }>();

const loading = ref(false);
const password = ref<string | null>(null);

async function onOpen() {
  if (!props.user) return;
  loading.value = true;
  password.value = null;
  try {
    const data = await resetUserPassword(props.user.id);
    password.value = data.new_password;
  } finally {
    loading.value = false;
  }
}

function onClose() {
  password.value = null;
}

async function copy() {
  if (!password.value) return;
  try {
    await navigator.clipboard.writeText(password.value);
    toastSuccess("已复制");
  } catch {
    toastError("复制失败，请手动复制");
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="重置密码"
    width="440px"
    :close-on-click-modal="false"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    @open="onOpen"
    @close="onClose"
  >
    <div
      v-if="loading"
      class="loading"
    >
      生成中…
    </div>
    <div
      v-else-if="password"
      class="result"
    >
      <p class="hint">
        已为 <b>{{ user?.username }}</b> 生成新密码：
      </p>
      <div class="pw-box">
        <code>{{ password }}</code>
        <el-button
          type="primary"
          link
          @click="copy"
        >
          复制
        </el-button>
      </div>
      <p class="warn">
        请线下转交用户，关闭后无法再次查看。
      </p>
    </div>
    <template #footer>
      <el-button
        type="primary"
        @click="emit('update:visible', false)"
      >
        完成
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.loading {
  text-align: center;
  padding: 24px;
  color: var(--color-text-secondary);
}
.result .hint {
  margin: 0 0 12px;
}
.pw-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--color-bg-subtle);
  border-radius: 8px;
  font-family: ui-monospace, Menlo, monospace;
  font-size: 16px;
}
.warn {
  margin-top: 12px;
  color: var(--color-warning);
  font-size: 13px;
}
</style>
