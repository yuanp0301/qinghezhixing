<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import * as contentsApi from "@/api/contents";
import type { ContentDetail } from "@/types/models";
import HtmlSandboxFrame from "@/components/HtmlSandboxFrame.vue";
import TagChips from "@/components/TagChips.vue";
import { formatAbs, formatBytes } from "@/utils/time";
import { useAuthStore } from "@/stores/auth";
import { confirm, toastError, toastSuccess } from "@/utils/feedback";
import ShareCreateDialog from "@/components/ShareCreateDialog.vue";
import ShareLinkList from "@/components/ShareLinkList.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const data = ref<ContentDetail | null>(null);
const showEdit = ref(false);
const showShare = ref(false);
const editForm = ref({ title: "", description: "", tags: [] as string[] });

const id = computed(() => Number(route.params.id));
const canManage = computed(
  () =>
    !!data.value &&
    !!auth.user &&
    (auth.user.id === data.value.uploader_id || auth.user.role === "admin"),
);

async function load() {
  try {
    data.value = await contentsApi.detail(id.value);
    editForm.value = {
      title: data.value.title,
      description: data.value.description ?? "",
      tags: data.value.tags.map((t) => t.name),
    };
  } catch (e: any) {
    if (e?.response?.status === 404) data.value = null;
    else toastError("加载失败");
  }
}

async function onSaveEdit() {
  if (!data.value) return;
  try {
    data.value = await contentsApi.patchContent(data.value.id, {
      title: editForm.value.title,
      description: editForm.value.description || null,
      tags: editForm.value.tags,
    });
    toastSuccess("已保存");
    showEdit.value = false;
  } catch {
    toastError("保存失败");
  }
}

async function onDelete() {
  if (!data.value) return;
  const ok = await confirm(
    "删除内容",
    "删除后内容将不可访问，已生成的分发链接会一并失效。此操作不可撤销。",
    "确认删除",
    "danger",
  );
  if (!ok) return;
  await contentsApi.removeContent(data.value.id);
  toastSuccess("已删除");
  router.push("/contents");
}

onMounted(load);
</script>

<template>
  <div v-if="!data" class="empty-wrap">
    <el-empty description="内容不存在或已被删除">
      <el-button @click="router.push('/contents')">返回公开库</el-button>
    </el-empty>
  </div>

  <div v-else>
    <div class="breadcrumb">
      <router-link to="/contents">公开库</router-link>
      <span> / </span>
      <span>{{ data.title }}</span>
    </div>

    <div class="title-row">
      <h1>{{ data.title }}</h1>
      <div v-if="canManage" class="actions">
        <el-button @click="showEdit = true">编辑</el-button>
        <el-button type="primary" @click="showShare = true">
          生成分发链接
        </el-button>
        <el-button type="danger" plain @click="onDelete">删除</el-button>
      </div>
    </div>

    <div class="meta">
      <span>{{ data.uploader_username }}</span>
      <span>·</span><span>{{ formatAbs(data.created_at) }}</span>
      <span>·</span><span>{{ formatBytes(data.size_bytes) }}</span>
      <span>·</span><span>{{ data.original_filename }}</span>
    </div>
    <TagChips :tags="data.tags" @click="(t) => router.push({
      path: '/contents', query: { tag: t.name }
    })" />

    <HtmlSandboxFrame :src="`/view/${data.id}`" />

    <p v-if="data.description" class="desc">{{ data.description }}</p>

    <ShareLinkList
      v-if="canManage"
      :content-id="data.id"
      :refresh-key="showShare ? 0 : 1"
    />

    <el-drawer
      v-model="showEdit" title="编辑内容" size="440"
      :destroy-on-close="true"
    >
      <el-form label-position="top" @submit.prevent="onSaveEdit">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="editForm.tags"
            multiple filterable allow-create default-first-option
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="简介">
          <el-input
            v-model="editForm.description" type="textarea"
            :rows="4" maxlength="500" show-word-limit
          />
        </el-form-item>
        <el-button type="primary" @click="onSaveEdit">保存</el-button>
      </el-form>
    </el-drawer>

    <ShareCreateDialog
      v-model="showShare"
      :content-id="data.id"
      @created="() => { /* 列表自刷新 */ }"
    />
  </div>
</template>

<style scoped>
.empty-wrap { display: flex; justify-content: center; padding: 64px; }
.breadcrumb {
  margin-bottom: 8px; color: var(--color-text-secondary); font-size: 13px;
}
.breadcrumb a { color: var(--color-text-secondary); }
.title-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
h1 { font-size: var(--font-size-h1); margin: 0; font-weight: 500; }
.actions { display: flex; gap: 8px; }
.meta {
  display: flex; gap: 6px; flex-wrap: wrap;
  color: var(--color-text-secondary); font-size: 13px;
  margin-bottom: 8px;
}
.desc {
  margin: 16px 0; white-space: pre-wrap;
  color: var(--color-text);
}
</style>
