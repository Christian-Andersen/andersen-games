<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

const clicks = ref<number[]>([]);
const cps = ref(0);

const handleClick = () => {
	const now = Date.now();
	clicks.value.push(now);
	updateCPS();
};

const updateCPS = () => {
	const now = Date.now();
	clicks.value = clicks.value.filter((t) => now - t < 5000);
	cps.value = clicks.value.length / 5;
};

let interval: ReturnType<typeof setInterval> | undefined;

onMounted(() => {
	interval = setInterval(updateCPS, 100);
});

onUnmounted(() => clearInterval(interval));
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-5">
    <h2 class="text-4xl font-black text-white">Clicks Per Second</h2>
    <p class="text-neutral-400">Click as fast as you can! (5s average)</p>

    <div class="my-5 text-center">
      <div class="text-7xl font-bold leading-none text-emerald-500">{{ cps.toFixed(1) }}</div>
      <div class="text-xl text-neutral-500">CPS</div>
    </div>

    <button
      @click="handleClick"
      class="h-48 w-48 cursor-pointer rounded-full border-none bg-slate-700 text-xl font-bold text-white shadow-[0_10px_0_#1e293b] transition-transform duration-75 active:translate-y-1 active:shadow-[0_5px_0_#1e293b]"
    >
      CLICK!
    </button>

    <div class="mt-5 text-neutral-500">Total clicks in last 5s: {{ clicks.length }}</div>
  </div>
</template>
