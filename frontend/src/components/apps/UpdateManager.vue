<template>
  <div class="h-full flex flex-col text-slate-200 p-6 space-y-6 overflow-auto">
    <!-- Header -->
    <div class="space-y-1">
      <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Software Update Center</h3>
      <p class="text-xs text-slate-500">Manage RoqNAS system versions, channels, and custom update endpoints.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- Left side: Configuration -->
      <div class="md:col-span-1 p-6 rounded-2xl glass-panel-light border border-white/5 space-y-4 h-max">
        <h4 class="text-xs font-bold uppercase text-slate-300 tracking-wider">Update Settings</h4>
        
        <div class="space-y-3">
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Update Server URL</label>
            <input v-model="settings.server_url" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono bg-slate-950/60" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Target Branch / Channel</label>
            <select v-model="settings.branch" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-950/60">
              <option value="release">Release (Stable)</option>
              <option value="beta">Beta (Pre-release testing)</option>
              <option value="dev">Dev (Active development builds)</option>
            </select>
          </div>
        </div>

        <button @click="saveSettings" class="w-full py-2 bg-indigo-600/30 border border-indigo-500/30 hover:bg-indigo-600 hover:text-white rounded-lg text-xs font-semibold transition">Save Configurations</button>
      </div>

      <!-- Right side: Status / Upgrade -->
      <div class="md:col-span-2 space-y-6">
        <!-- Status Card -->
        <div class="p-6 rounded-2xl glass-panel-light border border-white/5 space-y-6">
          <div class="flex items-center justify-between">
            <div class="space-y-1">
              <h4 class="text-xs font-bold uppercase text-slate-300 tracking-wider">System Status</h4>
              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-400">Current Version:</span>
                <span class="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">{{ settings.current_version }}</span>
              </div>
            </div>
            <button @click="checkUpdates" :disabled="checking" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-xs font-semibold rounded-lg transition flex items-center gap-1 text-white">
              <svg v-if="checking" class="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              <span>{{ checking ? 'Checking...' : 'Check for Updates' }}</span>
            </button>
          </div>

          <div v-if="updateInfo" class="space-y-4 border-t border-white/5 pt-4">
            <div class="flex items-center gap-3">
              <span class="text-xs text-slate-300">Latest Available:</span>
              <span class="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">{{ updateInfo.latest_version }}</span>
              <span v-if="updateInfo.update_available" class="text-[10px] font-bold uppercase px-2 py-0.5 bg-yellow-500/20 text-yellow-400 border border-yellow-500/20 rounded">Update Available</span>
              <span v-else class="text-[10px] font-bold uppercase px-2 py-0.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded">Up to Date</span>
            </div>

            <!-- Changelog -->
            <div class="space-y-2">
              <label class="block text-[10px] font-bold text-slate-400 uppercase">Changelog / Details</label>
              <div class="bg-slate-950/40 border border-white/5 rounded-xl p-4 max-h-48 overflow-auto text-xs leading-relaxed text-slate-400 font-mono">
                {{ updateInfo.changelog }}
              </div>
            </div>

            <!-- Action Button -->
            <div v-if="updateInfo.update_available" class="pt-2 flex justify-end">
              <button @click="applyUpgrade" :disabled="upgrading" class="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-xs font-bold rounded-lg transition flex items-center gap-1 text-white">
                <svg v-if="upgrading" class="animate-spin -ml-1 mr-1 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <span>{{ upgrading ? 'Upgrading System...' : 'Install Update Now' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps({
  token: String
})

const settings = ref({
  current_version: 'v0.0.5',
  server_url: 'https://update.roqnas.org',
  branch: 'release'
})

const checking = ref(false)
const upgrading = ref(false)
const updateInfo = ref<any>(null)

const fetchSettings = async () => {
  try {
    const res = await fetch('/api/system/app-version', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      settings.value = await res.json()
    }
  } catch (e) {
    console.error('Failed fetching version settings', e)
  }
}

const saveSettings = async () => {
  try {
    const res = await fetch(`/api/system/app-version/config?server_url=${encodeURIComponent(settings.value.server_url)}&branch=${settings.value.branch}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      alert('Settings updated successfully.')
      fetchSettings()
    }
  } catch (e) {
    alert(e)
  }
}

const checkUpdates = async () => {
  checking.value = true
  updateInfo.value = null
  try {
    const res = await fetch('/api/system/app-version/check', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      updateInfo.value = await res.json()
    }
  } catch (e) {
    alert('Failed checking update server: ' + e)
  } finally {
    checking.value = false
  }
}

const applyUpgrade = async () => {
  if (!confirm('Reboot or control plane restart may happen during upgrade. Proceed?')) return
  upgrading.value = true
  try {
    const res = await fetch('/api/system/app-version/upgrade', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      alert(data.message)
    } else {
      const data = await res.json()
      alert('Upgrade failed: ' + data.detail)
      upgrading.value = false
    }
  } catch (e) {
    alert(e)
    upgrading.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>
