<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>
<template>
  <div class="empty">
    <svg
      width="56"
      height="56"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#a1a1a6"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M4 7h16M4 12h16M4 17h10" />
    </svg>
    <h3>{{ title }}</h3>
    <p v-if="description">
      {{ description }}
    </p>
    <div class="action">
      <slot />
    </div>
  </div>
</template>
<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 64px 24px;
  gap: 12px;
  color: var(--color-text-secondary);
}
.empty h3 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--font-size-h3);
  font-weight: 500;
}
.empty p {
  margin: 0;
}
.action {
  margin-top: 12px;
}
</style>
