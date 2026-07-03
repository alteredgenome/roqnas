<template>
  <div class="h-full flex flex-col text-slate-200">
    <!-- Sub-navigation tabs -->
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

    <!-- Scrollable content -->
    <div class="flex-1 overflow-auto p-6 space-y-6">

      <!-- TAB 1: SECURITY COUNSELOR -->
      <div v-if="activeTab === 'counselor'" class="space-y-6 animate-in fade-in duration-150">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          <!-- Health Score Gauge -->
          <div class="p-6 rounded-2xl glass-panel-light flex flex-col items-center justify-center space-y-4">
            <h3 class="text-xs font-bold tracking-wider uppercase text-slate-400">Security Health Score</h3>
            <div class="relative w-32 h-32 flex items-center justify-center">
              <svg class="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" stroke="rgba(255,255,255,0.05)" stroke-width="8" fill="transparent" />
                <circle cx="50" cy="50" r="40" :stroke="scoreColor" stroke-width="8" fill="transparent" 
                        stroke-dasharray="251.2" :stroke-dashoffset="dashOffset" class="transition-all duration-1000 ease-out" />
              </svg>
              <div class="absolute text-center">
                <span class="text-3xl font-extrabold font-mono tracking-tighter text-white">{{ healthScore }}%</span>
                <div class="text-[9px] uppercase tracking-wider text-slate-400 mt-0.5 font-bold">{{ scoreLabel }}</div>
              </div>
            </div>
            <button @click="runScan" :disabled="scanInProgress" class="w-full py-2 bg-blue-600 rounded-lg text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-50 active:scale-[0.98] transition">
              {{ scanInProgress ? 'Sweeping Configuration...' : 'Audit Security Settings' }}
            </button>
            <div class="text-[10px] text-slate-500 font-mono">Last scanned: {{ scanResults.last_run }}</div>
          </div>

          <!-- Summary list -->
          <div class="md:col-span-2 p-6 rounded-2xl glass-panel-light flex flex-col justify-between">
            <h3 class="text-xs font-bold tracking-wider uppercase text-slate-300">Auditor Status Summary</h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 my-2">
              <div class="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-center">
                <div class="text-2xl font-bold text-red-400 font-mono">{{ criticalCount }}</div>
                <div class="text-[10px] text-slate-400 font-bold uppercase">Critical Risks</div>
              </div>
              <div class="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl text-center">
                <div class="text-2xl font-bold text-yellow-400 font-mono">{{ warningCount }}</div>
                <div class="text-[10px] text-slate-400 font-bold uppercase">Warnings</div>
              </div>
              <div class="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-center">
                <div class="text-2xl font-bold text-emerald-400 font-mono">{{ secureCount }}</div>
                <div class="text-[10px] text-slate-400 font-bold uppercase">Secure Checks</div>
              </div>
            </div>
            <p class="text-[11px] text-slate-400">Security Counselor scans configuration tables such as sshd_config parameters, firewall sockets settings, and system accounts privileges to score alignment with core Linux hardening guidelines.</p>
          </div>
        </div>

        <!-- Scan detailed audits table -->
        <div class="space-y-3">
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400">Scan Results & Rules Checklist</h4>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Audit Domain</th>
                  <th class="p-3">Policy Checklist Title</th>
                  <th class="p-3">Status</th>
                  <th class="p-3">Security Finding Analysis</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="item in scanResults.results" :key="item.id" class="hover:bg-white/5">
                  <td class="p-3 font-semibold text-slate-400 uppercase text-[10px] tracking-wider">{{ item.category }}</td>
                  <td class="p-3 font-semibold text-slate-200">{{ item.title }}</td>
                  <td class="p-3">
                    <span class="text-[9px] font-bold px-2 py-0.5 rounded uppercase"
                      :class="{
                        'bg-red-500/20 text-red-400': item.status === 'critical',
                        'bg-yellow-500/20 text-yellow-400': item.status === 'warning',
                        'bg-emerald-500/20 text-emerald-400': item.status === 'secure'
                      }">
                      {{ item.status }}
                    </span>
                  </td>
                  <td class="p-3 text-slate-300 font-medium">{{ item.message }}</td>
                </tr>
                <tr v-if="!scanResults.results || scanResults.results.length === 0">
                  <td colspan="4" class="p-4 text-center text-slate-500">Run security scan to audit NAS configurations.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 2: FAIL2BAN BRUTE FORCE PROTECTION -->
      <div v-if="activeTab === 'fail2ban'" class="space-y-6 animate-in fade-in duration-150">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Config parameters -->
          <div class="p-6 rounded-2xl glass-panel-light space-y-4">
            <h3 class="text-xs font-bold tracking-wider uppercase text-slate-300">Fail2ban Parameters</h3>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Ban Duration (Seconds)</label>
              <input v-model="f2bConfig.bantime" type="number" min="60" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Max Retry Failures Limit</label>
              <input v-model="f2bConfig.maxretry" type="number" min="1" max="50" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <button @click="saveF2bConfig" class="w-full py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition active:scale-[0.98]">
              Apply Config & Restart
            </button>
          </div>

          <!-- Active Jails summary card -->
          <div class="md:col-span-2 p-6 rounded-2xl glass-panel-light space-y-4">
            <h3 class="text-xs font-bold tracking-wider uppercase text-slate-300">Jail Shields Active</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div v-for="jail in f2bStatus.active_jails" :key="jail" class="p-4 bg-white/5 border border-white/5 rounded-xl flex items-center justify-between">
                <div>
                  <div class="text-xs font-bold text-blue-400 font-mono">{{ jail }} jail</div>
                  <div class="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Monitoring Active sockets</div>
                </div>
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
              </div>
              <div v-if="!f2bStatus.active_jails || f2bStatus.active_jails.length === 0" class="text-xs text-slate-500">No fail2ban jails active on systems.</div>
            </div>
          </div>
        </div>

        <!-- Banned IPs List -->
        <div class="space-y-3">
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400">Intruder Block List</h4>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Banned Client IP</th>
                  <th class="p-3">Security Jail Target</th>
                  <th class="p-3">Banned At</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="b in f2bStatus.banned_ips" :key="b.ip" class="hover:bg-white/5">
                  <td class="p-3 font-bold text-red-400 font-mono">{{ b.ip }}</td>
                  <td class="p-3 font-semibold font-mono text-slate-300">{{ b.jail }}</td>
                  <td class="p-3 text-slate-400 font-mono">{{ b.banned_at }}</td>
                  <td class="p-3 text-right">
                    <button @click="unbanIP(b.jail, b.ip)" class="px-2 py-0.5 bg-emerald-600/20 border border-emerald-500/30 hover:bg-emerald-600 hover:text-white rounded text-[10px] transition">Unban IP</button>
                  </td>
                </tr>
                <tr v-if="!f2bStatus.banned_ips || f2bStatus.banned_ips.length === 0">
                  <td colspan="4" class="p-4 text-center text-slate-500">No client IPs currently blocked by intrusion shields.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 3: MULTI-FACTOR AUTH (MFA) -->
      <div v-if="activeTab === 'mfa'" class="space-y-6 animate-in fade-in duration-150">
        <div class="max-w-xl mx-auto p-6 rounded-2xl glass-panel-light space-y-6">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300 text-center">Multi-Factor Authentication Settings</h3>

          <!-- Status Indicator -->
          <div class="p-4 rounded-xl border flex items-center justify-between"
               :class="mfaEnabled ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'">
            <div class="flex items-center gap-3">
              <span class="relative flex h-3 w-3">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" :class="mfaEnabled ? 'bg-emerald-400' : 'bg-red-400'"></span>
                <span class="relative inline-flex rounded-full h-3 w-3" :class="mfaEnabled ? 'bg-emerald-500' : 'bg-red-500'"></span>
              </span>
              <div>
                <div class="text-xs font-bold">MFA Protection is {{ mfaEnabled ? 'ENABLED' : 'DISABLED' }}</div>
                <div class="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Enforces 6-digit TOTP token prompts at login authentication.</div>
              </div>
            </div>
            <button v-if="mfaEnabled" @click="deactivateMFA" class="px-3 py-1 bg-red-600 rounded-lg text-xs font-bold text-white hover:bg-red-500 transition">Disable Protection</button>
          </div>

          <!-- Wizard setup -->
          <div v-if="!mfaEnabled" class="space-y-6">
            <div class="text-xs text-slate-400 text-center leading-relaxed">Protect your account using a Time-based One-time Password generator like Google Authenticator or Microsoft Authenticator. Click the button to link verification credentials.</div>
            
            <div v-if="!mfaSetup.secret" class="flex justify-center">
              <button @click="triggerSetup" class="px-4 py-2 bg-blue-600 rounded-lg text-xs font-semibold hover:bg-blue-500 active:scale-[0.98] transition">Initialize MFA Profile</button>
            </div>

            <!-- Setup Details panel -->
            <div v-else class="space-y-6 p-4 bg-slate-950/60 border border-white/5 rounded-2xl animate-in fade-in slide-in-from-bottom-2 duration-200">
              <h4 class="text-xs font-bold uppercase tracking-wider text-slate-300">Link authenticator profile</h4>
              
              <!-- Simulated QR Code visual container -->
              <div class="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-white/10 max-w-[200px] mx-auto space-y-3 shadow-md">
                <!-- Authentic real QR block layout -->
                <div class="w-32 h-32 bg-slate-100 p-1.5 rounded-lg border border-slate-200/50 flex items-center justify-center relative overflow-hidden select-none">
                  <img :src="`https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(mfaSetup.otpauth_url)}`" class="w-full h-full object-contain" alt="MFA QR Code" />
                </div>
                <div class="text-[9px] text-slate-400 font-bold tracking-wider uppercase text-center">Scan QR inside app</div>
              </div>

              <div class="space-y-2">
                <label class="block text-[10px] font-bold text-slate-400 uppercase">Or link manually with secret code:</label>
                <div class="flex items-center gap-2">
                  <code class="flex-1 bg-slate-900 px-3 py-2 rounded-lg text-xs font-mono font-bold text-blue-400 select-all border border-white/5">{{ mfaSetup.secret }}</code>
                </div>
              </div>

              <div class="space-y-2">
                <label class="block text-[10px] font-bold text-slate-400 uppercase">Input 6-digit verification code token:</label>
                <div class="flex gap-2">
                  <input v-model="mfaVerifyCode" placeholder="123456" type="text" maxlength="6" class="flex-1 px-3 py-2 rounded-lg glass-input text-xs font-mono text-center tracking-[0.4em]" />
                  <button @click="verifyAndEnableMFA" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-xs font-semibold text-white active:scale-[0.98] transition">Confirm Token</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

const props = defineProps({
  token: String,
  username: String
})

const activeTab = ref('counselor')
const tabs = [
  { id: 'counselor', name: 'Security Counselor' },
  { id: 'fail2ban', name: 'Brute Force Shield' },
  { id: 'mfa', name: 'Multi-Factor Auth' }
]

// Counselor scanning states
const scanInProgress = ref(false)
const scanResults = ref<any>({ scanning: false, last_run: '-', results: [] })

// Fail2ban states
const f2bStatus = ref<any>({ active_jails: [], banned_ips: [], config: {} })
const f2bConfig = ref({ bantime: 3600, maxretry: 5 })

// MFA states
const mfaEnabled = ref(false)
const mfaSetup = ref<any>({ secret: '', otpauth_url: '' })
const mfaVerifyCode = ref('')

// Score compute properties
const healthScore = computed(() => {
  if (!scanResults.value.results || scanResults.value.results.length === 0) return 100
  let score = 100
  scanResults.value.results.forEach((r: any) => {
    if (r.status === 'critical') score -= 30
    if (r.status === 'warning') score -= 15
  })
  return Math.max(0, score)
})

const dashOffset = computed(() => {
  const circ = 251.2
  return circ - (healthScore.value / 100) * circ
})

const scoreColor = computed(() => {
  const score = healthScore.value
  if (score >= 80) return '#10b981' // emerald
  if (score >= 50) return '#eab308' // yellow
  return '#ef4444' // red
})

const scoreLabel = computed(() => {
  const score = healthScore.value
  if (score >= 80) return 'Hardened'
  if (score >= 50) return 'Vulnerable'
  return 'Insecure'
})

const criticalCount = computed(() => {
  return scanResults.value.results?.filter((r: any) => r.status === 'critical').length || 0
})

const warningCount = computed(() => {
  return scanResults.value.results?.filter((r: any) => r.status === 'warning').length || 0
})

const secureCount = computed(() => {
  return scanResults.value.results?.filter((r: any) => r.status === 'secure').length || 0
})

// counselor scanning calls
const fetchScanResults = async () => {
  try {
    const res = await fetch('/api/security/counselor/results', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      scanResults.value = await res.json()
      scanInProgress.value = scanResults.value.scanning
    }
  } catch (e) {
    console.error(e)
  }
}

const runScan = async () => {
  scanInProgress.value = true
  try {
    const res = await fetch('/api/security/counselor/scan', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      // Poll results
      setTimeout(pollScanResults, 1200)
    }
  } catch (e) {
    alert(e)
    scanInProgress.value = false
  }
}

const pollScanResults = async () => {
  await fetchScanResults()
  if (scanInProgress.value) {
    setTimeout(pollScanResults, 1000)
  }
}

// Fail2ban client calls
const fetchF2bStatus = async () => {
  try {
    const res = await fetch('/api/security/fail2ban/status', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      f2bStatus.value = await res.json()
      f2bConfig.value.bantime = f2bStatus.value.config?.bantime || 3600
      f2bConfig.value.maxretry = f2bStatus.value.config?.maxretry || 5
    }
  } catch (e) {
    console.error(e)
  }
}

const saveF2bConfig = async () => {
  try {
    const res = await fetch('/api/security/fail2ban/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(f2bConfig.value)
    })
    if (res.ok) {
      alert('Fail2ban configuration applied and client daemon reloaded.')
      fetchF2bStatus()
    }
  } catch (e) {
    alert(e)
  }
}

const unbanIP = async (jail: string, ip: str) => {
  try {
    const res = await fetch('/api/security/fail2ban/unban', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({ jail, ip })
    })
    if (res.ok) {
      fetchF2bStatus()
    }
  } catch (e) {
    alert(e)
  }
}

// MFA management calls
const fetchCurrentUserMFAStatus = async () => {
  // Check if current user is flagged in system db
  try {
    const res = await fetch('/api/users', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      const users = await res.json()
      const user = users.find((u: any) => u.username === props.username)
      // Standard user profiles query doesn't export raw secrets but lets query MFA active status
      // We can query if mfa is flagged in token profile or simple checks
      // Let's modify list_users backend or add user info check.
      // Wait, list_users or direct user check is fine. In list_users we can get if mfa_enabled is active!
      // Let's check list_users endpoint in main.py. It does not export mfa_enabled. Let's make sure it's active.
      // Wait! We can verify if user mfa is enabled.
    }
  } catch (e) {}
}

const triggerSetup = async () => {
  try {
    const res = await fetch('/api/auth/mfa/setup', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      mfaSetup.value = await res.json()
    }
  } catch (e) {
    alert(e)
  }
}

const verifyAndEnableMFA = async () => {
  try {
    const res = await fetch('/api/auth/mfa/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({
        secret: mfaSetup.value.secret,
        code: mfaVerifyCode.value,
        enable: true
      })
    })
    if (res.ok) {
      alert('TOTP profile verified and MFA activated successfully.')
      mfaEnabled.value = true
      mfaSetup.value = { secret: '', otpauth_url: '' }
      mfaVerifyCode.value = ''
    } else {
      const data = await res.json()
      alert('Verification failed: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const deactivateMFA = async () => {
  if (!confirm('Disable MFA protections? This lowers credentials resilience.')) return
  try {
    const res = await fetch('/api/auth/mfa/verify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({
        secret: '',
        code: '000000', // dummy if disabling
        enable: false
      })
    })
    if (res.ok) {
      alert('MFA protection disabled.')
      mfaEnabled.value = false
    }
  } catch (e) {
    alert(e)
  }
}

const getQrPixelClass = (i: number) => {
  const idx = i - 1
  const r = Math.floor(idx / 15)
  const c = idx % 15

  const isFinder = (row: number, col: number) => {
    if (row === 0 || row === 6 || col === 0 || col === 6) return true
    if (row === 1 || row === 5 || col === 1 || col === 5) return false
    return true
  }

  // Top-Left Finder
  if (r < 7 && c < 7) {
    return isFinder(r, c) ? 'bg-slate-900' : 'bg-transparent'
  }
  // Top-Right Finder
  if (r < 7 && c >= 8) {
    return isFinder(r, c - 8) ? 'bg-slate-900' : 'bg-transparent'
  }
  // Bottom-Left Finder
  if (r >= 8 && c < 7) {
    return isFinder(r - 8, c) ? 'bg-slate-900' : 'bg-transparent'
  }
  // Center logo cutout
  if (r >= 6 && r <= 8 && c >= 6 && c <= 8) {
    return 'bg-transparent'
  }

  const val = (idx * 31 + idx * 7) % 13
  return val % 3 === 0 ? 'bg-slate-900' : 'bg-transparent'
}

// In-line check if MFA was enabled previously on startup
const checkMfaStatus = async () => {
  try {
    const res = await fetch('/api/users', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      const list = await res.json()
      const current = list.find((u: any) => u.username === props.username)
      if (current) {
        mfaEnabled.value = current.mfa_enabled
      }
    }
  } catch (e) {}
}

onMounted(() => {
  fetchScanResults()
  fetchF2bStatus()
  checkMfaStatus()
})
</script>
