<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>();
</script>
<template>
  <div class="page-header">
    <div class="left">
      <h1>{{ title }}</h1>
      <div v-if="subtitle" class="sub">{{ subtitle }}</div>
    </div>
    <div class="right"><slot name="actions" /></div>
  </div>
</template>
<style scoped>
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-5);
}
h1 { font-size: var(--font-size-h2); margin: 0; font-weight: 500; }
.sub {
  color: var(--color-text-secondary);
  font-size: var(--font-size-secondary);
  margin-top: 4px;
}
</style>
