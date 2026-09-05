<template>
  <div class="brand">
    <div class="mark">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      </svg>
    </div>
    <div class="text">
      <span class="name">面试大师</span>
      <span v-if="subtitle" class="sub">{{ subtitle }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ subtitle?: string }>(), { subtitle: '' })
</script>

<style scoped>
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
}
.mark {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--brand), var(--ai));
  color: #fff;
  display: grid;
  place-items: center;
  box-shadow: var(--shadow-md);
}
.mark svg {
  width: 21px;
  height: 21px;
}
.text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.name {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.3px;
}
.sub {
  font-size: 11px;
  color: var(--ink-400);
}
</style>
