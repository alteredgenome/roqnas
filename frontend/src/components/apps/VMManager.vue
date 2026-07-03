<template>
  <div class="h-full flex flex-col text-slate-200 relative overflow-hidden">
    <div class="flex-1 overflow-auto p-6 space-y-6">
      <div class="space-y-3">
        <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Virtual Machines & Containers</h3>
        <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
          <table class="w-full border-collapse text-left text-xs">
            <thead>
              <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                <th class="p-3">Node Name</th>
                <th class="p-3">Hypervisor</th>
                <th class="p-3">vCPU allocation</th>
                <th class="p-3">Memory allocation</th>
                <th class="p-3">Status</th>
                <th class="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr v-for="vm in vms" :key="vm.name" class="hover:bg-white/5">
                <td class="p-3 font-semibold text-blue-400 font-mono">{{ vm.name }}</td>
                <td class="p-3 text-slate-400">{{ vm.name.endsWith('-LXC') ? 'LXC Container' : 'QEMU/KVM VM' }}</td>
                <td class="p-3 font-semibold">{{ vm.vcpu }} Cores</td>
                <td class="p-3 font-semibold">{{ vm.ram_mb }} MB</td>
                <td class="p-3">
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded"
                    :class="vm.status === 'running' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'">
                    {{ vm.status }}
                  </span>
                </td>
                <td class="p-3 text-right space-x-1.5">
                  <button v-if="vm.status !== 'running'" @click="runAction(vm.name, 'start')" class="px-2 py-1 bg-emerald-600/20 border border-emerald-500/30 hover:bg-emerald-600 hover:text-white rounded text-xs transition">Boot</button>
                  <button v-if="vm.status === 'running'" @click="openConsole(vm.name)" class="px-2 py-1 bg-indigo-600/20 border border-indigo-500/30 hover:bg-indigo-600 hover:text-white rounded text-xs transition">Console</button>
                  <button v-if="vm.status === 'running'" @click="runAction(vm.name, 'stop')" class="px-2 py-1 bg-yellow-600/20 border border-yellow-500/30 hover:bg-yellow-600 hover:text-white rounded text-xs transition">Stop</button>
                  <button v-if="vm.status === 'running'" @click="runAction(vm.name, 'reboot')" class="px-2 py-1 bg-blue-600/20 border border-blue-500/30 hover:bg-blue-600 hover:text-white rounded text-xs transition">Reboot</button>
                  <button @click="runAction(vm.name, 'destroy')" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition">Destroy</button>
                </td>
              </tr>
              <tr v-if="vms.length === 0">
                <td colspan="6" class="p-4 text-center text-slate-500">Scanning hypervisor nodes...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Create VM Form -->
      <div class="p-6 rounded-2xl glass-panel-light space-y-4">
        <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Provision Virtual Machine</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">VM Name</label>
            <input v-model="form.name" placeholder="WindowsServer-2025" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">vCPUs Cores</label>
            <input v-model="form.vcpu" type="number" min="1" max="64" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Memory allocation (MB)</label>
            <input v-model="form.ram_mb" type="number" min="512" max="65536" step="512" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Root Storage Size (GB)</label>
            <input v-model="form.disk_gb" type="number" min="5" max="2000" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Boot ISO image path (Optional)</label>
            <input v-model="form.iso_path" placeholder="/mnt/md0/isos/ubuntu-live-server.iso" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
          </div>
        </div>

        <button @click="createVM" :disabled="!form.name" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
          Provision Node
        </button>
      </div>
    </div>

    <!-- VM Console Dialog (Overlay Modal) -->
    <div v-if="activeConsoleVM" class="absolute inset-0 bg-slate-950/80 backdrop-blur-md flex flex-col z-50 animate-in fade-in duration-200">
      <!-- Header -->
      <div class="p-4 border-b border-white/5 bg-white/5 flex items-center justify-between">
        <div class="flex items-center gap-4">
          <h3 class="text-sm font-semibold tracking-wider text-slate-300">VM Remote Console: <span class="text-blue-400 font-mono">{{ activeConsoleVM }}</span></h3>
          <div class="flex rounded bg-slate-900 p-0.5 border border-white/5 text-[10px]">
            <button @click="consoleMode = 'serial'" class="px-2 py-0.5 rounded font-bold uppercase transition" :class="consoleMode === 'serial' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-slate-200'">Serial Terminal</button>
            <button @click="consoleMode = 'vnc'" class="px-2 py-0.5 rounded font-bold uppercase transition" :class="consoleMode === 'vnc' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:text-slate-200'">VNC Graphics</button>
          </div>
        </div>
        <button @click="closeConsole" class="p-1.5 hover:bg-white/5 rounded-lg border border-transparent hover:border-white/5 text-slate-400 hover:text-slate-200 transition">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Console Body -->
      <div class="flex-1 min-h-0 bg-black flex items-center justify-center relative">
        <!-- SERIAL TERMINAL COMPONENT -->
        <div v-show="consoleMode === 'serial'" ref="termContainer" class="w-full h-full p-2 pointer-events-auto"></div>

        <!-- GRAPHICAL VNC PROXY (SIMULATION / REAL CANVAS) -->
        <div v-show="consoleMode === 'vnc'" class="w-full h-full flex flex-col items-center justify-center bg-slate-950 p-6 space-y-4">
          <!-- Mocking VNC screen graphics -->
          <div class="w-full max-w-2xl aspect-[4/3] bg-black border border-white/10 rounded-xl overflow-hidden shadow-2xl relative flex flex-col justify-between p-4 font-mono text-xs text-emerald-400">
            <!-- Screen Header -->
            <div class="flex justify-between border-b border-white/5 pb-2 text-[10px] text-slate-500">
              <span>QEMU RFB VNC 127.0.0.1:5900</span>
              <span>1024x768 60Hz</span>
            </div>

            <!-- Operating system boot sequence logs mock -->
            <div class="flex-1 flex flex-col justify-end space-y-1 py-4 text-[10px] overflow-hidden select-text text-left">
              <div>[    0.000000] Booting Linux kernel on physical CPU 0x0</div>
              <div>[    0.000000] Linux version 6.1.0-22-arm64 (debian-kernel@lists.debian.org)</div>
              <div>[    1.299042] ext4-fs (vda2): mounted filesystem with ordered data mode. Opts: (null)</div>
              <div>[    2.512991] systemd[1]: Detected architecture arm64.</div>
              <div>[    3.902102] systemd[1]: Started LSB: NFS kernel daemon.</div>
              <div>[    4.290113] systemd[1]: Reached target Multi-User System.</div>
              <div class="text-white mt-4">Debian GNU/Linux 13 guest-vm tty1</div>
              <div class="text-white flex items-center gap-1.5">
                <span>guest-vm login: root</span>
              </div>
              <div class="text-white flex items-center gap-1.5">
                <span>Password: ••••••••</span>
              </div>
              <div class="text-white font-bold mt-2">Welcome to Debian GNU/Linux 13 (Trixie) VM!</div>
              <div class="text-white">root@guest-vm:~# ip address show dev eth0</div>
              <div>2: eth0: &lt;BROADCAST,MULTICAST,UP,LOWER_UP&gt; mtu 1500 qdisc mq state UP group default qlen 1000</div>
              <div>    inet 192.168.122.45/24 brd 192.168.122.255 scope global dynamic eth0</div>
              <div class="text-white flex items-center gap-1">
                <span>root@guest-vm:~# </span>
                <span class="w-1.5 h-3 bg-white animate-pulse inline-block"></span>
              </div>
            </div>

            <!-- Screen Footer -->
            <div class="border-t border-white/5 pt-2 flex justify-between text-[10px] text-slate-500">
              <span>Console redirection active</span>
              <span>Press CTRL+ALT+2 for QEMU Monitor</span>
            </div>
          </div>
          <div class="text-xs text-slate-400">Mock VNC display active. Graphical RFB canvas tunnel proxy is active on socket port <code class="bg-slate-900 px-1.5 py-0.5 rounded text-white">/api/ws/vms/{{ activeConsoleVM }}/vnc</code>.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'

const props = defineProps({
  token: String
})

const vms = ref<any[]>([])

const form = ref({
  name: '',
  vcpu: 2,
  ram_mb: 2048,
  disk_gb: 20,
  iso_path: ''
})

// Console states
const activeConsoleVM = ref<string | null>(null)
const consoleMode = ref('serial') // serial or vnc

// Xterm refs
const termContainer = ref<HTMLElement | null>(null)
let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let socket: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

const fetchVMs = async () => {
  try {
    const res = await fetch('/api/hypervisor/vms', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      vms.value = await res.json()
    }
  } catch (e) {
    console.error('Failed fetching VMs', e)
  }
}

const runAction = async (name: string, action: string) => {
  if (action === 'destroy' && !confirm(`Permanently destroy VM "${name}"?`)) return
  try {
    const res = await fetch(`/api/hypervisor/vms/${name}/action?action=${action}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      fetchVMs()
    }
  } catch (e) {
    alert(e)
  }
}

const createVM = async () => {
  try {
    const res = await fetch('/api/hypervisor/vms', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(form.value)
    })
    if (res.ok) {
      alert('VM Created & started successfully.')
      form.value = { name: '', vcpu: 2, ram_mb: 2048, disk_gb: 20, iso_path: '' }
      fetchVMs()
    }
  } catch (e) {
    alert(e)
  }
}

// Console overlays
const openConsole = (vmName: string) => {
  activeConsoleVM.value = vmName
  consoleMode.value = 'serial'
  
  // Wait for container ref rendering and init xterm
  setTimeout(initConsoleTerminal, 150)
}

const closeConsole = () => {
  cleanupConsoleTerminal()
  activeConsoleVM.value = null
}

const initConsoleTerminal = () => {
  if (!termContainer.value || !activeConsoleVM.value) return

  term = new Terminal({
    cursorBlink: true,
    fontSize: 12,
    fontFamily: 'Consolas, "Courier New", Courier, monospace',
    theme: {
      background: '#090d16',
      foreground: '#cbd5e1',
      cursor: '#10b981'
    },
    allowProposedApi: true
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(termContainer.value)
  fitAddon.fit()

  // Setup WS connection
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/ws/vms/${activeConsoleVM.value}/console`
  socket = new WebSocket(wsUrl)

  socket.onopen = () => {
    if (term) {
      sendResize(term.cols, term.rows)
    }
  }

  socket.onmessage = (event) => {
    if (term) term.write(event.data)
  }

  socket.onclose = () => {
    if (term) term.write('\r\n\x1b[31m[VM console closed]\x1b[0m\r\n')
  }

  term.onData((data) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'data', data }))
    }
  })

  resizeObserver = new ResizeObserver(() => {
    if (fitAddon && term) {
      try {
        fitAddon.fit()
        sendResize(term.cols, term.rows)
      } catch (e) {}
    }
  })
  resizeObserver.observe(termContainer.value)
}

const sendResize = (cols: number, rows: number) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'resize', cols, rows }))
  }
}

const cleanupConsoleTerminal = () => {
  if (resizeObserver) resizeObserver.disconnect()
  if (socket) socket.close()
  if (term) term.dispose()
  term = null
  socket = null
}

onMounted(() => {
  fetchVMs()
})

onUnmounted(() => {
  cleanupConsoleTerminal()
})
</script>
