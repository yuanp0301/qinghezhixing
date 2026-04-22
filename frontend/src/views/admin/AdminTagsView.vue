<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessageBox } from "element-plus";
import { AxiosError } from "axios";
import PageHeader from "@/components/PageHeader.vue";
import TagMergeDialog from "@/components/admin/TagMergeDialog.vue";
import {
  createAdminTag,
  deleteAdminTag,
  listAdminTags,
  renameAdminTag,
} from "@/api/admin";
import { toastError, toastSuccess } from "@/utils/feedback";
import { formatAbs } from "@/utils/time";
import type { TagAdmin } from "@/types/models";

const rows = ref<TagAdmin[]>([]);
const loading = ref(false);
const q = ref("");

const editingId = ref<number | null>(null);
const editingName = ref("");

const mergeVisible = ref(false);
const mergingSource = ref<TagAdmin | null>(null);

async function reload() {
  loading.value = true;
  try {
    rows.value = await listAdminTags(q.value || undefined);
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  let value: string;
  try {
    const res = await ElMessageBox.prompt("请输入标签名（1–20 字）", "新建标签", {
      inputPattern: /^.{1,20}$/,
      inputErrorMessage: "1–20 字",
      confirmButtonText: "确定",
      cancelButtonText: "取消",
    });
    value = res.value;
  } catch {
    return;
  }
  try {
    await createAdminTag(value);
    toastSuccess("已创建");
    reload();
  } catch (err) {
    const ax = err as AxiosError;
    if (ax.response?.status === 409) {
      toastError("标签名已存在");
    } else {
      throw err;
    }
  }
}

function startRename(row: TagAdmin) {
  editingId.value = row.id;
  editingName.value = row.name;
}

function cancelRename() {
  editingId.value = null;
  editingName.value = "";
}

async function commitRename(row: TagAdmin) {
  if (!editingName.value || editingName.value === row.name) {
    cancelRename();
    return;
  }
  try {
    await renameAdminTag(row.id, editingName.value);
    toastSuccess("已重命名");
    cancelRename();
    reload();
  } catch (err) {
    const ax = err as AxiosError;
    if (ax.response?.status === 409) {
      toastError("标签名已存在");
    } else {
      throw err;
    }
  }
}

function openMerge(row: TagAdmin) {
  mergingSource.value = row;
  mergeVisible.value = true;
}

async function onDelete(row: TagAdmin) {
  try {
    await ElMessageBox.confirm(`确认删除标签 "${row.name}"？`, "删除标签", {
      type: "warning",
      confirmButtonText: "确认删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await deleteAdminTag(row.id);
    toastSuccess("已删除");
    reload();
  } catch (err) {
    const ax = err as AxiosError;
    if (ax.response?.status === 409) {
      toastError("标签仍被内容引用，无法删除");
    } else {
      throw err;
    }
  }
}

onMounted(reload);
</script>

<template>
  <div class="page-wrap">
    <PageHeader title="标签管理">
      <template #actions>
        <el-button
          type="primary"
          @click="onCreate"
        >
          新建标签
        </el-button>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <el-input
        v-model="q"
        placeholder="搜索标签"
        clearable
        style="width: 240px"
        @change="reload"
      />
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      stripe
    >
      <el-table-column
        label="标签名"
        min-width="200"
      >
        <template #default="{ row }">
          <span v-if="editingId !== row.id">{{ row.name }}</span>
          <el-input
            v-else
            v-model="editingName"
            size="small"
            @keyup.enter="commitRename(row)"
          />
        </template>
      </el-table-column>
      <el-table-column
        prop="content_count"
        label="关联内容数"
        width="140"
      />
      <el-table-column
        label="创建时间"
        width="170"
      >
        <template #default="{ row }">
          {{ formatAbs(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column
        label="操作"
        width="280"
        fixed="right"
      >
        <template #default="{ row }">
          <template v-if="editingId === row.id">
            <el-button
              link
              type="primary"
              @click="commitRename(row)"
            >
              保存
            </el-button>
            <el-button
              link
              @click="cancelRename"
            >
              取消
            </el-button>
          </template>
          <template v-else>
            <el-button
              link
              type="primary"
              @click="startRename(row)"
            >
              重命名
            </el-button>
            <el-button
              link
              type="primary"
              @click="openMerge(row)"
            >
              合并到…
            </el-button>
            <el-button
              link
              type="danger"
              :disabled="row.content_count > 0"
              @click="onDelete(row)"
            >
              删除
            </el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <TagMergeDialog
      v-model:visible="mergeVisible"
      :source="mergingSource"
      :all-tags="rows"
      @merged="reload"
    />
  </div>
</template>

<style scoped>
.page-wrap {
  padding: 24px 32px;
}
.filter-bar {
  display: flex;
  gap: 12px;
  margin: 16px 0;
}
</style>
