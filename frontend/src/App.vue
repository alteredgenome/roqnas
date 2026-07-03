<template>
  <div class="relative w-full h-full overflow-hidden bg-[#0a0f1d]">
    <!-- Background Animated Blobs -->
    <div class="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-blue-600/20 blur-[120px] pointer-events-none animate-pulse"></div>
    <div class="absolute -bottom-40 -right-40 w-96 h-96 rounded-full bg-purple-600/20 blur-[120px] pointer-events-none animate-pulse" style="animation-duration: 6s;"></div>
    <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-indigo-500/5 blur-[160px] pointer-events-none"></div>

    <!-- Login Panel -->
    <div v-if="!token" class="flex items-center justify-center w-full h-full p-4 relative z-10">
      <div class="w-full max-w-md p-8 rounded-2xl glass-panel glow-border flex flex-col items-center">
        <!-- Logo -->
        <div class="flex items-center gap-3 mb-8">
          <div class="w-12 h-12 rounded-xl bg-gradient-to-tr from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span class="text-xl font-bold text-white tracking-wide">R</span>
          </div>
          <div>
            <h1 class="text-2xl font-bold tracking-tight text-white">RoqNAS</h1>
            <p class="text-xs text-slate-400">Next-Gen Storage Controller</p>
          </div>
        </div>

        <h2 class="text-lg font-medium mb-6 text-slate-300 text-center">
          {{ mfaRequired ? 'Enter MFA Verification Code' : 'Unlock Control Center' }}
        </h2>

        <!-- MFA Code Entry Form -->
        <form v-if="mfaRequired" @submit.prevent="handleMfaVerify" class="w-full space-y-5">
          <p class="text-xs text-slate-400 text-center leading-relaxed">Account requires multi-factor authentication. Input the 6-digit verification code token from your authenticator app.</p>
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">TOTP Token Code</label>
            <div class="relative">
              <input 
                v-model="totpCode" 
                type="text" 
                required 
                maxlength="6"
                placeholder="123456" 
                class="w-full px-4 py-3 rounded-xl glass-input pl-10 text-center tracking-[0.4em] font-mono text-sm" 
              />
              <span class="absolute left-3.5 top-3.5 text-slate-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </span>
            </div>
          </div>

          <div v-if="error" class="p-3 text-xs bg-red-950/50 border border-red-500/30 rounded-lg text-red-300">
            {{ error }}
          </div>

          <div class="flex gap-3">
            <button 
              type="submit" 
              :disabled="loading"
              class="flex-1 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold shadow-lg shadow-blue-500/25 hover:from-blue-600 hover:to-indigo-700 active:scale-[0.98] transition duration-200 disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2 text-sm"
            >
              <span v-if="loading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              <span>Verify Code</span>
            </button>
            <button 
              type="button" 
              @click="cancelMfa"
              class="px-4 py-3 rounded-xl bg-slate-800 text-slate-300 font-semibold hover:bg-slate-700 transition text-sm"
            >
              Cancel
            </button>
          </div>
        </form>

        <!-- Standard Login Form -->
        <form v-else @submit.prevent="handleLogin" class="w-full space-y-5">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Username</label>
            <div class="relative">
              <input 
                v-model="username" 
                type="text" 
                required 
                placeholder="admin" 
                class="w-full px-4 py-3 rounded-xl glass-input pl-10" 
              />
              <span class="absolute left-3.5 top-3.5 text-slate-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </span>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Password</label>
            <div class="relative">
              <input 
                v-model="password" 
                type="password" 
                required 
                placeholder="••••••••" 
                class="w-full px-4 py-3 rounded-xl glass-input pl-10" 
              />
              <span class="absolute left-3.5 top-3.5 text-slate-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </span>
            </div>
          </div>

          <div v-if="error" class="p-3 text-xs bg-red-950/50 border border-red-500/30 rounded-lg text-red-300">
            {{ error }}
          </div>

          <button 
            type="submit" 
            :disabled="loading"
            class="w-full py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-semibold shadow-lg shadow-blue-500/25 hover:from-blue-600 hover:to-indigo-700 active:scale-[0.98] transition duration-200 disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
          >
            <span v-if="loading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            <span>{{ loading ? 'Authenticating...' : 'Sign In' }}</span>
          </button>
        </form>

        <p class="mt-6 text-xs text-slate-500">Default Credentials: <code class="text-slate-400 font-mono">admin</code> / <code class="text-slate-400 font-mono">admin</code></p>
      </div>
    </div>

    <!-- Active Workspace -->
    <Workspace 
      v-else 
      :token="token" 
      :username="authUsername"
      @logout="handleLogout" 
      class="relative z-10 w-full h-full"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Workspace from './components/Workspace.vue'

const token = ref<string | null>(localStorage.getItem('roqnas_token'))
const authUsername = ref<string>(localStorage.getItem('roqnas_username') || 'admin')
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

// MFA login controls
const mfaRequired = ref(false)
const challengeToken = ref('')
const totpCode = ref('')

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value
      })
    })
    
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || 'Authentication failed')
    }

    if (data.mfa_required) {
      mfaRequired.value = true
      challengeToken.value = data.challenge_token
      return
    }

    localStorage.setItem('roqnas_token', data.token)
    localStorage.setItem('roqnas_username', data.username)
    token.value = data.token
    authUsername.value = data.username
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const handleMfaVerify = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/auth/login/mfa', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        challenge_token: challengeToken.value,
        code: totpCode.value
      })
    })

    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || 'MFA code verification failed')
    }

    localStorage.setItem('roqnas_token', data.token)
    localStorage.setItem('roqnas_username', data.username)
    token.value = data.token
    authUsername.value = data.username
    mfaRequired.value = false
    challengeToken.value = ''
    totpCode.value = ''
  } catch (err: any) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const cancelMfa = () => {
  mfaRequired.value = false
  challengeToken.value = ''
  totpCode.value = ''
  username.value = ''
  password.value = ''
  error.value = ''
}

const handleLogout = () => {
  localStorage.removeItem('roqnas_token')
  localStorage.removeItem('roqnas_username')
  token.value = null
}
</script>
