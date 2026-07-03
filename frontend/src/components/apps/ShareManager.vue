<template>
  <div class="h-full flex flex-col text-slate-200">
    <div class="flex border-b border-white/5 bg-white/5 px-4 gap-2">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        @click="activeTab = tab.id"
        class="px-4 py-3 text-xs font-semibold uppercase tracking-wider transition border-b-2"
        :class="activeTab === tab.id ? 'border-blue-500 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'"
      >
        {{ tab.name }}
      </button>
    </div>

    <div class="flex-1 overflow-auto p-6 space-y-6">
      <!-- TAB 1: SMB EXPORTS -->
      <div v-if="activeTab === 'smb'" class="space-y-6">
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Active Samba (SMB) Shares</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Share Name</th>
                  <th class="p-3">Local Path</th>
                  <th class="p-3">Guest Access</th>
                  <th class="p-3">Write Status</th>
                  <th class="p-3">Comment</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="share in smbShares" :key="share.name" class="hover:bg-white/5">
                  <td class="p-3 font-semibold text-blue-400 flex items-center gap-1.5 flex-wrap">
                    <span>\\{{ systemHostname }}\\{{ share.name }}</span>
                    <span v-if="share.time_machine" class="text-[8px] font-bold px-1.5 py-0.5 bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 rounded uppercase">Time Machine</span>
                  </td>
                  <td class="p-3 font-mono text-[11px] text-slate-300">{{ share.path }}</td>
                  <td class="p-3">
                    <span class="text-[10px] px-2 py-0.5 rounded" :class="share.guest_ok ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'">
                      {{ share.guest_ok ? 'Allowed' : 'Disabled' }}
                    </span>
                  </td>
                  <td class="p-3">{{ share.read_only ? 'Read-Only' : 'Read-Write' }}</td>
                  <td class="p-3 text-slate-400">{{ share.comment || '-' }}</td>
                </tr>
                <tr v-if="smbShares.length === 0">
                  <td colspan="5" class="p-4 text-center text-slate-500">No Samba shares defined.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Add SMB Share Form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Add SMB Share</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Share Name</label>
              <input v-model="newSmb.name" placeholder="MediaFolder" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Volume Path</label>
              <input v-model="newSmb.path" placeholder="/tank/media" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
            <div class="md:col-span-2">
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Comment / Description</label>
              <input v-model="newSmb.comment" placeholder="Public network media collection" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
          </div>

          <div class="flex gap-6 text-xs pt-2">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="newSmb.guest_ok" class="rounded text-blue-500 bg-slate-900 border-white/20" />
              <span>Allow Guest Access (Anonymous)</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="newSmb.read_only" class="rounded text-blue-500 bg-slate-900 border-white/20" />
              <span>Read-Only Share</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="newSmb.time_machine" class="rounded text-blue-500 bg-slate-900 border-white/20" />
              <span>Apple Time Machine Target</span>
            </label>
          </div>

          <div v-if="newSmb.time_machine" class="pt-1 max-w-xs text-left">
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Max Backup Size Limit (e.g. 500G, 2T) - Optional</label>
            <input v-model="newSmb.time_machine_max_size" placeholder="e.g. 500G" type="text" class="w-full px-3 py-1.5 rounded-lg glass-input text-xs font-mono bg-slate-950" />
          </div>

          <button @click="addSmbShare" :disabled="!newSmb.name || !newSmb.path" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Publish Share
          </button>
        </div>
      </div>

      <!-- TAB 2: NFS EXPORTS -->
      <div v-if="activeTab === 'nfs'" class="space-y-6">
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">NFS Directory Exports</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Exported Directory</th>
                  <th class="p-3">Allowed Hosts / Client Range</th>
                  <th class="p-3">Options</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="share in nfsShares" :key="share.path" class="hover:bg-white/5">
                  <td class="p-3 font-semibold text-indigo-400 font-mono">{{ share.path }}</td>
                  <td class="p-3 font-mono">{{ share.allowed_hosts }}</td>
                  <td class="p-3 text-slate-400 font-mono">{{ share.options }}</td>
                </tr>
                <tr v-if="nfsShares.length === 0">
                  <td colspan="3" class="p-4 text-center text-slate-500">No NFS exports defined.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Add NFS Share Form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Export NFS Directory</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Directory Path</label>
              <input v-model="newNfs.path" placeholder="/tank/media" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Allowed Hosts</label>
              <input v-model="newNfs.allowed_hosts" placeholder="192.168.1.0/24" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
            <div class="md:col-span-2">
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Export Options</label>
              <input v-model="newNfs.options" placeholder="rw,sync,no_subtree_check,no_root_squash" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>

          <button @click="addNfsShare" :disabled="!newNfs.path" class="px-4 py-2 bg-indigo-600 rounded-lg font-semibold text-xs text-white hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Export NFS Path
          </button>
        </div>
      </div>

      <!-- TAB 3: ISCSI TARGETS -->
      <div v-if="activeTab === 'iscsi'" class="space-y-6">
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Active iSCSI LUN Targets</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Target IQN</th>
                  <th class="p-3">Backing Device/File</th>
                  <th class="p-3">Allowed Initiator</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="tgt in iscsiTargets" :key="tgt.target_iqn" class="hover:bg-white/5">
                  <td class="p-3 font-semibold text-teal-400 font-mono">{{ tgt.target_iqn }}</td>
                  <td class="p-3 font-mono text-slate-300">{{ tgt.backing_store }}</td>
                  <td class="p-3 text-slate-400 font-mono">{{ tgt.initiator_address }}</td>
                </tr>
                <tr v-if="iscsiTargets.length === 0">
                  <td colspan="3" class="p-4 text-center text-slate-500">No active iSCSI targets exposed.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Add iSCSI Target Form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Expose Block Volume (iSCSI LUN)</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Target IQN</label>
              <input v-model="newIscsi.target_iqn" placeholder="iqn.2026-07.local.rocknas:lun1" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Backing Storage device or file</label>
              <input v-model="newIscsi.backing_store" placeholder="/dev/md0" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div class="md:col-span-2">
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Allowed Initiator IP Address (Optional)</label>
              <input v-model="newIscsi.initiator_address" placeholder="ALL" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>

          <button @click="addIscsiTarget" :disabled="!newIscsi.target_iqn || !newIscsi.backing_store" class="px-4 py-2 bg-teal-600 rounded-lg font-semibold text-xs text-white hover:bg-teal-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Bind iSCSI Target
          </button>
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

const activeTab = ref('smb')
const tabs = [
  { id: 'smb', name: 'Samba / SMB Shares' },
  { id: 'nfs', name: 'NFS Exports' },
  { id: 'iscsi', name: 'iSCSI Targets' }
]

const smbShares = ref<any[]>([])
const nfsShares = ref<any[]>([])
const iscsiTargets = ref<any[]>([])
const systemHostname = ref('roqnas')

const newSmb = ref({ name: '', path: '', read_only: false, guest_ok: true, comment: '', time_machine: false, time_machine_max_size: '' })
const newNfs = ref({ path: '', allowed_hosts: '*', options: 'rw,sync,no_subtree_check,no_root_squash' })
const newIscsi = ref({ target_iqn: 'iqn.2026-07.local.roqnas:lun1', backing_store: '', initiator_address: 'ALL' })

const fetchShareData = async () => {
  try {
    const headers = { 'Authorization': `Bearer ${props.token}` }

    // Fetch telemetry to get active hostname
    const telemetryRes = await fetch('/api/system/telemetry', { headers })
    if (telemetryRes.ok) {
      const tel = await telemetryRes.json()
      if (tel.hostname) {
        systemHostname.value = tel.hostname
      }
    }

    const smbRes = await fetch('/api/shares/smb', { headers })
    if (smbRes.ok) smbShares.value = await smbRes.json()

    const nfsRes = await fetch('/api/shares/nfs', { headers })
    if (nfsRes.ok) nfsShares.value = await nfsRes.json()

    const iscsiRes = await fetch('/api/iscsi/targets', { headers })
    if (iscsiRes.ok) iscsiTargets.value = await iscsiRes.json()

  } catch (e) {
    console.error('Failed querying share information', e)
  }
}

const addSmbShare = async () => {
  try {
    const res = await fetch('/api/shares/smb', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(newSmb.value)
    })
    if (res.ok) {
      alert('Samba share published successfully.')
      newSmb.value = { name: '', path: '', read_only: false, guest_ok: true, comment: '', time_machine: false, time_machine_max_size: '' }
      fetchShareData()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const addNfsShare = async () => {
  try {
    const res = await fetch('/api/shares/nfs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(newNfs.value)
    })
    if (res.ok) {
      alert('NFS export published.')
      newNfs.value = { path: '', allowed_hosts: '*', options: 'rw,sync,no_subtree_check,no_root_squash' }
      fetchShareData()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const addIscsiTarget = async () => {
  try {
    const res = await fetch('/api/iscsi/targets', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(newIscsi.value)
    })
    if (res.ok) {
      alert('iSCSI target exposed.')
      newIscsi.value = { target_iqn: 'iqn.2026-07.local.roqnas:lun1', backing_store: '', initiator_address: 'ALL' }
      fetchShareData()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

onMounted(() => {
  fetchShareData()
})
</script>
