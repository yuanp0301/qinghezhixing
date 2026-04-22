<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  src: string;
}>();
const loaded = ref(false);
const errored = ref(false);

function reload() {
  loaded.value = false;
  errored.value = false;
  const f = document.querySelector(
    "iframe.sandbox-frame",
  ) as HTMLIFrameElement | null;
  if (f) f.src = props.src;
}

function openNewWindow() {
  window.open(props.src, "_blank");
}
</script>

<template>
  <div class="frame-wrap">
    <div v-if="!loaded && !errored" class="overlay">正在加载互动内容…</div>
    <div v-if="errored" class="overlay error">
      <p>内容加载失败</p>
      <el-button size="small" @click="reload">重试</el-button>
    </div>
    <iframe
      class="sandbox-frame"
      :src="src"
      sandbox="allow-scripts"
      @load="loaded = true"
      @error="errored = true"
    />
    <div class="tools">
      <el-button size="small" link @click="
        ($event.currentTarget as HTMLElement)
          .closest('.frame-wrap')!.requestFullscreen()
      ">全屏</el-button>
      <el-button size="small" link @click="openNewWindow">
        在新窗口打开
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.frame-wrap {
  position: relative;
  background: #000; border-radius: var(--radius-card);
  overflow: hidden;
  aspect-ratio: 16 / 9;
}
iframe {
  width: 100%; height: 100%; border: 0; display: block;
}
.overlay {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #fff; background: rgba(0,0,0,.6);
  flex-direction: column; gap: 12px;
}
.tools {
  position: absolute; top: 8px; right: 8px;
  display: flex; gap: 6px;
  background: rgba(0,0,0,.4); padding: 4px 8px; border-radius: 8px;
}
.tools .el-button { color: #fff; }
</style>
