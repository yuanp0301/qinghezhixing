<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessageBox } from "element-plus";
import PageHeader from "@/components/PageHeader.vue";
import TagChips from "@/components/TagChips.vue";
import { listAdminContents, restoreContent } from "@/api/admin";
import { removeContent } from "@/api/contents";
import { toastSuccess } from "@/utils/feedback";
import { formatAbs, formatBytes } from "@/utils/time";
import type { ContentSummary } from "@/types/models";

const rows = ref<ContentSummary[]>([]);
const total = ref(0);
const loading = ref(false);
const page = ref(1);
const pageSize = 20;
const q = ref("");
const status = ref<"active" | "deleted" | undefined>();

async function reload() {
  loading.value = true;
  try {
    const data = await listAdminContents({
      q: q.value || undefined,
      status: status.value,
      page: page.value,
      size: pageSize,
    });
    rows.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

async function onDelete(row: ContentSummary) {
  try {
    await ElMessageBox.confirm(
      "删除后内容将不可访问，已生成的分发链接会一并失效。",
      "下架内容",
      {
        type: "warning",
        confirmButtonText: "确认下架",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }
  await removeContent(row.id);
  toastSuccess("已下架");
  reload();
}

async function onRestore(row: ContentSummary) {
  await restoreContent(row.id);
  toastSuccess("已恢复");
  reload();
}

function onPageChange(p: number) {
  page.value = p;
  reload();
}

onMounted(reload);
</script>

<template>
  <div class="page-wrap">
    <PageHeader title="全部内容" />

    <div class="filter-bar">
      <el-input
        v-model="q"
        placeholder="搜索标题"
        clearable
        style="width: 240px"
        @change="reload"
      />
      <el-select
        v-model="status"
        placeholder="状态"
        clearable
        style="width: 140px"
        @change="reload"
      >
        <el-option
          label="正常"
          value="active"
        />
        <el-option
          label="已删除"
          value="deleted"
        />
      </el-select>
    </div>

    <el-table
      v-loading="loading"
      :data="rows"
      stripe
    >
      <el-table-column
        label="标题"
        min-width="240"
      >
        <template #default="{ row }">
          <router-link
            :to="`/contents/${row.id}`"
            class="title-link"
          >
            {{ row.title }}
          </router-link>
        </template>
      </el-table-column>
      <el-table-column
        label="上传者"
        width="140"
      >
        <template #default="{ row }">
          {{ row.uploader_username }}
        </template>
      </el-table-column>
      <el-table-column
        label="标签"
        min-width="180"
      >
        <template #default="{ row }">
          <TagChips :tags="row.tags" />
        </template>
      </el-table-column>
      <el-table-column
        label="文件大小"
        width="120"
      >
        <template #default="{ row }">
          {{ formatBytes(row.size_bytes) }}
        </template>
      </el-table-column>
      <el-table-column
        label="状态"
        width="100"
      >
        <template #default="{ row }">
          <el-tag :type="row.status === 'deleted' ? 'info' : 'success'">
            {{ row.status === 'deleted' ? '已删除' : '正常' }}
          </el-tag>
        </template>
      </el-table-column>
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
        width="160"
        fixed="right"
      >
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'deleted'"
            link
            type="primary"
            @click="onRestore(row)"
          >
            恢复
          </el-button>
          <el-button
            v-else
            link
            type="danger"
            @click="onDelete(row)"
          >
            下架
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      class="pager"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next, total"
      @current-change="onPageChange"
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
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
.title-link {
  color: var(--color-brand);
  text-decoration: none;
}
.title-link:hover {
  text-decoration: underline;
}
</style>
