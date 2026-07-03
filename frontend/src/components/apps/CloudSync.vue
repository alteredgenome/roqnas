<template>
  <div class="h-full flex flex-col text-slate-200">
    <div class="flex-1 overflow-auto p-6 space-y-6">
      
      <!-- List active Cloud Sync Tasks -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Cloud Sync Tasks</h3>
          <button @click="fetchTasks" class="p-1 hover:bg-white/5 rounded text-slate-400 hover:text-slate-200 transition">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18.2" /></svg>
          </button>
        </div>

        <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
          <table class="w-full border-collapse text-left text-xs">
            <thead>
              <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                <th class="p-3">Profile Name</th>
                <th class="p-3">ZFS Dataset Source</th>
                <th class="p-3">Target Bucket (Provider)</th>
                <th class="p-3">Schedule</th>
                <th class="p-3">Last Sync</th>
                <th class="p-3">Status</th>
                <th class="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr v-for="task in tasks" :key="task.id" class="hover:bg-white/5">
                <td class="p-3 font-semibold text-blue-400">{{ task.name }}</td>
                <td class="p-3 font-mono text-[11px] text-slate-300">{{ task.local_path }}</td>
                <td class="p-3 font-mono text-slate-300">
                  <span class="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 uppercase font-semibold mr-1.5">{{ task.provider }}</span>
                  <span>{{ task.bucket }}</span>
                </td>
                <td class="p-3 font-mono text-slate-400">{{ task.schedule }}</td>
                <td class="p-3 font-mono text-slate-400">{{ task.last_run }}</td>
                <td class="p-3">
                  <div class="flex flex-col gap-1 w-24">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded w-max capitalize"
                      :class="{
                        'bg-slate-800 text-slate-400': task.status === 'idle',
                        'bg-blue-500/20 text-blue-400 animate-pulse': task.status === 'syncing',
                        'bg-emerald-500/20 text-emerald-400': task.status === 'success',
                        'bg-red-500/20 text-red-400': task.status === 'failed'
                      }">
                      {{ task.status }}
                    </span>
                    <!-- Progress bar -->
                    <div v-if="task.status === 'syncing'" class="w-full bg-slate-800 h-1 rounded overflow-hidden mt-1">
                      <div class="bg-blue-500 h-full transition-all duration-300" :style="{ width: `${task.progress}%` }"></div>
                    </div>
                  </div>
                </td>
                <td class="p-3 text-right space-x-1.5">
                  <button :disabled="task.status === 'syncing'" @click="runSync(task.id)" class="px-2 py-1 bg-emerald-600/20 border border-emerald-500/30 hover:bg-emerald-600 hover:text-white rounded text-xs transition disabled:opacity-20 disabled:pointer-events-none">Sync</button>
                  <button :disabled="task.status === 'syncing'" @click="deleteTask(task.id)" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition disabled:opacity-20 disabled:pointer-events-none">Delete</button>
                </td>
              </tr>
              <tr v-if="tasks.length === 0">
                <td colspan="7" class="p-4 text-center text-slate-500">No backup synchronization tasks configured.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Create Cloud Sync Task Form -->
      <div class="p-6 rounded-2xl glass-panel-light space-y-4">
        <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Register Hybrid Cloud Backup Profile</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Task Profile Name</label>
            <input v-model="form.name" placeholder="Weekly Media Sync" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Source ZFS Dataset</label>
            <select v-model="form.local_path" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
              <option v-for="ds in datasets" :key="ds.name" :value="ds.mountpoint">{{ ds.name }} ({{ ds.mountpoint }})</option>
              <option v-if="datasets.length === 0" value="">-- Create ZFS pool first --</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Cloud Provider Target</label>
            <select v-model="form.provider" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
              <option value="AWS S3">Amazon S3 Storage</option>
              <option value="Backblaze B2">Backblaze B2</option>
              <option value="Google Cloud Storage">Google Cloud Storage (GCS)</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Target Bucket Name</label>
            <input v-model="form.bucket" placeholder="my-secure-nas-backup" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Access Key ID (or Client ID)</label>
            <input v-model="form.access_key" placeholder="AKIAIOSFODNN7EXAMPLE" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Secret Access Key (Credentials)</label>
            <input v-model="form.secret_key" placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" type="password" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Synchronization Scheduling Frequency (cron)</label>
            <input v-model="form.schedule" placeholder="0 4 * * 0 (Every Sunday at 4:00 AM)" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
        </div>

        <button @click="createTask" :disabled="!form.name || !form.local_path || !form.bucket" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
          Publish Backup Profile
        </button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  token: String
})

const tasks = ref<any[]>([])
const datasets = ref<any[]>([])
let monitorTimer: any = null

const form = ref({
  name: '',
  local_path: '',
  provider: 'AWS S3',
  bucket: '',
  schedule: '0 2 * * *',
  access_key: '',
  secret_key: ''
})

const fetchTasks = async () => {
  try {
    const res = await fetch('/api/backup/cloud', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      tasks.value = await res.json()
    }
  } catch (e) {
    console.error('Failed fetching sync profiles', e)
  }
}

const fetchDatasets = async () => {
  try {
    const res = await fetch('/api/storage/zfs/datasets', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      datasets.value = await res.json()
      if (datasets.value.length > 0 && !form.value.local_path) {
        form.value.local_path = datasets.value[0].mountpoint
      }
    }
  } catch (e) {
    console.error('Failed fetching datasets list', e)
  }
}

const createTask = async () => {
  try {
    const res = await fetch('/api/backup/cloud', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(form.value)
    })
    if (res.ok) {
      alert('Backup sync profile registered.')
      form.value = {
        name: '',
        local_path: datasets.value[0]?.mountpoint || '',
        provider: 'AWS S3',
        bucket: '',
        schedule: '0 2 * * *',
        access_key: '',
        secret_key: ''
      }
      fetchTasks()
    }
  } catch (e) {
    alert(e)
  }
}

const runSync = async (taskId: string) => {
  try {
    const res = await fetch(`/api/backup/cloud/${taskId}/sync-run`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      fetchTasks()
    }
  } catch (e) {
    alert(e)
  }
}

const deleteTask = async (taskId: string) => {
  if (!confirm('Permanently delete cloud synchronization task?')) return
  try {
    const res = await fetch(`/api/backup/cloud/${taskId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) fetchTasks()
  } catch (e) {
    alert(e)
  }
}

onMounted(() => {
  fetchTasks()
  fetchDatasets()
  monitorTimer = setInterval(fetchTasks, 2000)
})

onUnmounted(() => {
  if (monitorTimer) clearInterval(monitorTimer)
})
</script>
