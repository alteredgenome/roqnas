<template>
  <div class="relative w-full h-full overflow-hidden bg-[#0d1527] select-none text-slate-100 flex flex-col">
    <!-- Top Global Menu Bar -->
    <div class="h-10 w-full bg-slate-950/60 border-b border-white/5 backdrop-blur-md flex items-center justify-between px-4 z-50">
      <div class="flex items-center gap-4">
        <!-- Logo/Start Menu -->
        <button 
          @click="toggleLauncher" 
          class="flex items-center gap-2 hover:bg-white/5 px-2.5 py-1 rounded-lg transition"
          :class="{ 'bg-white/10': showLauncher }"
        >
          <div class="w-5 h-5 rounded bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-xs">R</div>
          <span class="text-xs font-semibold tracking-wider text-slate-200">RoqNAS</span>
        </button>

        <span class="text-[11px] text-slate-500 font-mono">Host: {{ health.hostname || 'roqnas' }}</span>
      </div>

      <!-- Time & Quick Panel -->
      <div class="flex items-center gap-4">
        <span class="text-xs text-slate-300 font-mono">{{ currentTime }}</span>
        
        <div class="h-4 w-[1px] bg-white/10"></div>
        
        <!-- User account details -->
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-300 font-medium">{{ username }}</span>
          <span class="text-[9px] bg-blue-500/20 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded font-bold uppercase">{{ role }}</span>
        </div>

        <button 
          @click="emit('logout')" 
          title="Sign Out"
          class="p-1 hover:bg-red-500/10 hover:text-red-400 rounded-lg text-slate-400 transition"
        >
          <LogOut class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Desktop Space (where windows live) -->
    <div class="flex-1 w-full relative z-10 p-4" @click.self="blurAllWindows">
      
      <!-- System Status Floating Widget (fydeOS/fnOS look) -->
      <div 
        @mousedown="startWidgetDrag"
        :style="{ top: `${widgetY}px`, left: `${widgetX}px` }"
        class="absolute w-64 p-5 rounded-2xl glass-panel border border-white/5 shadow-xl select-none cursor-move z-0"
      >
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400">Control Center</h4>
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
        </div>
        
        <div class="space-y-4">
          <!-- CPU Status -->
          <div class="space-y-1">
            <div class="flex justify-between text-xs text-slate-300">
              <span>CPU Usage</span>
              <span class="font-semibold">{{ health.cpu?.percent.toFixed(0) }}%</span>
            </div>
            <div class="w-full bg-slate-900/60 rounded-full h-1.5 overflow-hidden border border-white/5">
              <div class="bg-blue-500 h-full transition-all duration-500" :style="{ width: `${health.cpu?.percent}%` }"></div>
            </div>
          </div>

          <!-- Memory Status -->
          <div class="space-y-1">
            <div class="flex justify-between text-xs text-slate-300">
              <span>Memory Usage</span>
              <span class="font-semibold">{{ health.memory?.percent.toFixed(0) }}%</span>
            </div>
            <div class="w-full bg-slate-900/60 rounded-full h-1.5 overflow-hidden border border-white/5">
              <div class="bg-emerald-500 h-full transition-all duration-500" :style="{ width: `${health.memory?.percent}%` }"></div>
            </div>
          </div>

          <!-- Disk usage general -->
          <div class="space-y-1">
            <div class="flex justify-between text-xs text-slate-300">
              <span>Storage Usage</span>
              <span class="font-semibold">{{ activeDiskUsagePercent }}%</span>
            </div>
            <div class="w-full bg-slate-900/60 rounded-full h-1.5 overflow-hidden border border-white/5">
              <div class="bg-purple-500 h-full transition-all" :style="{ width: `${activeDiskUsagePercent}%` }"></div>
            </div>
          </div>

          <!-- System Temperatures & Fan indicators -->
          <div class="flex justify-between text-[11px] text-slate-400 pt-2 border-t border-white/5">
            <span>Core Temp</span>
            <span class="font-mono font-bold text-slate-200">{{ health.temperature }}°C</span>
          </div>
        </div>
      </div>

      <!-- Render Windows -->
      <Window
        v-for="win in windows"
        :key="win.id"
        :title="win.title"
        :width="win.width"
        :height="win.height"
        :x="win.x"
        :y="win.y"
        :zIndex="win.zIndex"
        :active="win.active"
        :minimized="win.minimized"
        @close="closeWindow(win.id)"
        @minimize="minimizeWindow(win.id)"
        @focus="focusWindow(win.id)"
      >
        <template #icon>
          <component :is="win.icon" class="w-4 h-4 text-blue-400" />
        </template>
        <!-- App content injector -->
        <component :is="win.component" :token="token" />
      </Window>

      <!-- App Launcher Overlay -->
      <div 
        v-if="showLauncher" 
        class="absolute left-4 top-12 w-80 p-6 rounded-2xl glass-panel border border-white/10 shadow-2xl z-50 animate-in fade-in zoom-in duration-200"
      >
        <div class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Applications</div>
        <div class="grid grid-cols-3 gap-3">
          <button 
            v-for="app in appTemplates" 
            :key="app.id"
            @click="launchApp(app)"
            class="flex flex-col items-center p-3 rounded-xl hover:bg-white/5 transition border border-transparent hover:border-white/5 group text-center"
          >
            <div class="w-10 h-10 rounded-xl bg-slate-900 border border-white/5 flex items-center justify-center mb-2 group-hover:scale-105 transition text-blue-400 shadow-md">
              <component :is="app.icon" class="w-5 h-5" />
            </div>
            <span class="text-[10px] font-medium text-slate-300 leading-tight">{{ app.title }}</span>
          </button>
        </div>
      </div>

    </div>

    <!-- Floating Dock / Taskbar (fnOS Style) -->
    <div class="h-16 w-full flex items-center justify-center p-3 relative z-40 select-none pointer-events-none">
      <div class="flex items-center gap-3 px-6 py-2.5 rounded-2xl glass-panel border border-white/10 shadow-2xl pointer-events-auto">
        <!-- Start launcher button -->
        <button 
          @click="toggleLauncher" 
          title="App Launcher"
          class="p-2 rounded-xl hover:bg-white/5 text-slate-300 transition duration-200 active:scale-[0.98]"
        >
          <LayoutGrid class="w-5 h-5 text-indigo-400" />
        </button>

        <div class="h-6 w-[1px] bg-white/10"></div>

        <!-- Open Apps in taskbar -->
        <div class="flex items-center gap-2">
          <button 
            v-for="win in windows" 
            :key="win.id"
            @click="toggleWindowMinimize(win.id)"
            class="p-2 rounded-xl relative transition duration-200"
            :class="win.active ? 'bg-white/10 text-white' : 'hover:bg-white/5 text-slate-400'"
            :title="win.title"
          >
            <component :is="win.icon" class="w-5 h-5 text-blue-400" />
            <!-- Active dot tracker -->
            <span 
              class="absolute bottom-1.5 left-1/2 transform -translate-x-1/2 w-1 h-1 rounded-full bg-blue-500 transition-all duration-300"
              :class="win.minimized ? 'opacity-40 w-1.5 bg-yellow-500' : 'opacity-100'"
            ></span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, shallowRef } from 'vue'
import { 
  LogOut, 
  Activity, 
  HardDrive, 
  Share2, 
  Network, 
  Server, 
  Terminal as TerminalIcon, 
  Users, 
  FileText, 
  LayoutGrid,
  FolderOpen,
  Cloud,
  ShieldCheck,
  Globe,
  RefreshCw
} from 'lucide-vue-next'

import Window from './Window.vue'

// Import Sub Application Views
import Telemetry from './apps/Telemetry.vue'
import StorageManager from './apps/StorageManager.vue'
import ShareManager from './apps/ShareManager.vue'
import NetworkConfig from './apps/NetworkConfig.vue'
import VMManager from './apps/VMManager.vue'
import Terminal from './apps/Terminal.vue'
import UserManager from './apps/UserManager.vue'
import LogViewer from './apps/LogViewer.vue'
import UpdateManager from './apps/UpdateManager.vue'
import FileExplorer from './apps/FileExplorer.vue'
import CloudSync from './apps/CloudSync.vue'
import SecurityHub from './apps/SecurityHub.vue'
import DirectoryServices from './apps/DirectoryServices.vue'

const props = defineProps({
  token: String,
  username: String
})

const emit = defineEmits(['logout'])

const role = ref(props.username === 'admin' ? 'admin' : 'standard')

// Desktop clock
const currentTime = ref('')
const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleDateString() + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Widget draggable
const widgetX = ref(60)
const widgetY = ref(60)
let startWdx = 0
let startWdy = 0
let startWmx = 0
let startWmy = 0

const startWidgetDrag = (e: MouseEvent) => {
  startWmx = e.clientX
  startWmy = e.clientY
  startWdx = widgetX.value
  startWdy = widgetY.value

  document.addEventListener('mousemove', widgetDragHandler)
  document.addEventListener('mouseup', stopWidgetDragHandler)
}

const widgetDragHandler = (e: MouseEvent) => {
  const dx = e.clientX - startWmx
  const dy = e.clientY - startWmy
  widgetX.value = Math.max(10, Math.min(window.innerWidth - 270, startWdx + dx))
  widgetY.value = Math.max(50, Math.min(window.innerHeight - 200, startWdy + dy))
}

const stopWidgetDragHandler = () => {
  document.removeEventListener('mousemove', widgetDragHandler)
  document.removeEventListener('mouseup', stopWidgetDragHandler)
}

// Telemetry state
const health = ref<any>({})
let healthTimer: any = null

const fetchHealth = async () => {
  try {
    const res = await fetch('/api/system/telemetry', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      health.value = await res.json()
    }
  } catch (e) {
    console.error('Failed fetching widget details', e)
  }
}

const activeDiskUsagePercent = computed(() => {
  if (!health.value.disks || health.value.disks.length === 0) return 0
  return health.value.disks[0].percent || 0
})

// Windows state management
const windows = ref<any[]>([])
let globalZIndex = 10
const showLauncher = ref(false)

const appTemplates = [
  { id: 'telemetry', title: 'System Telemetry', icon: Activity, component: shallowRef(Telemetry), width: 900, height: 600 },
  { id: 'files', title: 'File Station', icon: FolderOpen, component: shallowRef(FileExplorer), width: 900, height: 580 },
  { id: 'cloud', title: 'Cloud Backup', icon: Cloud, component: shallowRef(CloudSync), width: 900, height: 600 },
  { id: 'security', title: 'Security Center', icon: ShieldCheck, component: shallowRef(SecurityHub), width: 900, height: 600 },
  { id: 'directory', title: 'Directory Services', icon: Globe, component: shallowRef(DirectoryServices), width: 900, height: 580 },
  { id: 'storage', title: 'Storage Manager', icon: HardDrive, component: shallowRef(StorageManager), width: 950, height: 650 },
  { id: 'shares', title: 'Share & Bindings', icon: Share2, component: shallowRef(ShareManager), width: 850, height: 600 },
  { id: 'network', title: 'Network Settings', icon: Network, component: shallowRef(NetworkConfig), width: 850, height: 500 },
  { id: 'vm', title: 'Hypervisor Node', icon: Server, component: shallowRef(VMManager), width: 900, height: 600 },
  { id: 'terminal', title: 'Console Terminal', icon: TerminalIcon, component: shallowRef(Terminal), width: 750, height: 480 },
  { id: 'users', title: 'User Accounts', icon: Users, component: shallowRef(UserManager), width: 800, height: 520 },
  { id: 'logs', title: 'System Logs', icon: FileText, component: shallowRef(LogViewer), width: 800, height: 500 },
  { id: 'updates', title: 'Update Manager', icon: RefreshCw, component: shallowRef(UpdateManager), width: 850, height: 500 }
]

const toggleLauncher = () => {
  showLauncher.value = !showLauncher.value
}

const launchApp = (appTemplate: any) => {
  showLauncher.value = false
  // Check if already open
  const existing = windows.value.find(w => w.id === appTemplate.id)
  if (existing) {
    existing.minimized = false
    focusWindow(appTemplate.id)
    return
  }

  // Create new window
  globalZIndex += 1
  windows.value.push({
    id: appTemplate.id,
    title: appTemplate.title,
    icon: appTemplate.icon,
    component: appTemplate.component,
    width: appTemplate.width,
    height: appTemplate.height,
    x: 120,
    y: 80,
    zIndex: globalZIndex,
    active: true,
    minimized: false
  })

  // Blur all other windows
  windows.value.forEach(w => {
    if (w.id !== appTemplate.id) w.active = false
  })
}

const focusWindow = (id: string) => {
  const win = windows.value.find(w => w.id === id)
  if (win && !win.active) {
    globalZIndex += 1
    win.zIndex = globalZIndex
    win.active = true
    win.minimized = false

    // Blur others
    windows.value.forEach(w => {
      if (w.id !== id) w.active = false
    })
  }
}

const blurAllWindows = () => {
  windows.value.forEach(w => w.active = false)
}

const closeWindow = (id: string) => {
  windows.value = windows.value.filter(w => w.id !== id)
}

const minimizeWindow = (id: string) => {
  const win = windows.value.find(w => w.id === id)
  if (win) {
    win.minimized = true
    win.active = false
  }
}

const toggleWindowMinimize = (id: string) => {
  const win = windows.value.find(w => w.id === id)
  if (win) {
    if (win.minimized) {
      win.minimized = false
      focusWindow(id)
    } else if (win.active) {
      minimizeWindow(id)
    } else {
      focusWindow(id)
    }
  }
}

let clockTimer: any = null
onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)

  fetchHealth()
  healthTimer = setInterval(fetchHealth, 3000)

  // Launch dashboard by default
  setTimeout(() => {
    launchApp(appTemplates[0])
  }, 300)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (healthTimer) clearInterval(healthTimer)
})
</script>
