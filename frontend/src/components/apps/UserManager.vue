<template>
  <div class="p-6 space-y-6 text-slate-200">
    <div class="space-y-3">
      <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Authorized System Accounts</h3>
      <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
        <table class="w-full border-collapse text-left text-xs">
          <thead>
            <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
              <th class="p-3">Username</th>
              <th class="p-3">Access Role</th>
              <th class="p-3">Email Address</th>
              <th class="p-3">Created Date</th>
              <th class="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5">
            <tr v-for="u in users" :key="u.username" class="hover:bg-white/5">
              <td class="p-3 font-semibold text-blue-400 font-mono">{{ u.username }}</td>
              <td class="p-3">
                <span class="text-[10px] font-bold px-2 py-0.5 rounded capitalize"
                  :class="u.role === 'admin' ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-800 text-slate-400'">
                  {{ u.role }}
                </span>
              </td>
              <td class="p-3">{{ u.email || '-' }}</td>
              <td class="p-3 text-slate-400">{{ u.created_at || 'Pre-installed' }}</td>
              <td class="p-3 text-right">
                <button @click="deleteUser(u.username)" :disabled="u.username === 'admin'" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition disabled:opacity-20 disabled:pointer-events-none">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create User Form -->
    <div class="p-6 rounded-2xl glass-panel-light space-y-4">
      <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Create Account / Sync smbpasswd</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Username</label>
          <input v-model="form.username" placeholder="john_doe" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Email Address</label>
          <input v-model="form.email" placeholder="john@example.com" type="email" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Password</label>
          <input v-model="form.password" placeholder="••••••••" type="password" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">System Permission Role</label>
          <select v-model="form.role" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
            <option value="standard">Standard User (Storage Access Only)</option>
            <option value="admin">Administrator (Full OS Console Control)</option>
          </select>
        </div>
      </div>

      <button @click="createUser" :disabled="!form.username || !form.password" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
        Register Account
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps({
  token: String
})

const users = ref<any[]>([])

const form = ref({
  username: '',
  password: '',
  role: 'standard',
  email: ''
})

const fetchUsers = async () => {
  try {
    const res = await fetch('/api/users', {
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      users.value = await res.json()
    }
  } catch (e) {
    console.error('Failed fetching user list', e)
  }
}

const createUser = async () => {
  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(form.value)
    })
    if (res.ok) {
      alert('User successfully created and credentials synced.')
      form.value = { username: '', password: '', role: 'standard', email: '' }
      fetchUsers()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const deleteUser = async (username: string) => {
  if (!confirm(`Delete user "${username}" from the database and remove filesystem access?`)) return
  try {
    const res = await fetch(`/api/users/${username}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      fetchUsers()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
