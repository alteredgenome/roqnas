<template>
  <div class="h-full flex flex-col text-slate-200">
    <div class="flex items-center justify-between px-6 py-3 border-b border-white/5 bg-white/5">
      <span class="text-xs text-slate-400 font-semibold uppercase">System Event Audit Trail (journald)</span>
      <button @click="fetchLogs" class="px-2 py-1 bg-white/5 hover:bg-white/10 rounded border border-white/10 text-xs flex items-center gap-1 transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18.2" /></svg>
        <span>Refresh</span>
      </button>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <div class="font-mono text-xs bg-slate-900/60 border border-white/5 rounded-xl p-4 space-y-1 select-text">
        <div v-for="(line, idx) in logs" :key="idx" class="whitespace-pre-wrap leading-relaxed py-0.5 hover:bg-white/5 px-1.5 rounded transition">
          <span class="text-slate-500 font-semibold">{{ idx + 1 }}.</span> {{ line }}
        </div>
        <div v-if="logs.length === 0" class="text-slate-500 text-center py-4">No events found.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps({
  token: String
})

const logs = ref<string[]>([])

const fetchLogs = async () => {
  try {
    const res = await fetch('/api/system/logs?lines=60', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      logs.value = await res.json()
    }
  } catch (e) {
    logs.value = ['Error retrieving system logs.']
  }
}

onMounted(() => {
  fetchLogs()
})
</script>
