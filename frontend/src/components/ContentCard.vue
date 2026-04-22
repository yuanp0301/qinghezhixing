<script setup lang="ts">
import type { ContentSummary } from "@/types/models";
import TagChips from "./TagChips.vue";
import { formatRel } from "@/utils/time";

defineProps<{ item: ContentSummary }>();
const emit = defineEmits<{
  (e: "click"): void;
  (e: "tag", name: string): void;
}>();
</script>
<template>
  <article
    class="card"
    @click="emit('click')"
  >
    <div class="thumb">
      <svg
        width="36"
        height="36"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#a1a1a6"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
      </svg>
    </div>
    <h3 class="title">
      {{ item.title }}
    </h3>
    <div class="meta">
      <span>{{ item.uploader_username }}</span>
      <span>·</span>
      <span>{{ formatRel(item.created_at) }}</span>
    </div>
    <TagChips
      :tags="item.tags"
      :max="3"
      @click="(t) => emit('tag', t.name)"
    />
  </article>
</template>
<style scoped>
.card {
  background: var(--color-bg);
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-card);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: var(--motion-fast);
  cursor: pointer;
}
.card:hover {
  box-shadow: var(--shadow-card);
  transform: translateY(-1px);
}
.thumb {
  height: 96px;
  border-radius: 8px;
  background: var(--color-bg-soft);
  display: flex;
  align-items: center;
  justify-content: center;
}
.title {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  display: flex;
  gap: 6px;
  color: var(--color-text-secondary);
  font-size: 12px;
}
</style>
