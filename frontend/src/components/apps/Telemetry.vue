<template>
  <div class="p-6 space-y-6 text-slate-200">
    <!-- Grid: Top stats -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="p-4 rounded-xl glass-panel-light flex items-center gap-4">
        <div class="p-3 rounded-lg bg-blue-500/20 text-blue-400">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" /></svg>
        </div>
        <div>
          <div class="text-xs text-slate-400 font-semibold uppercase">CPU Load</div>
          <div class="text-2xl font-bold">{{ telemetry.cpu?.percent.toFixed(1) }}%</div>
          <div class="text-xs text-slate-500">{{ telemetry.cpu?.cores }} Cores</div>
        </div>
      </div>

      <div class="p-4 rounded-xl glass-panel-light flex items-center gap-4">
        <div class="p-3 rounded-lg bg-emerald-500/20 text-emerald-400">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
        </div>
        <div>
          <div class="text-xs text-slate-400 font-semibold uppercase">Memory Usage</div>
          <div class="text-2xl font-bold">{{ telemetry.memory?.percent.toFixed(1) }}%</div>
          <div class="text-xs text-slate-500">{{ formatBytes(telemetry.memory?.used) }} / {{ formatBytes(telemetry.memory?.total) }}</div>
        </div>
      </div>

      <div class="p-4 rounded-xl glass-panel-light flex items-center gap-4">
        <div class="p-3 rounded-lg bg-purple-500/20 text-purple-400">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z" /></svg>
        </div>
        <div>
          <div class="text-xs text-slate-400 font-semibold uppercase">CPU Temp</div>
          <div class="text-2xl font-bold">{{ telemetry.temperature }}°C</div>
          <div class="text-xs text-slate-500">Optimal</div>
        </div>
      </div>

      <div class="p-4 rounded-xl glass-panel-light flex items-center gap-4">
        <div class="p-3 rounded-lg bg-amber-500/20 text-amber-400">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        </div>
        <div>
          <div class="text-xs text-slate-400 font-semibold uppercase">Uptime</div>
          <div class="text-lg font-bold tracking-tight">{{ formatUptime(telemetry.uptime) }}</div>
          <div class="text-xs text-slate-500">System running</div>
        </div>
      </div>
    </div>

    <!-- Visual Dashboard Charts -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- CPU and Memory Ring meters -->
      <div class="p-6 rounded-2xl glass-panel-light">
        <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400 mb-6">Resource Allocation</h3>
        <div class="flex flex-around items-center justify-center gap-12">
          <!-- CPU circular gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-32 h-32">
              <svg class="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" r="54" stroke="rgba(255,255,255,0.05)" stroke-width="10" fill="transparent" />
                <circle cx="64" cy="64" r="54" stroke="#3b82f6" stroke-width="10" fill="transparent"
                  :stroke-dasharray="2 * Math.PI * 54"
                  :stroke-dashoffset="2 * Math.PI * 54 * (1 - (telemetry.cpu?.percent || 0) / 100)"
                  stroke-linecap="round" class="transition-all duration-500" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-xl font-bold">{{ telemetry.cpu?.percent.toFixed(0) }}%</span>
                <span class="text-[10px] text-slate-400 uppercase font-semibold">CPU</span>
              </div>
            </div>
            <div class="mt-3 text-xs text-slate-400">Load Average: {{ telemetry.cpu?.load_avg[0].toFixed(2) }}</div>
          </div>

          <!-- Memory circular gauge -->
          <div class="flex flex-col items-center">
            <div class="relative w-32 h-32">
              <svg class="w-full h-full transform -rotate-90">
                <circle cx="64" cy="64" r="54" stroke="rgba(255,255,255,0.05)" stroke-width="10" fill="transparent" />
                <circle cx="64" cy="64" r="54" stroke="#10b981" stroke-width="10" fill="transparent"
                  :stroke-dasharray="2 * Math.PI * 54"
                  :stroke-dashoffset="2 * Math.PI * 54 * (1 - (telemetry.memory?.percent || 0) / 100)"
                  stroke-linecap="round" class="transition-all duration-500" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-xl font-bold">{{ telemetry.memory?.percent.toFixed(0) }}%</span>
                <span class="text-[10px] text-slate-400 uppercase font-semibold">RAM</span>
              </div>
            </div>
            <div class="mt-3 text-xs text-slate-400">Free: {{ formatBytes(telemetry.memory?.available) }}</div>
          </div>
        </div>
      </div>

      <!-- Storage Devices Partition Capacity -->
      <div class="p-6 rounded-2xl glass-panel-light flex flex-col justify-between">
        <div>
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400 mb-6">Storage Volume Mounts</h3>
          <div class="space-y-4">
            <div v-for="disk in telemetry.disks" :key="disk.device" class="space-y-2">
              <div class="flex justify-between text-xs">
                <span class="font-semibold text-slate-300">{{ disk.mountpoint }} ({{ disk.device }})</span>
                <span class="text-slate-400">{{ formatBytes(disk.used) }} / {{ formatBytes(disk.total) }} ({{ disk.percent }}%)</span>
              </div>
              <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-500 to-indigo-600 h-full rounded-full" :style="{ width: `${disk.percent}%` }"></div>
              </div>
            </div>
            <div v-if="!telemetry.disks || telemetry.disks.length === 0" class="text-xs text-slate-500 py-4 text-center">
              No mounted local volumes found.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Network throughput -->
    <div class="p-6 rounded-2xl glass-panel-light">
      <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400 mb-4">Network Interface Traffic</h3>
      <div class="flex items-center justify-around text-center py-4">
        <div>
          <div class="text-xs text-slate-400 uppercase font-semibold mb-1">Total Data Sent</div>
          <div class="text-xl font-bold text-blue-400">{{ formatBytes(telemetry.network?.bytes_sent) }}</div>
        </div>
        <div class="h-10 w-[1px] bg-white/10"></div>
        <div>
          <div class="text-xs text-slate-400 uppercase font-semibold mb-1">Total Data Received</div>
          <div class="text-xl font-bold text-emerald-400">{{ formatBytes(telemetry.network?.bytes_recv) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  token: String
})

const telemetry = ref<any>({})
let timer: any = null

const fetchTelemetry = async () => {
  try {
    const res = await fetch('/api/system/telemetry', {
      headers: {
        'Authorization': `Bearer ${props.token}`
      }
    })
    if (res.ok) {
      telemetry.value = await res.json()
    }
  } catch (e) {
    console.error('Failed fetching telemetry', e)
  }
}

const formatBytes = (bytes: number) => {
  if (bytes === undefined || bytes === null || isNaN(bytes)) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatUptime = (seconds: number) => {
  if (!seconds) return '0s'
  const d = Math.floor(seconds / (3600 * 24))
  const h = Math.floor((seconds % (3600 * 24)) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  
  const parts = []
  if (d > 0) parts.push(`${d}d`)
  if (h > 0) parts.push(`${h}h`)
  if (m > 0) parts.push(`${m}m`)
  if (parts.length < 3) parts.push(`${s}s`)
  
  return parts.join(' ')
}

onMounted(() => {
  fetchTelemetry()
  timer = setInterval(fetchTelemetry, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
