<script setup lang="ts">
defineProps<{ small?: boolean }>();
</script>
<template>
  <div
    class="brand"
    :class="{ small }"
  >
    <span class="dot" />
    <span class="name">青禾知行</span>
  </div>
</template>
<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.brand .dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-brand);
}
.brand .name {
  font-weight: 500;
}
.brand.small .name {
  font-size: 13px;
}
</style>
