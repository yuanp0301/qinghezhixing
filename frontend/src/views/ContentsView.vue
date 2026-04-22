<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import * as contentsApi from "@/api/contents";
import { listTags } from "@/api/tags";
import type { ContentSummary, Tag } from "@/types/models";
import PageHeader from "@/components/PageHeader.vue";
import EmptyState from "@/components/EmptyState.vue";
import ContentCard from "@/components/ContentCard.vue";
import { useAuthStore } from "@/stores/auth";
import { toastError } from "@/utils/feedback";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const q = ref((route.query.q as string) || "");
const tag = ref((route.query.tag as string) || "");
const order = ref(((route.query.order as string) || "newest") as
  "newest" | "oldest");
const page = ref(parseInt((route.query.page as string) || "1", 10));
const size = 24;

const items = ref<ContentSummary[]>([]);
const total = ref(0);
const loading = ref(false);
const tags = ref<Tag[]>([]);

const hasFilter = computed(
  () => Boolean(q.value || tag.value || order.value !== "newest"),
);

const canUpload = computed(
  () => !!auth.user && ["creator", "admin"].includes(auth.user.role),
);

async function reload() {
  loading.value = true;
  try {
    const r = await contentsApi.listPublic({
      q: q.value || undefined,
      tag: tag.value || undefined,
      order: order.value,
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

function syncQuery() {
  router.replace({
    query: {
      q: q.value || undefined,
      tag: tag.value || undefined,
      order: order.value === "newest" ? undefined : order.value,
      page: page.value === 1 ? undefined : String(page.value),
    },
  });
}

watch([q, tag, order], () => { page.value = 1; syncQuery(); reload(); });
watch(page, () => { syncQuery(); reload(); });

function clearAll() {
  q.value = ""; tag.value = ""; order.value = "newest";
  page.value = 1; syncQuery(); reload();
}

onMounted(async () => {
  tags.value = await listTags().catch(() => []);
  await reload();
});

function go(item: ContentSummary) {
  router.push(`/contents/${item.id}`);
}
</script>

<template>
  <PageHeader title="公开库" :subtitle="`共 ${total} 条`">
    <template #actions>
      <el-button v-if="canUpload" type="primary"
        @click="router.push('/contents/new')">上传</el-button>
    </template>
  </PageHeader>

  <div class="toolbar">
    <el-input
      v-model="q" placeholder="搜索标题"
      style="width: 320px"
      :prefix-icon="undefined"
      clearable
    />
    <el-select
      v-model="tag" placeholder="标签筛选"
      clearable filterable style="width: 200px"
    >
      <el-option
        v-for="t in tags" :key="t.id"
        :label="t.name" :value="t.name"
      />
    </el-select>
    <el-select v-model="order" style="width: 140px">
      <el-option label="最新上传" value="newest" />
      <el-option label="最早上传" value="oldest" />
    </el-select>
    <el-button v-if="hasFilter" link @click="clearAll">清空筛选</el-button>
  </div>

  <div v-loading="loading">
    <EmptyState
      v-if="!loading && items.length === 0 && !hasFilter"
      title="这里还没有互动动画"
      description="联系制作者上传第一份内容吧"
    >
      <el-button v-if="canUpload" type="primary"
        @click="router.push('/contents/new')">上传</el-button>
    </EmptyState>

    <EmptyState
      v-else-if="!loading && items.length === 0"
      :title="`没有匹配 “${q}” 的内容`"
    >
      <el-button @click="clearAll">清空筛选</el-button>
    </EmptyState>

    <div v-else class="grid">
      <ContentCard
        v-for="it in items"
        :key="it.id"
        :item="it"
        @click="go(it)"
        @tag="(name) => { tag = name; }"
      />
    </div>
  </div>

  <div class="pager">
    <el-pagination
      background layout="prev, pager, next"
      :total="total" :page-size="size"
      :current-page="page"
      @current-change="(p: number) => (page = p)"
    />
  </div>
</template>

<style scoped>
.toolbar {
  display: flex; gap: 12px; align-items: center;
  margin-bottom: var(--space-5);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-4);
}
.pager {
  display: flex; justify-content: center; margin-top: var(--space-5);
}
</style>
