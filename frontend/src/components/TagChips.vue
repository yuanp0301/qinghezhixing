<script setup lang="ts">
import type { Tag } from "@/types/models";

defineProps<{
  tags: Tag[];
  max?: number;
}>();
const emit = defineEmits<{ (e: "click", t: Tag): void }>();
</script>
<template>
  <span class="chips">
    <template
      v-for="(t, i) in tags"
      :key="t.id"
    >
      <button
        v-if="max == null || i < max"
        class="chip"
        @click.prevent="emit('click', t)"
      >
        {{ t.name }}
      </button>
    </template>
    <span
      v-if="max != null && tags.length > max"
      class="chip more"
    >+{{ tags.length - max }}</span>
  </span>
</template>
<style scoped>
.chips {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  border: 1px solid var(--color-divider);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  padding: 2px 8px;
  font-size: 12px;
  border-radius: var(--radius-chip);
  cursor: pointer;
}
.chip:hover {
  color: var(--color-brand);
  border-color: var(--color-brand);
}
.chip.more {
  cursor: default;
}
</style>
