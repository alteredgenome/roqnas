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

      <!-- TAB 1: ACTIVE DIRECTORY -->
      <div v-if="activeTab === 'ad'" class="space-y-6 animate-in fade-in duration-150">
        
        <!-- AD Status Card -->
        <div class="p-6 rounded-2xl glass-panel-light border flex items-center justify-between"
             :class="adStatus.joined ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-slate-800/40 border-white/5 text-slate-400'">
          <div class="flex items-center gap-3">
            <span class="relative flex h-3.5 w-3.5">
              <span v-if="adStatus.joined" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-3.5 w-3.5" :class="adStatus.joined ? 'bg-emerald-500' : 'bg-slate-600'"></span>
            </span>
            <div>
              <h3 class="text-xs font-bold uppercase tracking-wider">Active Directory: {{ adStatus.joined ? 'CONNECTED' : 'DISCONNECTED' }}</h3>
              <div v-if="adStatus.joined" class="grid grid-cols-2 gap-x-6 gap-y-1 text-[11px] text-slate-300 font-mono mt-1.5">
                <div>Domain: <span class="font-bold text-white">{{ adStatus.domain }}</span></div>
                <div>DC Server IP: <span class="font-bold text-white">{{ adStatus.dc_ip }}</span></div>
                <div>Connection Log: <span class="text-slate-400">{{ adStatus.joined_at }}</span></div>
                <div>Kerberos Ticket Expiry: <span class="text-yellow-400">{{ adStatus.ticket_expiry }}</span></div>
              </div>
              <div v-else class="text-[10px] text-slate-500 uppercase mt-0.5 font-semibold">NAS is not joined to a domain controller. Local users database active.</div>
            </div>
          </div>
          <button v-if="adStatus.joined" @click="leaveAD" class="px-3 py-1.5 bg-red-600 hover:bg-red-500 rounded-lg text-xs font-semibold text-white transition active:scale-[0.98]">
            Leave Domain
          </button>
        </div>

        <!-- Join AD Form -->
        <div v-if="!adStatus.joined" class="p-6 rounded-2xl glass-panel-light space-y-4 border border-white/5">
          <h3 class="text-xs font-bold tracking-wider uppercase text-slate-300">Join Active Directory Domain</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Target AD Domain (FQDN)</label>
              <input v-model="adForm.domain" placeholder="corp.rocknas.internal" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Domain DNS Server IP</label>
              <input v-model="adForm.dns_ip" placeholder="192.168.1.10" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">AD Admin Username</label>
              <input v-model="adForm.username" placeholder="administrator" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">AD Admin Password</label>
              <input v-model="adForm.password" placeholder="••••••••" type="password" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>
          <button @click="joinAD" :disabled="!adForm.domain || !adForm.username" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none">
            Join Domain
          </button>
        </div>
      </div>

      <!-- TAB 2: LDAP CLIENT -->
      <div v-if="activeTab === 'ldap'" class="space-y-6 animate-in fade-in duration-150">
        <!-- LDAP status card -->
        <div class="p-6 rounded-2xl glass-panel-light border flex items-center justify-between"
             :class="ldapStatus.connected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-slate-800/40 border-white/5 text-slate-400'">
          <div class="flex items-center gap-3">
            <span class="relative flex h-3.5 w-3.5">
              <span v-if="ldapStatus.connected" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-3.5 w-3.5" :class="ldapStatus.connected ? 'bg-emerald-500' : 'bg-slate-600'"></span>
            </span>
            <div>
              <h3 class="text-xs font-bold uppercase tracking-wider">LDAP client: {{ ldapStatus.connected ? 'ACTIVE' : 'INACTIVE' }}</h3>
              <div v-if="ldapStatus.connected" class="grid grid-cols-2 gap-x-6 gap-y-1 text-[11px] text-slate-300 font-mono mt-1.5">
                <div>Server URL: <span class="font-bold text-white">{{ ldapStatus.server }}</span></div>
                <div>Base DN: <span class="font-bold text-white text-[10px]">{{ ldapStatus.base_dn }}</span></div>
                <div>Bind DN: <span class="text-slate-400 text-[10px]">{{ ldapStatus.bind_dn }}</span></div>
                <div>Imported Accounts: <span class="text-blue-400 font-bold">{{ ldapStatus.imported_users_count }} Users</span></div>
              </div>
              <div v-else class="text-[10px] text-slate-500 uppercase mt-0.5 font-semibold">NAS has no LDAP binding set. Querying NSS local maps only.</div>
            </div>
          </div>
        </div>

        <!-- Configure LDAP form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4 border border-white/5">
          <h3 class="text-xs font-bold tracking-wider uppercase text-slate-300">LDAP Binding Parameters</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">LDAP Server URI</label>
              <input v-model="ldapForm.server" placeholder="ldap://ldap.rocknas.internal" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Base DN</label>
              <input v-model="ldapForm.base_dn" placeholder="dc=rocknas,dc=internal" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Bind DN (User Credentials)</label>
              <input v-model="ldapForm.bind_dn" placeholder="cn=admin,dc=rocknas,dc=internal" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Bind Password</label>
              <input v-model="ldapForm.password" placeholder="••••••••" type="password" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>
          <button @click="saveLDAP" :disabled="!ldapForm.server || !ldapForm.base_dn" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none">
            Bind LDAP Client
          </button>
        </div>
      </div>

      <!-- TAB 3: SINGLE SIGN-ON (SSO) -->
      <div v-if="activeTab === 'sso'" class="space-y-6 animate-in fade-in duration-150">
        <!-- SSO Status Card -->
        <div class="p-6 rounded-2xl glass-panel-light border flex items-center justify-between"
             :class="ssoStatus.enabled ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-slate-800/40 border-white/5 text-slate-400'">
          <div class="flex items-center gap-3">
            <span class="relative flex h-3.5 w-3.5">
              <span v-if="ssoStatus.enabled" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-3.5 w-3.5" :class="ssoStatus.enabled ? 'bg-emerald-500' : 'bg-slate-600'"></span>
            </span>
            <div>
              <h3 class="text-xs font-bold uppercase tracking-wider">SSO Console Access: {{ ssoStatus.enabled ? 'ENFORCED' : 'LOCAL ONLY' }}</h3>
              <div v-if="ssoStatus.enabled" class="grid grid-cols-2 gap-x-6 gap-y-1 text-[11px] text-slate-300 font-mono mt-1.5">
                <div>SSO Protocol: <span class="font-bold text-white">{{ ssoStatus.provider }}</span></div>
                <div>Metadata URL: <span class="font-bold text-white text-[10px]">{{ ssoStatus.metadata_url }}</span></div>
                <div>Client ID: <span class="text-slate-400 text-[10px]">{{ ssoStatus.client_id }}</span></div>
                <div>Redirect URI: <span class="text-slate-400 text-[10px]">{{ ssoStatus.redirect_url }}</span></div>
              </div>
              <div v-else class="text-[10px] text-slate-500 uppercase mt-0.5 font-semibold">Web console relies on local SHA256 hashed password locks.</div>
            </div>
          </div>
        </div>

        <!-- Configure SSO Form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4 border border-white/5">
          <h3 class="text-xs font-bold tracking-wider uppercase text-slate-300">Identity Provider Federation Configurations</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">SSO Protocol</label>
              <select v-model="ssoForm.provider" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option value="OpenID Connect">OpenID Connect (OIDC)</option>
                <option value="SAML 2.0">SAML 2.0 (AzureAD / Okta)</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">IdP Metadata / Discovery Endpoint</label>
              <input v-model="ssoForm.metadata_url" placeholder="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Client ID (Application ID)</label>
              <input v-model="ssoForm.client_id" placeholder="rocknas-dashboard" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Client Secret (Key Credential)</label>
              <input v-model="ssoForm.client_secret" placeholder="••••••••" type="password" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>

          <div class="flex items-center gap-2 pt-2 select-none">
            <input id="enforce_sso" type="checkbox" v-model="ssoForm.enabled" class="rounded text-blue-500 bg-slate-900 border-white/20" />
            <label for="enforce_sso" class="text-xs font-semibold text-slate-300 cursor-pointer">Enforce Identity Provider login redirects</label>
          </div>

          <button @click="saveSSO" :disabled="!ssoForm.metadata_url || !ssoForm.client_id" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white transition active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none">
            Save SSO Settings
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

const activeTab = ref('ad')
const tabs = [
  { id: 'ad', name: 'Active Directory' },
  { id: 'ldap', name: 'LDAP Directory' },
  { id: 'sso', name: 'Console SSO' }
]

// Status bindings
const adStatus = ref<any>({ joined: false, domain: '', dc_ip: '', joined_at: '', ticket_expiry: '' })
const ldapStatus = ref<any>({ connected: false, server: '', base_dn: '', bind_dn: '', imported_users_count: 0 })
const ssoStatus = ref<any>({ enabled: false, provider: 'OpenID Connect', metadata_url: '', client_id: '', redirect_url: '' })

// Forms
const adForm = ref({ domain: '', username: 'administrator', password: '', dns_ip: '' })
const ldapForm = ref({ server: '', base_dn: '', bind_dn: '', password: '' })
const ssoForm = ref({ enabled: false, provider: 'OpenID Connect', metadata_url: '', client_id: '', client_secret: '' })

const fetchADStatus = async () => {
  try {
    const res = await fetch('/api/directory/ad', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) adStatus.value = await res.json()
  } catch (e) {
    console.error(e)
  }
}

const fetchLDAPStatus = async () => {
  try {
    const res = await fetch('/api/directory/ldap', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      ldapStatus.value = await res.json()
      ldapForm.value.server = ldapStatus.value.server
      ldapForm.value.base_dn = ldapStatus.value.base_dn
      ldapForm.value.bind_dn = ldapStatus.value.bind_dn
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchSSOStatus = async () => {
  try {
    const res = await fetch('/api/directory/sso', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      ssoStatus.value = await res.json()
      ssoForm.value.enabled = ssoStatus.value.enabled
      ssoForm.value.provider = ssoStatus.value.provider
      ssoForm.value.metadata_url = ssoStatus.value.metadata_url
      ssoForm.value.client_id = ssoStatus.value.client_id
    }
  } catch (e) {
    console.error(e)
  }
}

const joinAD = async () => {
  try {
    const res = await fetch('/api/directory/ad/join', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(adForm.value)
    })
    if (res.ok) {
      alert(`NAS successfully registered inside Active Directory domain: ${adForm.value.domain.toUpperCase()}`)
      adForm.value.password = ''
      fetchADStatus()
    } else {
      const data = await res.json()
      alert('AD Join error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const leaveAD = async () => {
  if (!confirm('Leave Active Directory domain? All domain mapping will be disabled.')) return
  try {
    const res = await fetch('/api/directory/ad/leave', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      alert('Domain leave complete. Local Winbind server targets disabled.')
      fetchADStatus()
    }
  } catch (e) {
    alert(e)
  }
}

const saveLDAP = async () => {
  try {
    const res = await fetch('/api/directory/ldap/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(ldapForm.value)
    })
    if (res.ok) {
      alert('LDAP configurations successfully saved.')
      fetchLDAPStatus()
    } else {
      const data = await res.json()
      alert('LDAP config error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const saveSSO = async () => {
  try {
    const res = await fetch('/api/directory/sso/config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(ssoForm.value)
    })
    if (res.ok) {
      alert('Single Sign-On metadata updated.')
      fetchSSOStatus()
    }
  } catch (e) {
    alert(e)
  }
}

onMounted(() => {
  fetchADStatus()
  fetchLDAPStatus()
  fetchSSOStatus()
})
</script>
