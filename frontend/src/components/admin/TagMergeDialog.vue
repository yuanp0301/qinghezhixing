<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElMessageBox } from "element-plus";
import { mergeAdminTag } from "@/api/admin";
import { toastSuccess } from "@/utils/feedback";
import type { TagAdmin } from "@/types/models";

const props = defineProps<{
  visible: boolean;
  source: TagAdmin | null;
  allTags: TagAdmin[];
}>();
const emit = defineEmits<{
  (e: "update:visible", v: boolean): void;
  (e: "merged"): void;
}>();

const targetId = ref<number | undefined>();
const saving = ref(false);

const candidates = computed(() =>
  props.allTags.filter((t) => t.id !== props.source?.id),
);

watch(
  () => props.visible,
  (v) => {
    if (v) {
      targetId.value = undefined;
    }
  },
);

async function onConfirm() {
  if (!props.source || !targetId.value) return;
  const target = props.allTags.find((t) => t.id === targetId.value);
  if (!target) return;
  try {
    await ElMessageBox.confirm(
      `将 "${props.source.name}" 合并到 "${target.name}" 后，"${props.source.name}" 会被删除，` +
        `${props.source.content_count} 条内容的标签会被改为 "${target.name}"。`,
      "确认合并",
      {
        type: "warning",
        confirmButtonText: "确认合并",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }
  saving.value = true;
  try {
    await mergeAdminTag(props.source.id, targetId.value);
    toastSuccess("已合并");
    emit("merged");
    emit("update:visible", false);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="合并标签"
    width="440px"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
  >
    <el-form label-width="80px">
      <el-form-item label="源标签">
        <el-tag>{{ source?.name }}</el-tag>
      </el-form-item>
      <el-form-item label="合并到">
        <el-select
          v-model="targetId"
          placeholder="选择目标标签"
          filterable
          style="width: 100%"
        >
          <el-option
            v-for="t in candidates"
            :key="t.id"
            :label="t.name"
            :value="t.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:visible', false)">
        取消
      </el-button>
      <el-button
        type="primary"
        :disabled="!targetId"
        :loading="saving"
        @click="onConfirm"
      >
        合并
      </el-button>
    </template>
  </el-dialog>
</template>
