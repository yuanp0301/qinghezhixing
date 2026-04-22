<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { uploadContent } from "@/api/contents";
import { listTags } from "@/api/tags";
import type { Tag } from "@/types/models";
import PageHeader from "@/components/PageHeader.vue";
import { toastError, toastSuccess } from "@/utils/feedback";

const router = useRouter();
const title = ref("");
const description = ref("");
const tags = ref<string[]>([]);
const tagOptions = ref<Tag[]>([]);
const file = ref<File | null>(null);
const errorFile = ref("");
const submitting = ref(false);
const progress = ref(0);

(async () => { tagOptions.value = await listTags().catch(() => []); })();

const MAX = 10 * 1024 * 1024;

function onFileChange(f: File | null) {
  errorFile.value = "";
  if (!f) { file.value = null; return; }
  if (!f.name.toLowerCase().endsWith(".html")) {
    errorFile.value = "仅支持 .html 文件"; return;
  }
  if (f.size > MAX) {
    errorFile.value = `文件大小不能超过 10MB（当前 ${
      (f.size / 1024 / 1024).toFixed(1)
    } MB）`;
    return;
  }
  file.value = f;
}

function onUploadChange(f: { raw?: File }) {
  onFileChange(f.raw ?? null);
}

async function onSubmit() {
  if (!title.value) { toastError("请输入标题"); return; }
  if (!file.value) { toastError("请选择文件"); return; }
  if (tags.value.length > 10) { toastError("最多 10 个标签"); return; }
  submitting.value = true;
  progress.value = 0;
  try {
    const detail = await uploadContent(
      file.value,
      {
        title: title.value,
        description: description.value || undefined,
        tags: tags.value,
      },
      (p) => (progress.value = p),
    );
    toastSuccess("上传成功");
    router.push(`/contents/${detail.id}`);
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: unknown } } };
    const msg = err?.response?.data?.detail ?? "上传失败，请稍后重试";
    toastError(typeof msg === "string" ? msg : JSON.stringify(msg));
  } finally {
    submitting.value = false;
  }
}

function beforeUnloadHandler(e: BeforeUnloadEvent) {
  if (submitting.value || file.value || title.value || description.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}

onMounted(() => {
  window.addEventListener("beforeunload", beforeUnloadHandler);
});
onUnmounted(() => {
  window.removeEventListener("beforeunload", beforeUnloadHandler);
});
</script>

<template>
  <PageHeader title="上传互动动画" />

  <el-form label-position="top" class="form" @submit.prevent="onSubmit">
    <el-form-item label="标题" required>
      <el-input v-model="title" maxlength="100" show-word-limit />
    </el-form-item>
    <el-form-item label="标签">
      <el-select
        v-model="tags" multiple filterable allow-create
        default-first-option style="width: 100%"
      >
        <el-option v-for="t in tagOptions" :key="t.id"
          :label="t.name" :value="t.name" />
      </el-select>
    </el-form-item>
    <el-form-item label="简介">
      <el-input
        v-model="description" type="textarea" :rows="4"
        maxlength="500" show-word-limit
      />
    </el-form-item>
    <el-form-item label="HTML 文件" required :error="errorFile">
      <el-upload
        drag :auto-upload="false" :show-file-list="false"
        accept=".html"
        @change="onUploadChange"
      >
        <div v-if="!file" class="drop">
          <p>将 HTML 文件拖到此处，或点击选择</p>
          <p class="muted">仅支持 .html，≤ 10MB</p>
        </div>
        <div v-else class="picked">
          <div>{{ file.name }} · {{ (file.size / 1024).toFixed(1) }} KB</div>
          <el-button link @click.stop="file = null">移除</el-button>
        </div>
      </el-upload>
    </el-form-item>

    <el-progress
      v-if="submitting"
      :percentage="progress" :stroke-width="6"
    />

    <div class="footer">
      <el-button @click="router.back()">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="onSubmit">
        上传
      </el-button>
    </div>
  </el-form>
</template>

<style scoped>
.form { max-width: 720px; }
.drop {
  text-align: center; padding: 24px;
}
.muted { color: var(--color-text-secondary); font-size: 12px; }
.picked {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px;
}
.footer {
  display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px;
}
</style>
