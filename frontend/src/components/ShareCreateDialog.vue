<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { createShare } from "@/api/shares";
import type { ShareLink } from "@/types/models";
import { toastError, toastSuccess } from "@/utils/feedback";

const props = defineProps<{
  modelValue: boolean;
  contentId: number;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "created", s: ShareLink): void;
}>();

const PRESETS = [
  { label: "1 小时", seconds: 3600 },
  { label: "24 小时", seconds: 86400 },
  { label: "7 天", seconds: 604800 },
  { label: "自定义", seconds: -1 },
];

const choice = ref(86400);
const customN = ref(30);
const customUnit = ref<"minute" | "hour" | "day">("minute");
const allowDownload = ref(false);
const submitting = ref(false);
const result = ref<ShareLink | null>(null);

const expiresInSeconds = computed(() => {
  if (choice.value !== -1) return choice.value;
  const m = { minute: 60, hour: 3600, day: 86400 }[customUnit.value];
  return Math.max(300, Math.min(2592000, customN.value * m));
});

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      result.value = null;
      choice.value = 86400;
      allowDownload.value = false;
    }
  },
);

async function onSubmit() {
  submitting.value = true;
  try {
    const s = await createShare(props.contentId, {
      expires_in_seconds: expiresInSeconds.value,
      allow_download: allowDownload.value,
    });
    result.value = s;
    emit("created", s);
  } catch {
    toastError("生成失败");
  } finally {
    submitting.value = false;
  }
}

async function copy(text: string) {
  await navigator.clipboard.writeText(text);
  toastSuccess("已复制");
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="result ? '链接已生成' : '生成分发链接'"
    width="520"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <div v-if="!result">
      <el-form label-position="top">
        <el-form-item label="有效期">
          <el-radio-group v-model="choice">
            <el-radio
              v-for="p in PRESETS"
              :key="p.label"
              :value="p.seconds"
            >
              {{ p.label }}
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item
          v-if="choice === -1"
          label="自定义时长"
        >
          <el-input-number
            v-model="customN"
            :min="1"
            :max="30"
          />
          <el-select
            v-model="customUnit"
            style="width: 100px; margin-left: 8px"
          >
            <el-option
              label="分钟"
              value="minute"
            />
            <el-option
              label="小时"
              value="hour"
            />
            <el-option
              label="天"
              value="day"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="允许下载原文件">
          <el-switch v-model="allowDownload" />
          <div class="hint">
            开启后，访客除了在线观看还可下载 HTML 源文件
          </div>
        </el-form-item>
      </el-form>
    </div>

    <div
      v-else
      class="result"
    >
      <el-input
        :model-value="result.url"
        readonly
      />
      <div class="row">
        <el-button @click="copy(result.url)">
          复制链接
        </el-button>
        <el-button @click="copy(`${result.url}\n有效期至 ${result.expires_at}`)">
          复制链接和有效期
        </el-button>
      </div>
      <p class="hint">
        链接将在 {{ result.expires_at }} 过期
      </p>
    </div>

    <template #footer>
      <template v-if="!result">
        <el-button @click="emit('update:modelValue', false)">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="onSubmit"
        >
          生成
        </el-button>
      </template>
      <template v-else>
        <el-button
          type="primary"
          @click="emit('update:modelValue', false)"
        >
          完成
        </el-button>
      </template>
    </template>
  </el-dialog>
</template>

<style scoped>
.hint {
  color: var(--color-text-secondary);
  font-size: 12px;
  margin-top: 4px;
}
.result {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.row {
  display: flex;
  gap: 8px;
}
</style>
