<template>
  <div class="h-full flex text-slate-200">
    <!-- Sidebar Navigation -->
    <div class="w-56 border-r border-white/5 bg-slate-950/40 p-4 space-y-4">
      <h4 class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Quick Access</h4>
      
      <div class="space-y-1">
        <button 
          v-for="dir in shortcuts" 
          :key="dir.path"
          @click="navigateTo(dir.path)"
          class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs transition text-left"
          :class="currentPath === dir.path ? 'bg-blue-500/20 text-blue-400 font-semibold' : 'hover:bg-white/5 text-slate-400 hover:text-slate-200'"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
          <span>{{ dir.name }}</span>
        </button>
      </div>
    </div>

    <!-- Main File Grid & Explorer -->
    <div class="flex-1 flex flex-col min-w-0 bg-slate-950/20">
      <!-- Toolbar -->
      <div class="p-4 border-b border-white/5 bg-white/5 flex items-center justify-between gap-4">
        <!-- Path Breadcrumb -->
        <div class="flex items-center gap-1 font-mono text-xs overflow-hidden">
          <button @click="navigateTo('/')" class="text-blue-400 hover:underline">root</button>
          <template v-for="(part, idx) in pathParts" :key="idx">
            <span class="text-slate-600">/</span>
            <button @click="navigateIdx(idx)" class="text-blue-400 hover:underline max-w-[120px] truncate">{{ part }}</button>
          </template>
        </div>

        <!-- Action tools -->
        <div class="flex items-center gap-2">
          <button @click="showCreateDir = true" class="p-1.5 bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 text-xs flex items-center gap-1 transition">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" /></svg>
            <span>New Folder</span>
          </button>

          <!-- Upload triggering input -->
          <label class="p-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs flex items-center gap-1 cursor-pointer transition select-none">
            <input type="file" @change="handleUpload" class="hidden" />
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
            <span>Upload File</span>
          </label>
        </div>
      </div>

      <!-- Main Directory Files list -->
      <div class="flex-1 overflow-auto p-6">
        <!-- Uploading overlay indicator -->
        <div v-if="uploading" class="mb-4 p-4 rounded-xl bg-blue-950/30 border border-blue-500/20 flex items-center gap-4 animate-pulse">
          <span class="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></span>
          <span class="text-xs text-blue-300 font-medium">Uploading file to Storage Node (Simulated progress)...</span>
        </div>

        <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
          <table class="w-full border-collapse text-left text-xs">
            <thead>
              <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                <th class="p-3 w-1/2">Name</th>
                <th class="p-3">Size</th>
                <th class="p-3">Permissions</th>
                <th class="p-3">Modified Date</th>
                <th class="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <!-- Back folder directory link -->
              <tr v-if="currentPath !== '/'" @click="navigateUp" class="hover:bg-white/5 cursor-pointer transition">
                <td colspan="5" class="p-3 font-semibold text-blue-400 flex items-center gap-2">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
                  <span>..</span>
                </td>
              </tr>

              <!-- Files lists mapping -->
              <tr v-for="file in files" :key="file.name" class="hover:bg-white/5 transition group">
                <td class="p-3 font-semibold flex items-center gap-2 max-w-md truncate">
                  <span v-if="file.type === 'dir'" class="text-blue-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                  </span>
                  <span v-else class="text-slate-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  </span>
                  <button 
                    @click="file.type === 'dir' ? navigateTo(getFullPath(file.name)) : null"
                    class="hover:underline font-mono text-[11px]"
                    :class="file.type === 'dir' ? 'text-slate-200' : 'text-slate-300'"
                  >
                    {{ file.name }}
                  </button>
                </td>
                <td class="p-3 text-slate-400 font-mono">{{ file.type === 'dir' ? '-' : formatBytes(file.size) }}</td>
                <td class="p-3 text-slate-500 font-mono text-[11px]">{{ file.perms }}</td>
                <td class="p-3 text-slate-400 font-mono">{{ file.mtime }}</td>
                <td class="p-3 text-right space-x-1.5 opacity-0 group-hover:opacity-100 transition">
                  <button v-if="file.type === 'file'" @click="downloadFile(file.name)" title="Download" class="px-2 py-0.5 bg-white/5 hover:bg-white/10 rounded border border-white/10 text-[10px]">Get</button>
                  <button v-if="file.type === 'dir'" @click="archiveFolder(file.name)" title="Compress Archive" class="px-2 py-0.5 bg-indigo-600/20 hover:bg-indigo-600 rounded border border-indigo-500/20 text-[10px]">Zip</button>
                  <button @click="deleteItem(file.name)" title="Delete" class="px-2 py-0.5 bg-red-600/20 hover:bg-red-600 hover:text-white rounded border border-red-500/20 text-[10px]">Del</button>
                </td>
              </tr>

              <tr v-if="files.length === 0">
                <td colspan="5" class="p-8 text-center text-slate-500 font-mono text-xs">Directory folder is empty.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Create Folder Modal Overlay -->
    <div v-if="showCreateDir" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="w-full max-w-sm p-6 rounded-2xl glass-panel border border-white/10 shadow-2xl space-y-4">
        <h3 class="text-sm font-semibold tracking-wider text-slate-300">Create New Folder</h3>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Folder Name</label>
          <input v-model="newDirName" placeholder="SubFolder" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
        </div>
        <div class="flex gap-2 justify-end">
          <button @click="createFolder" :disabled="!newDirName" class="px-3 py-1.5 bg-blue-600 rounded-lg text-xs hover:bg-blue-500 disabled:opacity-50 transition">Create</button>
          <button @click="showCreateDir = false" class="px-3 py-1.5 bg-slate-800 rounded-lg text-xs hover:bg-slate-700 transition">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

const props = defineProps({
  token: String
})

const currentPath = ref('/')
const files = ref<any[]>([])
const uploading = ref(false)

const showCreateDir = ref(false)
const newDirName = ref('')

const shortcuts = [
  { name: 'Root FileSystem', path: '/' },
  { name: 'Backups Pool', path: '/backups' },
  { name: 'Media Pool', path: '/media' },
  { name: 'Documents Pool', path: '/documents' }
]

// Computed path parts
const pathParts = computed(() => {
  return currentPath.value.split('/').filter(Boolean)
})

const navigateTo = (path: string) => {
  currentPath.value = path
  fetchFiles()
}

const navigateUp = () => {
  const parts = pathParts.value
  if (parts.length > 0) {
    parts.pop()
    currentPath.value = '/' + parts.join('/')
    fetchFiles()
  }
}

const navigateIdx = (index: number) => {
  const parts = pathParts.value.slice(0, index + 1)
  currentPath.value = '/' + parts.join('/')
  fetchFiles()
}

const getFullPath = (name: string) => {
  const clean = currentPath.value.rstrip('/')
  return `${clean}/${name}`
}

// String right-strip helper
String.prototype.rstrip = function(chars: string) {
  let end = this.length
  while (end > 0 && chars.indexOf(this[end - 1]) !== -1) {
    end--
  }
  return this.substring(0, end)
}

const fetchFiles = async () => {
  try {
    const res = await fetch(`/api/files/list?path=${encodeURIComponent(currentPath.value)}`, {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      files.value = await res.json()
    }
  } catch (e) {
    console.error('Failed reading file catalog', e)
  }
}

const createFolder = async () => {
  try {
    const res = await fetch(`/api/files/create_dir?path=${encodeURIComponent(currentPath.value)}&dir_name=${encodeURIComponent(newDirName.value)}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      showCreateDir.value = false
      newDirName.value = ''
      fetchFiles()
    }
  } catch (e) {
    alert(e)
  }
}

const deleteItem = async (name: string) => {
  if (!confirm(`Permanently delete "${name}"?`)) return
  try {
    const target = getFullPath(name)
    const res = await fetch(`/api/files/delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({ path: target })
    })
    if (res.ok) {
      fetchFiles()
    }
  } catch (e) {
    alert(e)
  }
}

const archiveFolder = async (folderName: string) => {
  try {
    const target = getFullPath(folderName)
    const res = await fetch(`/api/files/archive`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({
        path: target,
        archive_type: 'zip',
        output_name: `${folderName}.zip`
      })
    })
    if (res.ok) {
      alert(`Compressed folder successfully to ${folderName}.zip`)
      fetchFiles()
    }
  } catch (e) {
    alert(e)
  }
}

const downloadFile = (fileName: string) => {
  alert(`Initiating secure local network download for: ${fileName}`)
}

const handleUpload = (e: any) => {
  const file = e.target.files[0]
  if (!file) return
  uploading.value = true
  
  // Simulate network upload timeout
  setTimeout(() => {
    uploading.value = false
    alert(`File ${file.name} successfully written to storage pool.`)
    // Mock insert
    files.value.push({
      name: file.name,
      size: file.size,
      type: 'file',
      perms: 'rw-r--r--',
      mtime: 'Just now'
    })
  }, 2000)
}

const formatBytes = (bytes: number) => {
  if (bytes === 0 || bytes === undefined || bytes === null) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  fetchFiles()
})
</script>
