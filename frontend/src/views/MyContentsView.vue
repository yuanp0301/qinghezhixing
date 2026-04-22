<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import * as contentsApi from "@/api/contents";
import { listTags } from "@/api/tags";
import type { ContentSummary, Tag } from "@/types/models";
import PageHeader from "@/components/PageHeader.vue";
import EmptyState from "@/components/EmptyState.vue";
import TagChips from "@/components/TagChips.vue";
import { confirm, toastError, toastSuccess } from "@/utils/feedback";
import { formatAbs, formatBytes } from "@/utils/time";

const router = useRouter();
const items = ref<ContentSummary[]>([]);
const total = ref(0);
const page = ref(1);
const size = 20;
const q = ref("");
const tag = ref("");
const tags = ref<Tag[]>([]);
const loading = ref(false);

async function reload() {
  loading.value = true;
  try {
    const r = await contentsApi.listMine({
      q: q.value || undefined,
      tag: tag.value || undefined,
      page: page.value,
      size,
    });
    items.value = r.items;
    total.value = r.total;
  } catch {
    toastError("加载失败");
  } finally {
    loading.value = false;
  }
}

async function onDelete(it: ContentSummary) {
  const ok = await confirm(
    "删除内容",
    `“${it.title}” 删除后将不可访问，已生成的分发链接会一并失效。`,
    "确认删除",
    "danger",
  );
  if (!ok) return;
  await contentsApi.removeContent(it.id);
  toastSuccess("已删除");
  reload();
}

watch([q, tag], () => { page.value = 1; reload(); });
watch(page, reload);
onMounted(async () => {
  tags.value = await listTags().catch(() => []);
  reload();
});
</script>

<template>
  <PageHeader title="我的上传" :subtitle="`共 ${total} 条`">
    <template #actions>
      <el-button type="primary" @click="router.push('/contents/new')">
        上传
      </el-button>
    </template>
  </PageHeader>

  <div class="toolbar">
    <el-input v-model="q" placeholder="搜索标题" style="width: 320px" clearable />
    <el-select v-model="tag" placeholder="标签筛选" clearable filterable
      style="width: 200px">
      <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.name"/>
    </el-select>
  </div>

  <div v-loading="loading">
    <EmptyState
      v-if="!loading && items.length === 0"
      title="还没有上传过互动动画"
    >
      <el-button type="primary" @click="router.push('/contents/new')">上传</el-button>
    </EmptyState>

    <el-table v-else :data="items" stripe>
      <el-table-column label="标题">
        <template #default="{ row }">
          <a class="link" @click="router.push(`/contents/${row.id}`)">
            {{ row.title }}
          </a>
        </template>
      </el-table-column>
      <el-table-column label="标签">
        <template #default="{ row }">
          <TagChips :tags="row.tags" :max="3" />
        </template>
      </el-table-column>
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatAbs(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link @click="router.push(`/contents/${row.id}`)">观看</el-button>
          <el-button link @click="router.push(`/contents/${row.id}?edit=1`)">编辑</el-button>
          <el-button link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager" v-if="total > size">
      <el-pagination
        background layout="prev, pager, next"
        :total="total" :page-size="size"
        :current-page="page"
        @current-change="(p: number) => (page = p)"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: var(--space-5); }
.link { color: var(--color-brand); cursor: pointer; }
.pager { display: flex; justify-content: center; margin-top: 16px; }
</style>
