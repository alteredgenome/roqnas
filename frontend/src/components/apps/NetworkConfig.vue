<template>
  <div class="h-full flex flex-col text-slate-200">
    <!-- Sub tabs -->
    <div class="flex border-b border-white/5 bg-white/5 px-4 gap-2">
      <button 
        @click="activeSubTab = 'interfaces'"
        class="px-4 py-3 text-xs font-semibold uppercase tracking-wider transition border-b-2"
        :class="activeSubTab === 'interfaces' ? 'border-blue-500 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'"
      >
        Network Interfaces
      </button>
      <button 
        @click="activeSubTab = 'bonds'"
        class="px-4 py-3 text-xs font-semibold uppercase tracking-wider transition border-b-2"
        :class="activeSubTab === 'bonds' ? 'border-blue-500 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'"
      >
        Bonds & Link Aggregation (LAG)
      </button>
      <button 
        @click="activeSubTab = 'mdns'"
        class="px-4 py-3 text-xs font-semibold uppercase tracking-wider transition border-b-2"
        :class="activeSubTab === 'mdns' ? 'border-blue-500 text-white' : 'border-transparent text-slate-400 hover:text-slate-200'"
      >
        Bonjour Discovery (mDNS)
      </button>
    </div>

    <!-- Scrollable content -->
    <div class="flex-1 overflow-auto p-6 space-y-6">

      <!-- TAB 1: NETWORK INTERFACES -->
      <div v-if="activeSubTab === 'interfaces'" class="space-y-6">
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Physical & Virtual Interfaces</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Interface</th>
                  <th class="p-3">IP Address</th>
                  <th class="p-3">Subnet Mask</th>
                  <th class="p-3">Gateway</th>
                  <th class="p-3">MTU</th>
                  <th class="p-3">Status</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="iface in interfaces" :key="iface.name" class="hover:bg-white/5">
                  <td class="p-3 font-mono font-bold text-blue-400">{{ iface.name }}</td>
                  <td class="p-3 font-mono">{{ iface.ip || 'Unassigned' }}</td>
                  <td class="p-3 font-mono text-slate-400">{{ iface.netmask || '-' }}</td>
                  <td class="p-3 font-mono text-slate-400">{{ iface.gateway || '-' }}</td>
                  <td class="p-3 font-mono">{{ iface.mtu }} B</td>
                  <td class="p-3">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded"
                      :class="iface.status === 'UP' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'">
                      {{ iface.status }}
                    </span>
                  </td>
                  <td class="p-3 text-right">
                    <button @click="selectInterface(iface)" class="px-2 py-1 bg-blue-600/20 border border-blue-500/30 hover:bg-blue-600 hover:text-white rounded text-xs transition">Configure</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Configure Panel -->
        <div v-if="selected" class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Configure Interface: <span class="text-blue-400 font-mono">{{ selected.name }}</span></h3>
          
          <div class="flex gap-6 text-xs mb-4">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="radio" :value="true" v-model="form.dhcp" class="text-blue-500 bg-slate-900 border-white/20" />
              <span>DHCP (Dynamic IP assignment)</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="radio" :value="false" v-model="form.dhcp" class="text-blue-500 bg-slate-900 border-white/20" />
              <span>Static IP Address</span>
            </label>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">IP Address / Netmask</label>
              <input v-model="form.address" :disabled="form.dhcp" placeholder="192.168.1.100/24" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono disabled:opacity-30" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Gateway</label>
              <input v-model="form.gateway" :disabled="form.dhcp" placeholder="192.168.1.1" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono disabled:opacity-30" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">DNS Server (Primary)</label>
              <input v-model="form.dns1" :disabled="form.dhcp" placeholder="1.1.1.1" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono disabled:opacity-30" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">MTU Size (Up to 9000 for Jumbo Frames)</label>
              <input v-model="form.mtu" type="number" min="68" max="9000" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>

          <div class="flex gap-3 pt-2">
            <button @click="applyConfiguration" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] transition">
              Apply Configuration
            </button>
            <button @click="selected = null" class="px-4 py-2 bg-slate-800 rounded-lg font-semibold text-xs text-slate-300 hover:bg-slate-700 active:scale-[0.98] transition">
              Cancel
            </button>
          </div>
        </div>
      </div>

      <!-- TAB 2: BONDS & LINK AGGREGATION -->
      <div v-if="activeSubTab === 'bonds'" class="space-y-6">
        <!-- List active Network bonds -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Active Link Aggregation Groups (LAG)</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Bond Name</th>
                  <th class="p-3">Aggregation Mode</th>
                  <th class="p-3">Member Interfaces</th>
                  <th class="p-3">IP Address</th>
                  <th class="p-3">MTU Size</th>
                  <th class="p-3">Status</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="bond in bonds" :key="bond.name" class="hover:bg-white/5">
                  <td class="p-3 font-mono font-bold text-blue-400">{{ bond.name }}</td>
                  <td class="p-3 font-semibold uppercase tracking-wider text-[11px]">{{ bond.mode }}</td>
                  <td class="p-3">
                    <span v-for="member in bond.interfaces" :key="member" class="font-mono bg-slate-800/80 px-1.5 py-0.5 rounded text-[10px] mr-1">{{ member }}</span>
                  </td>
                  <td class="p-3 font-mono">{{ bond.address || 'Unassigned' }}</td>
                  <td class="p-3 font-mono">{{ bond.mtu }} B</td>
                  <td class="p-3">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded"
                      :class="bond.status === 'UP' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'">
                      {{ bond.status }}
                    </span>
                  </td>
                  <td class="p-3 text-right">
                    <button @click="deleteBond(bond.name)" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition">Destroy</button>
                  </td>
                </tr>
                <tr v-if="bonds.length === 0">
                  <td colspan="7" class="p-4 text-center text-slate-500">No active network bonds configured.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Create Network Bond Form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Create Link Aggregation Group (LAG/Bond)</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Bond Interface Name</label>
              <input v-model="newBond.name" placeholder="bond0" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Bonding Mode</label>
              <select v-model="newBond.mode" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option value="802.3ad">LACP (802.3ad - Dynamic Link Aggregation)</option>
                <option value="active-backup">Active-Backup (Network Failover Redundancy)</option>
                <option value="balance-alb">Adaptive Load Balancing (balance-alb)</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">MTU Size</label>
              <input v-model="newBond.mtu" type="number" min="68" max="9000" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-2">Select Member Interfaces</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="iface in eligiblePhysicalInterfaces" :key="iface.name" class="flex items-center gap-2 bg-white/5 border border-white/10 px-3 py-2 rounded-lg cursor-pointer hover:bg-white/10 select-none text-xs">
                <input type="checkbox" :value="iface.name" v-model="newBond.interfaces" class="rounded text-blue-500 bg-slate-900 border-white/20" />
                <span class="font-mono font-bold text-blue-400">{{ iface.name }}</span>
                <span class="text-slate-400">({{ iface.status }})</span>
              </label>
              <div v-if="eligiblePhysicalInterfaces.length === 0" class="text-xs text-slate-500">No physical network interfaces available to bind.</div>
            </div>
          </div>

          <hr class="border-white/5" />

          <!-- Network Bond IP allocation -->
          <div class="space-y-4">
            <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400">Bond IP Addressing</h4>
            <div class="flex gap-6 text-xs">
              <label class="flex items-center gap-2 cursor-pointer select-none">
                <input type="radio" :value="true" v-model="newBond.dhcp" class="text-blue-500 bg-slate-900 border-white/20" />
                <span>DHCP IP</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer select-none">
                <input type="radio" :value="false" v-model="newBond.dhcp" class="text-blue-500 bg-slate-900 border-white/20" />
                <span>Static IP Address</span>
              </label>
            </div>

            <div v-if="!newBond.dhcp" class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">IP Address / Netmask</label>
                <input v-model="newBond.address" placeholder="192.168.1.200/24" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Gateway</label>
                <input v-model="newBond.gateway" placeholder="192.168.1.1" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">DNS Server</label>
                <input v-model="newBond.dns1" placeholder="1.1.1.1" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
              </div>
            </div>
          </div>

          <button @click="createBond" :disabled="!newBond.name || newBond.interfaces.length < 2" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Provision Network Bond
          </button>
        </div>
      </div>

      <!-- TAB 3: BONJOUR DISCOVERY (mDNS) -->
      <div v-if="activeSubTab === 'mdns'" class="max-w-2xl space-y-6">
        <div class="p-6 rounded-2xl glass-panel-light space-y-6">
          <div class="text-left">
            <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Bonjour LAN Service Broadcasts</h3>
            <p class="text-xs text-slate-400 mt-1">
              Bonjour / Multicast DNS (mDNS) allows client computers on your local network (macOS Finder, Linux file managers, and Windows Network Neighborhood) to discover and display RoqNAS services automatically without manual IP configuration.
            </p>
          </div>

          <div class="space-y-4">
            <!-- Toggle Active -->
            <div class="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
              <div class="text-left">
                <span class="block text-xs font-semibold text-slate-200">Multicast Advertisements Daemon</span>
                <span class="text-[10px] text-slate-400">Toggle zero-config LAN discoverability for SMB and Web portal</span>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="mdnsConfig.active" class="sr-only peer" />
                <div class="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-300 after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600 peer-checked:after:bg-white peer-checked:after:border-white"></div>
              </label>
            </div>

            <!-- Icon profile dropdown -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="text-left">
                <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">LAN Finder representation Profile</label>
                <select v-model="mdnsConfig.model" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900 border border-white/10 text-slate-200">
                  <option value="TimeCapsule">Time Capsule (White Box)</option>
                  <option value="Macmini">Mac mini (Compact Server)</option>
                  <option value="MacPro">Mac Pro (Tower Server)</option>
                  <option value="iMac">iMac (Desktop)</option>
                  <option value="Xserve">Xserve (Rackmounted Chassis)</option>
                </select>
              </div>

              <div class="p-3 rounded-lg bg-white/5 text-[10px] text-slate-400 border border-white/5 flex flex-col justify-center text-left">
                <span class="block font-semibold text-slate-300 mb-0.5">Active advertised Services:</span>
                <div class="flex gap-1.5 flex-wrap mt-1">
                  <span v-for="srv in mdnsStatus.services" :key="srv" class="px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded-md font-mono border border-blue-500/10">
                    {{ srv }}
                  </span>
                  <span v-if="mdnsStatus.services.length === 0" class="text-[9px] text-slate-500">None</span>
                </div>
              </div>
            </div>
          </div>

          <div class="flex">
            <button @click="saveMdnsSettings" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] transition duration-150">
              Save & Publish Advertisements
            </button>
          </div>
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

const activeSubTab = ref('interfaces')
const interfaces = ref<any[]>([])
const bonds = ref<any[]>([])
const selected = ref<any>(null)

const form = ref({
  dhcp: true,
  address: '',
  gateway: '',
  dns1: '1.1.1.1',
  mtu: 1500
})

const newBond = ref({
  name: '',
  mode: '802.3ad',
  interfaces: [] as string[],
  dhcp: true,
  address: '',
  gateway: '',
  dns1: '1.1.1.1',
  mtu: 9000
})

const mdnsConfig = ref({ active: true, model: 'TimeCapsule' })
const mdnsStatus = ref({ active: true, model: 'TimeCapsule', services: [] as string[] })

const fetchMdnsData = async () => {
  try {
    const headers = { 'Authorization': `Bearer ${props.token}` }
    const res = await fetch('/api/system/mdns', { headers })
    if (res.ok) {
      const data = await res.json()
      mdnsStatus.value = data
      mdnsConfig.value.active = data.active
      mdnsConfig.value.model = data.model
    }
  } catch (e) {
    console.error('Failed fetching mDNS settings', e)
  }
}

const saveMdnsSettings = async () => {
  try {
    const res = await fetch('/api/system/mdns/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(mdnsConfig.value)
    })
    if (res.ok) {
      alert('mDNS / Bonjour discoverability settings successfully saved.')
      fetchMdnsData()
    } else {
      const data = await res.json()
      alert('Error saving config: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

// Physical interfaces eligible for bonding
const eligiblePhysicalInterfaces = computed(() => {
  return interfaces.value.filter(iface => {
    // Exclude virtual/loopback/bonds
    if (iface.name.startsWith('lo') || iface.name.startsWith('bond')) return false
    // Exclude if already in an active bond
    return !bonds.value.some(b => b.interfaces.includes(iface.name))
  })
})

const fetchNetworkData = async () => {
  try {
    const headers = { 'Authorization': `Bearer ${props.token}` }

    const ifaceRes = await fetch('/api/network/interfaces', { headers })
    if (ifaceRes.ok) interfaces.value = await ifaceRes.json()

    const bondRes = await fetch('/api/network/bonds', { headers })
    if (bondRes.ok) bonds.value = await bondRes.json()

  } catch (e) {
    console.error('Failed fetching network configuration details', e)
  }
}

const selectInterface = (iface: any) => {
  selected.value = iface
  form.value = {
    dhcp: iface.dhcp,
    address: iface.ip ? `${iface.ip}/24` : '',
    gateway: iface.gateway || '',
    dns1: '1.1.1.1',
    mtu: iface.mtu || 1500
  }
}

const applyConfiguration = async () => {
  try {
    const payload = {
      interface: selected.value.name,
      dhcp: form.value.dhcp,
      address: form.value.dhcp ? '' : form.value.address,
      gateway: form.value.dhcp ? '' : form.value.gateway,
      dns: form.value.dhcp ? [] : [form.value.dns1],
      mtu: form.value.mtu
    }

    const res = await fetch('/api/network/configure', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(payload)
    })

    if (res.ok) {
      const data = await res.json()
      alert(data.message)
      selected.value = null
      fetchNetworkData()
    }
  } catch (e) {
    alert(e)
  }
}

// Bond Actions
const createBond = async () => {
  try {
    const payload = {
      name: newBond.value.name,
      mode: newBond.value.mode,
      interfaces: newBond.value.interfaces,
      dhcp: newBond.value.dhcp,
      address: newBond.value.dhcp ? '' : newBond.value.address,
      gateway: newBond.value.dhcp ? '' : newBond.value.gateway,
      dns: newBond.value.dhcp ? [] : [newBond.value.dns1],
      mtu: newBond.value.mtu
    }

    const res = await fetch('/api/network/bonds', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(payload)
    })

    if (res.ok) {
      alert(`Network Bond ${newBond.value.name} created successfully.`)
      newBond.value = {
        name: '',
        mode: '802.3ad',
        interfaces: [],
        dhcp: true,
        address: '',
        gateway: '',
        dns1: '1.1.1.1',
        mtu: 9000
      }
      fetchNetworkData()
    } else {
      const data = await res.json()
      alert('Error creating bond: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const deleteBond = async (name: string) => {
  if (!confirm(`Are you sure you want to delete network bond "${name}"?`)) return
  try {
    const res = await fetch(`/api/network/bonds/${name}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) fetchNetworkData()
  } catch (e) {
    alert(e)
  }
}

onMounted(() => {
  fetchNetworkData()
  fetchMdnsData()
})
</script>
