<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { listShares, revokeShare } from "@/api/shares";
import type { ShareLink } from "@/types/models";
import { confirm, toastError, toastSuccess } from "@/utils/feedback";
import { formatAbs, remainingText } from "@/utils/time";
import ShareAccessDrawer from "./ShareAccessDrawer.vue";

const props = defineProps<{
  contentId: number;
  refreshKey?: number;
}>();

const items = ref<ShareLink[]>([]);
const expanded = ref(false);
const drawerToken = ref<string | null>(null);
const drawerOpen = ref(false);
const loading = ref(false);

const stats = computed(() => {
  const valid = items.value.filter((s) => s.state === "active").length;
  return { valid, total: items.value.length };
});

async function reload() {
  loading.value = true;
  try {
    items.value = await listShares(props.contentId);
  } catch {
    toastError("加载失败");
  } finally {
    loading.value = false;
  }
}

async function copy(url: string) {
  await navigator.clipboard.writeText(url);
  toastSuccess("已复制");
}

async function revoke(s: ShareLink) {
  const ok = await confirm(
    "撤销分发链接",
    "撤销后此链接立即失效，已通过它打开页面的访客刷新后将看到失效提示。确定撤销？",
    "撤销",
    "danger",
  );
  if (!ok) return;
  await revokeShare(s.token);
  toastSuccess("已撤销");
  reload();
}

function openLogs(s: ShareLink) {
  drawerToken.value = s.token;
  drawerOpen.value = true;
}

function shortToken(t: string) {
  if (t.length <= 14) return t;
  return `${t.slice(0, 8)}…${t.slice(-4)}`;
}

const STATE_TYPE: Record<ShareLink["state"], string> = {
  active: "success",
  expired: "info",
  revoked: "danger",
};
const STATE_LABEL: Record<ShareLink["state"], string> = {
  active: "有效", expired: "已过期", revoked: "已撤销",
};

onMounted(reload);
watch(() => props.refreshKey, reload);
</script>

<template>
  <section class="block">
    <header @click="expanded = !expanded">
      <h3>分发链接（{{ stats.total }}）</h3>
      <span class="stat">
        有效 {{ stats.valid }} / 总 {{ stats.total }}
      </span>
      <el-button link @click.stop="expanded = !expanded">
        {{ expanded ? "收起" : "展开" }}
      </el-button>
    </header>

    <div v-if="expanded" v-loading="loading" class="body">
      <el-table :data="items" v-if="items.length">
        <el-table-column label="链接" width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.url">
              <span class="link" @click="copy(row.url)">
                /s/{{ shortToken(row.token) }}
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="STATE_TYPE[row.state as ShareLink['state']] as any" size="small">
              {{ STATE_LABEL[row.state as ShareLink['state']] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="倒计时" width="120">
          <template #default="{ row }">
            <span v-if="row.state === 'active'">
              {{ remainingText(row.expires_at) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="允许下载" width="90">
          <template #default="{ row }">
            {{ row.allow_download ? "是" : "否" }}
          </template>
        </el-table-column>
        <el-table-column label="生成时间" width="170">
          <template #default="{ row }">{{ formatAbs(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link @click="copy(row.url)">复制</el-button>
            <el-button link @click="openLogs(row)">访问记录</el-button>
            <el-button
              link type="danger"
              :disabled="row.state !== 'active'"
              @click="revoke(row)"
            >撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="还没有生成分发链接" />
    </div>

    <ShareAccessDrawer
      v-model="drawerOpen"
      :token="drawerToken"
    />
  </section>
</template>

<style scoped>
.block {
  margin-top: var(--space-5);
  background: var(--color-bg);
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-card);
  padding: 16px 20px;
}
header {
  display: flex; align-items: center; gap: 12px; cursor: pointer;
}
header h3 {
  margin: 0; font-size: 15px; font-weight: 500;
}
.stat {
  margin-left: auto; color: var(--color-text-secondary); font-size: 12px;
}
.body { margin-top: 12px; }
.link { color: var(--color-brand); cursor: pointer; }
</style>
