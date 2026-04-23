<script setup lang="ts">
import { ref, watch } from "vue";
import { listOfflineOpens } from "@/api/shares";
import type { OfflineOpenLog } from "@/types/models";
import { formatAbs } from "@/utils/time";

const props = defineProps<{
  modelValue: boolean;
  contentId: number;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
}>();

const loading = ref(false);
const rows = ref<OfflineOpenLog[]>([]);
const total = ref(0);
const page = ref(1);
const size = 20;

async function reload() {
  if (!props.modelValue) return;
  loading.value = true;
  try {
    const res = await listOfflineOpens(props.contentId, page.value, size);
    rows.value = res.items;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return;
    page.value = 1;
    reload();
  },
);

function onPageChange(p: number) {
  page.value = p;
  reload();
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="下载使用信息"
    width="900"
    @update:model-value="(v:boolean) => emit('update:modelValue', v)"
  >
    <el-table
      v-loading="loading"
      :data="rows"
      stripe
      empty-text="暂无下载使用记录"
    >
      <el-table-column
        label="用户信息"
        min-width="140"
      >
        <template #default="{ row }">
          {{ row.user_info || "-" }}
        </template>
      </el-table-column>
      <el-table-column
        label="打开时间"
        width="180"
      >
        <template #default="{ row }">
          {{ row.opened_at ? formatAbs(row.opened_at) : "-" }}
        </template>
      </el-table-column>
      <el-table-column
        label="上报时间"
        width="180"
      >
        <template #default="{ row }">
          {{ formatAbs(row.reported_at) }}
        </template>
      </el-table-column>
      <el-table-column
        label="上报方式"
        width="120"
      >
        <template #default="{ row }">
          <el-tag :type="row.is_offline_replay ? 'warning' : 'success'">
            {{ row.is_offline_replay ? "离线补报" : "在线上报" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        label="浏览器"
        min-width="220"
      >
        <template #default="{ row }">
          <span class="ua">{{ row.user_agent || "-" }}</span>
        </template>
      </el-table-column>
      <el-table-column
        label="链接Key"
        min-width="220"
      >
        <template #default="{ row }">
          <span class="mono">{{ row.token }}</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="size"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="onPageChange"
      />
    </div>
  </el-dialog>
</template>

<style scoped>
.pager {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}
.ua {
  color: var(--color-text-secondary);
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
</style>
