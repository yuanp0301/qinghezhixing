<script setup lang="ts">
import { ref, watch } from "vue";
import type { ShareAccessLog } from "@/types/models";
import { listShareLogs } from "@/api/shares";
import { formatAbs } from "@/utils/time";

const props = defineProps<{
  modelValue: boolean;
  token: string | null;
}>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void }>();

const items = ref<ShareAccessLog[]>([]);
const total = ref(0);
const page = ref(1);
const size = 20;
const loading = ref(false);

async function reload() {
  if (!props.token) return;
  loading.value = true;
  try {
    const r = await listShareLogs(props.token, page.value, size);
    items.value = r.items;
    total.value = r.total;
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.modelValue, props.token],
  ([open]) => {
    if (open) {
      page.value = 1;
      reload();
    }
  },
);

const RESULT_LABEL: Record<ShareAccessLog["result"], string> = {
  success: "成功",
  expired: "已过期",
  revoked: "已撤销",
  not_found: "不存在",
};
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    title="分发链接访问记录"
    size="520"
    :destroy-on-close="true"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <div v-loading="loading">
      <el-table
        v-if="items.length"
        :data="items"
      >
        <el-table-column
          label="访问时间"
          width="170"
        >
          <template #default="{ row }">
            {{ formatAbs(row.viewed_at) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="client_ip_masked"
          label="IP"
          width="140"
        />
        <el-table-column label="UA">
          <template #default="{ row }">
            <span class="ua">{{ row.user_agent }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="结果"
          width="90"
        >
          <template #default="{ row }">
            {{ RESULT_LABEL[row.result as ShareAccessLog["result"]] }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty
        v-else
        description="暂无访问记录"
      />

      <div
        v-if="total > size"
        class="pager"
      >
        <el-pagination
          background
          layout="prev, pager, next"
          :total="total"
          :page-size="size"
          :current-page="page"
          @current-change="
            (p: number) => {
              page = p;
              reload();
            }
          "
        />
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.ua {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  max-width: 220px;
}
.pager {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
