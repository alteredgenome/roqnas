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
      
      <!-- TAB 1: PHYSICAL DISKS -->
      <div v-if="activeTab === 'disks'" class="space-y-4">
        <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Detected Block Devices</h3>
        <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
          <table class="w-full border-collapse text-left text-xs">
            <thead>
              <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                <th class="p-3">Device</th>
                <th class="p-3">Model / Vendor</th>
                <th class="p-3">Size</th>
                <th class="p-3">Type</th>
                <th class="p-3">FSType / Encryption</th>
                <th class="p-3">Mountpoint</th>
                <th class="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr v-for="disk in disks" :key="disk.name" class="hover:bg-white/5 transition">
                <td class="p-3 font-mono font-bold text-blue-400">/dev/{{ disk.name }}</td>
                <td class="p-3">{{ disk.model || 'Unknown' }} ({{ disk.vendor || 'Generic' }})</td>
                <td class="p-3 font-semibold">{{ disk.size }}</td>
                <td class="p-3 uppercase text-[10px] bg-slate-800/40 px-2 py-0.5 rounded w-max inline-block mt-2">{{ disk.type }}</td>
                <td class="p-3">
                  <span v-if="disk.fstype === 'crypto_LUKS'" class="text-yellow-400 flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    <span>LUKS Locked</span>
                  </span>
                  <span v-else-if="disk.mountpoint && disk.mountpoint.startsWith('/dev/mapper/')" class="text-emerald-400 flex items-center gap-1">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" /></svg>
                    <span>LUKS Unlocked</span>
                  </span>
                  <span v-else class="text-slate-400">{{ getDiskFSType(disk) }}</span>
                </td>
                <td class="p-3 font-mono text-[11px] text-slate-400">{{ getDiskMountpoint(disk) }}</td>
                <td class="p-3 text-right space-x-1.5">
                  <button v-if="!isDiskAssigned(disk)" @click="promptEncrypt(disk.name)" class="px-2 py-0.5 bg-yellow-600/20 border border-yellow-500/30 hover:bg-yellow-600 hover:text-white rounded text-[10px] transition">LUKS Encrypt</button>
                  <button v-if="disk.fstype === 'crypto_LUKS'" @click="promptUnlock(disk.name)" class="px-2 py-0.5 bg-emerald-600/20 border border-emerald-500/30 hover:bg-emerald-600 hover:text-white rounded text-[10px] transition">Unlock</button>
                  <button v-if="disk.mountpoint && disk.mountpoint.startsWith('/dev/mapper/')" @click="lockDisk(disk.mountpoint)" class="px-2 py-0.5 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-[10px] transition">Lock</button>
                </td>
              </tr>
              <tr v-if="disks.length === 0">
                <td colspan="7" class="p-4 text-center text-slate-500">Scanning for storage devices...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- TAB 2: MDADM RAID -->
      <div v-if="activeTab === 'mdadm'" class="space-y-6">
        <!-- List active MD arrays -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Active Software RAID Arrays</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Array Name</th>
                  <th class="p-3">RAID Level</th>
                  <th class="p-3">Active Disks</th>
                  <th class="p-3">Mountpoint</th>
                  <th class="p-3">Status</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="array in mdadmArrays" :key="array.name" class="hover:bg-white/5">
                  <td class="p-3 font-mono font-bold text-blue-400">/dev/{{ array.name }}</td>
                  <td class="p-3 font-semibold">RAID {{ array.level }}</td>
                  <td class="p-3">
                    <span v-for="d in array.disks" :key="d" class="font-mono bg-slate-800/60 px-1.5 py-0.5 rounded text-[10px] mr-1">{{ d }}</span>
                  </td>
                  <td class="p-3 font-mono text-[11px]">{{ array.mountpoint || '-' }}</td>
                  <td class="p-3">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded"
                      :class="array.status === 'clean' || array.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'">
                      {{ array.status }}
                    </span>
                  </td>
                  <td class="p-3 text-right space-x-1.5">
                    <button @click="openMdadmManage(array)" class="px-2 py-1 bg-indigo-600/20 border border-indigo-500/30 hover:bg-indigo-600 hover:text-white rounded text-xs transition">Manage</button>
                    <button @click="destroyMdadm(array.name)" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition">Destroy</button>
                  </td>
                </tr>
                <tr v-if="mdadmArrays.length === 0">
                  <td colspan="6" class="p-4 text-center text-slate-500">No active mdadm arrays configured.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Build mdadm Array Form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Create Software RAID Array</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Array Name</label>
              <input v-model="newMd.name" placeholder="md0" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">RAID Level</label>
              <select v-model="newMd.level" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option :value="0">RAID 0 (Striping)</option>
                <option :value="1">RAID 1 (Mirroring)</option>
                <option :value="5">RAID 5 (Parity)</option>
                <option :value="6">RAID 6 (Double Parity)</option>
                <option :value="10">RAID 10 (Striped Mirror)</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Filesystem Formatting</label>
              <select v-model="newMd.fstype" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option value="ext4">ext4 (Standard Linux)</option>
                <option value="xfs">XFS (Enterprise Storage)</option>
                <option value="none">none (Raw / Unformatted RAID)</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-2">Select Unassigned Disks</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="d in availableDisks" :key="d.name" class="flex items-center gap-2 bg-white/5 border border-white/10 px-3 py-2 rounded-lg cursor-pointer hover:bg-white/10 select-none text-xs">
                <input type="checkbox" :value="`/dev/${d.name}`" v-model="newMd.disks" class="rounded text-blue-500 bg-slate-900 border-white/20" />
                <span class="font-mono font-bold text-blue-400">/dev/{{ d.name }}</span>
                <span class="text-slate-400">({{ d.size }})</span>
              </label>
              <div v-if="availableDisks.length === 0" class="text-xs text-slate-500">No unassigned block devices available for RAID orchestration.</div>
            </div>
          </div>

          <button @click="createMdadm" :disabled="!newMd.name || newMd.disks.length === 0" class="px-4 py-2 bg-blue-600 rounded-lg font-semibold text-xs text-white hover:bg-blue-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Build RAID Volume
          </button>
        </div>
      </div>

      <!-- TAB 3: ZFS POOLS & DATASETS -->
      <div v-if="activeTab === 'zfs'" class="space-y-6">
        <!-- ZFS Pools listing -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Active Storage Pools (zpools)</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Pool Name</th>
                  <th class="p-3">Layout</th>
                  <th class="p-3">Disks</th>
                  <th class="p-3">Status</th>
                  <th class="p-3">Mountpoint</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="pool in zpools" :key="pool.name" class="hover:bg-white/5">
                  <td class="p-3 font-bold text-indigo-400">{{ pool.name }}</td>
                  <td class="p-3 capitalize">{{ pool.layout }}</td>
                  <td class="p-3">
                    <span v-for="d in pool.disks" :key="d" class="font-mono bg-slate-800/60 px-1.5 py-0.5 rounded text-[10px] mr-1">{{ d }}</span>
                  </td>
                  <td class="p-3">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">{{ pool.status }}</span>
                  </td>
                  <td class="p-3 font-mono text-[11px]">{{ pool.mountpoint }}</td>
                  <td class="p-3 text-right space-x-1.5">
                    <button @click="openZpoolManage(pool)" class="px-2 py-1 bg-indigo-600/20 border border-indigo-500/30 hover:bg-indigo-600 hover:text-white rounded text-xs transition">Manage</button>
                    <button @click="destroyZpool(pool.name)" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition">Destroy</button>
                  </td>
                </tr>
                <tr v-if="zpools.length === 0">
                  <td colspan="6" class="p-4 text-center text-slate-500">No ZFS Pools created yet.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Create ZFS pool form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Create ZFS Storage Pool</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Pool Name</label>
              <input v-model="newPool.name" placeholder="tank" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Virtual Device Layout</label>
              <select v-model="newPool.layout" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option value="striped">Striped (RAID 0 - No parity)</option>
                <option value="mirror">Mirror (RAID 1 - Redundancy)</option>
                <option value="raidz1">RaidZ1 (RAID 5 - Single Parity)</option>
                <option value="raidz2">RaidZ2 (RAID 6 - Double Parity)</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-2">Select Block Devices</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="d in availableDisks" :key="d.name" class="flex items-center gap-2 bg-white/5 border border-white/10 px-3 py-2 rounded-lg cursor-pointer hover:bg-white/10 select-none text-xs">
                <input type="checkbox" :value="`/dev/${d.name}`" v-model="newPool.disks" class="rounded text-blue-500 bg-slate-900 border-white/20" />
                <span class="font-mono font-bold text-indigo-400">/dev/{{ d.name }}</span>
                <span class="text-slate-400">({{ d.size }})</span>
              </label>
              <div v-if="availableDisks.length === 0" class="text-xs text-slate-500">No unassigned block devices available for ZFS pool creation.</div>
            </div>
          </div>

          <button @click="createZpool" :disabled="!newPool.name || newPool.disks.length === 0" class="px-4 py-2 bg-indigo-600 rounded-lg font-semibold text-xs text-white hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Create ZFS Pool
          </button>
        </div>

        <hr class="border-white/5" />

        <!-- ZFS Datasets listing -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">ZFS Datasets</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Dataset Name</th>
                  <th class="p-3">Parent Pool</th>
                  <th class="p-3">Used</th>
                  <th class="p-3">Available</th>
                  <th class="p-3">Mountpoint</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="ds in datasets" :key="ds.name" class="hover:bg-white/5">
                  <td class="p-3 font-semibold text-indigo-300 font-mono">{{ ds.name }}</td>
                  <td class="p-3 text-slate-400 font-mono">{{ ds.pool }}</td>
                  <td class="p-3">{{ ds.used }}</td>
                  <td class="p-3 text-slate-400">{{ ds.available }}</td>
                  <td class="p-3 font-mono text-[11px]">{{ ds.mountpoint }}</td>
                  <td class="p-3 text-right">
                    <button @click="destroyDataset(ds.name)" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition">Destroy</button>
                  </td>
                </tr>
                <tr v-if="datasets.length === 0">
                  <td colspan="6" class="p-4 text-center text-slate-500">No ZFS datasets configured.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Create ZFS dataset form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Create ZFS Dataset</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Parent Pool</label>
              <select v-model="newDataset.pool" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option v-for="pool in zpools" :key="pool.name" :value="pool.name">{{ pool.name }}</option>
                <option v-if="zpools.length === 0" value="">-- Create a pool first --</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Dataset Name</label>
              <input v-model="newDataset.name" placeholder="media" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
          </div>
          <button @click="createDataset" :disabled="!newDataset.pool || !newDataset.name" class="px-4 py-2 bg-indigo-600 rounded-lg font-semibold text-xs text-white hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Create Dataset
          </button>
        </div>

        <hr class="border-white/5" />

        <!-- ZFS Volumes (Zvols) listing -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">ZFS Volumes (Zvols - Virtual block devices)</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Zvol Path</th>
                  <th class="p-3">Parent Pool</th>
                  <th class="p-3">Size (GB)</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="zvol in zvols" :key="zvol.fullname" class="hover:bg-white/5">
                  <td class="p-3 font-semibold text-indigo-300 font-mono">/dev/zvol/{{ zvol.fullname }}</td>
                  <td class="p-3 text-slate-400 font-mono">{{ zvol.pool }}</td>
                  <td class="p-3 font-semibold">{{ zvol.size_gb }} GB</td>
                  <td class="p-3 text-right">
                    <button @click="destroyZvol(zvol.pool, zvol.name)" class="px-2 py-1 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-xs transition">Destroy</button>
                  </td>
                </tr>
                <tr v-if="zvols.length === 0">
                  <td colspan="4" class="p-4 text-center text-slate-500">No ZFS block volumes (Zvols) created yet.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Create Zvol form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Create ZFS Volume (Zvol)</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Parent Pool</label>
              <select v-model="newZvol.pool" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option v-for="pool in zpools" :key="pool.name" :value="pool.name">{{ pool.name }}</option>
                <option v-if="zpools.length === 0" value="">-- Create a pool first --</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Volume Name</label>
              <input v-model="newZvol.name" placeholder="zvol1" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Size (GB)</label>
              <input v-model="newZvol.size_gb" type="number" min="1" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
            </div>
          </div>
          <button @click="createZvol" :disabled="!newZvol.pool || !newZvol.name || newZvol.size_gb <= 0" class="px-4 py-2 bg-indigo-600 rounded-lg font-semibold text-xs text-white hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Create Zvol
          </button>
        </div>
      </div>

      <!-- TAB 4: ZFS SNAPSHOTS -->
      <div v-if="activeTab === 'snapshots'" class="space-y-6">
        <!-- Create Snapshot Form -->
        <div class="p-6 rounded-2xl glass-panel-light space-y-4">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Create Dataset Snapshot</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Select ZFS Volume / Dataset</label>
              <select v-model="newSnap.dataset" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-900">
                <option v-for="ds in datasets" :key="ds.name" :value="ds.name">{{ ds.name }}</option>
                <option v-if="datasets.length === 0" value="">-- Create a dataset first --</option>
              </select>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Snapshot Tag/Name</label>
              <input v-model="newSnap.name" placeholder="daily-backup-1" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
            </div>
          </div>
          <button @click="createSnapshot" :disabled="!newSnap.dataset || !newSnap.name" class="px-4 py-2 bg-indigo-600 rounded-lg font-semibold text-xs text-white hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none transition duration-150">
            Create Snapshot
          </button>
        </div>

        <!-- Snapshots list -->
        <div class="space-y-3">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-400">Dataset Snapshots (Holds & Immutability active)</h3>
          <div class="overflow-hidden rounded-xl glass-panel-light border border-white/5">
            <table class="w-full border-collapse text-left text-xs">
              <thead>
                <tr class="bg-white/5 border-b border-white/5 font-semibold text-slate-300">
                  <th class="p-3">Snapshot IQN</th>
                  <th class="p-3">Dataset</th>
                  <th class="p-3">Snapshot Name</th>
                  <th class="p-3">Used Space</th>
                  <th class="p-3">Creation Date</th>
                  <th class="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr v-for="snap in snapshots" :key="snap.name" class="hover:bg-white/5">
                  <td class="p-3 font-semibold text-teal-400 font-mono flex items-center gap-1.5">
                    <span v-if="snap.holds && snap.holds.length > 0" class="text-yellow-500" :title="`Locked holds: ${snap.holds.join(', ')}`">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    </span>
                    <span>{{ snap.name }}</span>
                  </td>
                  <td class="p-3 font-mono text-slate-400">{{ snap.dataset }}</td>
                  <td class="p-3 font-bold">@{{ snap.snapshot }}</td>
                  <td class="p-3">{{ snap.used }}</td>
                  <td class="p-3 text-slate-400">{{ snap.creation }}</td>
                  <td class="p-3 text-right space-x-1.5">
                    <button v-if="snap.holds && snap.holds.length > 0" @click="releaseHold(snap.name)" class="px-2 py-0.5 bg-yellow-600/20 border border-yellow-500/30 hover:bg-yellow-600 hover:text-white rounded text-[10px]">Unlock Hold</button>
                    <button v-else @click="applyHold(snap.name)" class="px-2 py-0.5 bg-blue-600/20 border border-blue-500/30 hover:bg-blue-600 hover:text-white rounded text-[10px]">Hold Lock</button>

                    <button @click="rollbackSnapshot(snap.name)" class="px-2 py-0.5 bg-emerald-600/20 border border-emerald-500/30 hover:bg-emerald-600 hover:text-white rounded text-[10px]">Rollback</button>
                    <button :disabled="snap.holds && snap.holds.length > 0" @click="destroySnapshot(snap.name)" class="px-2 py-0.5 bg-red-600/20 border border-red-500/30 hover:bg-red-600 hover:text-white rounded text-[10px] disabled:opacity-20 disabled:pointer-events-none">Delete</button>
                  </td>
                </tr>
                <tr v-if="snapshots.length === 0">
                  <td colspan="6" class="p-4 text-center text-slate-500">No active snapshots found.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </div>

    <!-- LUKS Encrypt Modal -->
    <div v-if="encryptTarget" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="w-full max-w-sm p-6 rounded-2xl glass-panel border border-white/10 shadow-2xl space-y-4 text-slate-200">
        <h3 class="text-sm font-semibold tracking-wider text-slate-300">Format with LUKS Encryption</h3>
        <p class="text-xs text-slate-400 font-medium">Warning: formatting /dev/{{ encryptTarget }} with LUKS encryption will destroy all data on the disk.</p>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Passphrase</label>
          <input v-model="luksPassword" type="password" placeholder="••••••••" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
        </div>
        <div class="flex gap-2 justify-end">
          <button @click="encryptDisk" :disabled="!luksPassword" class="px-3 py-1.5 bg-yellow-600 rounded-lg text-xs hover:bg-yellow-500 disabled:opacity-50 transition text-white">Format & Encrypt</button>
          <button @click="encryptTarget = null" class="px-3 py-1.5 bg-slate-800 rounded-lg text-xs hover:bg-slate-700 transition">Cancel</button>
        </div>
      </div>
    </div>

    <!-- LUKS Unlock Modal -->
    <div v-if="unlockTarget" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="w-full max-w-sm p-6 rounded-2xl glass-panel border border-white/10 shadow-2xl space-y-4 text-slate-200">
        <h3 class="text-sm font-semibold tracking-wider text-slate-300">Unlock LUKS Encrypted Volume</h3>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Mapper Name target</label>
          <input v-model="luksMapper" placeholder="secure_vol0" type="text" class="w-full px-3 py-2 rounded-lg glass-input text-xs font-mono" />
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Passphrase</label>
          <input v-model="luksPassword" type="password" placeholder="••••••••" class="w-full px-3 py-2 rounded-lg glass-input text-xs" />
        </div>
        <div class="flex gap-2 justify-end">
          <button @click="unlockDisk" :disabled="!luksPassword || !luksMapper" class="px-3 py-1.5 bg-emerald-600 rounded-lg text-xs hover:bg-emerald-500 disabled:opacity-50 transition text-white">Unlock Device</button>
          <button @click="unlockTarget = null" class="px-3 py-1.5 bg-slate-800 rounded-lg text-xs hover:bg-slate-700 transition">Cancel</button>
        </div>
      </div>
    </div>

    <!-- ZFS Pool Management Modal -->
    <div v-if="selectedPool" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-slate-900 border border-white/10 rounded-2xl p-6 w-full max-w-lg space-y-6 shadow-2xl">
        <div class="flex justify-between items-center">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Manage ZFS Pool: {{ selectedPool.name }}</h3>
          <button @click="selectedPool = null" class="text-slate-400 hover:text-white text-lg">&times;</button>
        </div>

        <!-- Mode selection tabs -->
        <div class="flex border-b border-white/5 bg-white/5 p-1 rounded-lg gap-2">
          <button @click="zpoolMode = 'add_vdev'" :class="zpoolMode === 'add_vdev' ? 'bg-blue-600 text-white' : 'text-slate-400'" class="flex-1 py-1.5 text-xs font-semibold rounded transition">Add VDev</button>
          <button @click="zpoolMode = 'replace'" :class="zpoolMode === 'replace' ? 'bg-blue-600 text-white' : 'text-slate-400'" class="flex-1 py-1.5 text-xs font-semibold rounded transition">Replace Disk</button>
          <button @click="zpoolMode = 'expand_raidz'" :class="zpoolMode === 'expand_raidz' ? 'bg-blue-600 text-white' : 'text-slate-400'" class="flex-1 py-1.5 text-xs font-semibold rounded transition">RAIDZ Expand</button>
        </div>

        <!-- Form 1: Add VDev -->
        <div v-if="zpoolMode === 'add_vdev'" class="space-y-4 text-left">
          <p class="text-[11px] text-slate-400">Add a new striped, mirror, or raidz vdev directly into the pool. Data will stripe across vdevs.</p>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">New VDev Layout</label>
            <select v-model="vdevForm.layout" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-950">
              <option value="striped">Striped (RAID 0 - No parity)</option>
              <option value="mirror">Mirror (RAID 1 - Redundancy)</option>
              <option value="raidz1">RaidZ1 (RAID 5 - Single Parity)</option>
              <option value="raidz2">RaidZ2 (RAID 6 - Double Parity)</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-2">Select Unassigned Disks</label>
            <div class="flex flex-wrap gap-2">
              <label v-for="d in availableDisks" :key="d.name" class="flex items-center gap-2 bg-white/5 border border-white/10 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-white/10 text-xs">
                <input type="checkbox" :value="`/dev/${d.name}`" v-model="vdevForm.disks" class="rounded text-blue-500 bg-slate-900 border-white/20" />
                <span class="font-mono text-indigo-400">/dev/{{ d.name }}</span>
              </label>
              <div v-if="availableDisks.length === 0" class="text-xs text-slate-500">No unassigned disks available.</div>
            </div>
          </div>
          <button @click="submitAddVdev" class="w-full py-2 bg-blue-600 hover:bg-blue-700 text-xs font-semibold rounded-lg transition">Attach VDev</button>
        </div>

        <!-- Form 2: Replace Disk -->
        <div v-if="zpoolMode === 'replace'" class="space-y-4 text-left">
          <p class="text-[11px] text-slate-400">Select an existing disk to replace. The pool will resilver onto the new disk. Ensure the new disk is at least as large.</p>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Old Disk to Replace</label>
            <select v-model="replaceForm.oldDisk" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-950">
              <option v-for="d in selectedPool.disks" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">New Unassigned Disk</label>
            <select v-model="replaceForm.newDisk" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-950">
              <option v-for="d in availableDisks" :key="d.name" :value="`/dev/${d.name}`">/dev/{{ d.name }} ({{ d.size }})</option>
            </select>
          </div>
          <button @click="submitReplaceDisk" class="w-full py-2 bg-blue-600 hover:bg-blue-700 text-xs font-semibold rounded-lg transition">Start Resilver / Replacement</button>
        </div>

        <!-- Form 3: RAIDZ Expand -->
        <div v-if="zpoolMode === 'expand_raidz'" class="space-y-4 text-left">
          <p class="text-[11px] text-slate-400">Attach a new disk to your existing RAIDZ group. Requires ZFS 2.2.0+ (supported). The vdev structure will re-flow.</p>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">RAIDZ Group VDev</label>
            <input type="text" v-model="raidzExpandForm.vdev" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-950" placeholder="raidz1-0" />
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">New Disk to Attach</label>
            <select v-model="raidzExpandForm.newDisk" class="w-full px-3 py-2 rounded-lg glass-input text-xs bg-slate-950">
              <option v-for="d in availableDisks" :key="d.name" :value="`/dev/${d.name}`">/dev/{{ d.name }} ({{ d.size }})</option>
            </select>
          </div>
          <button @click="submitRaidzExpand" class="w-full py-2 bg-blue-600 hover:bg-blue-700 text-xs font-semibold rounded-lg transition">Expand RAIDZ Group</button>
        </div>
      </div>
    </div>

    <!-- MDADM RAID Management Modal -->
    <div v-if="selectedArray" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div class="bg-slate-900 border border-white/10 rounded-2xl p-6 w-full max-w-lg space-y-6 shadow-2xl">
        <div class="flex justify-between items-center">
          <h3 class="text-sm font-semibold tracking-wider uppercase text-slate-300">Manage RAID Array: /dev/{{ selectedArray.name }}</h3>
          <button @click="selectedArray = null" class="text-slate-400 hover:text-white text-lg">&times;</button>
        </div>

        <div class="space-y-4 text-left">
          <h4 class="text-[10px] font-bold text-slate-400 uppercase">Array Disk Members</h4>
          <div class="divide-y divide-white/5 max-h-40 overflow-auto">
            <div v-for="d in selectedArray.disks" :key="d" class="flex justify-between items-center py-2 text-xs font-mono">
              <span>{{ d }}</span>
              <div class="space-x-1.5">
                <button @click="failMdadmDisk(selectedArray.name, d)" class="px-1.5 py-0.5 bg-yellow-600/20 border border-yellow-500/30 text-[10px] rounded text-yellow-400 hover:bg-yellow-600 hover:text-white transition">Fail</button>
                <button @click="removeMdadmDisk(selectedArray.name, d)" class="px-1.5 py-0.5 bg-red-600/20 border border-red-500/30 text-[10px] rounded text-red-400 hover:bg-red-600 hover:text-white transition">Remove</button>
              </div>
            </div>
          </div>

          <hr class="border-white/5" />

          <!-- Add Disk / Spare -->
          <div class="space-y-3">
            <h4 class="text-[10px] font-bold text-slate-400 uppercase">Add Disk / Spare to Array</h4>
            <div class="flex gap-2">
              <select v-model="mdadmAddDiskTarget" class="flex-1 px-3 py-2 rounded-lg glass-input text-xs bg-slate-950">
                <option v-for="d in availableDisks" :key="d.name" :value="`/dev/${d.name}`">/dev/{{ d.name }} ({{ d.size }})</option>
              </select>
              <button @click="submitMdadmAddDisk" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold rounded-lg transition">Add Disk</button>
            </div>
          </div>

          <hr class="border-white/5" />

          <!-- Grow Array -->
          <div class="space-y-3">
            <h4 class="text-[10px] font-bold text-slate-400 uppercase">Grow Array Active Devices</h4>
            <p class="text-[10px] text-slate-400">After adding new disks, set the new total number of active member devices to grow the array capacity and auto-grow the filesystem.</p>
            <div class="flex gap-2">
              <input type="number" v-model="mdadmNewDevicesCount" class="w-24 px-3 py-2 rounded-lg glass-input text-xs bg-slate-950" :placeholder="selectedArray.disks.length.toString()" />
              <button @click="submitMdadmGrow" class="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-xs font-semibold rounded-lg transition">Grow Array Capacity</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps({
  token: String
})

const activeTab = ref('disks')
const tabs = [
  { id: 'disks', name: 'Physical Disks' },
  { id: 'mdadm', name: 'mdadm RAID' },
  { id: 'zfs', name: 'ZFS Pools & Datasets' },
  { id: 'snapshots', name: 'ZFS Snapshots' }
]

const disks = ref<any[]>([])
const mdadmArrays = ref<any[]>([])
const zpools = ref<any[]>([])
const datasets = ref<any[]>([])
const snapshots = ref<any[]>([])
const zvols = ref<any[]>([])

// Forms Ref
const newMd = ref({ name: '', level: 5, disks: [] as string[], fstype: 'ext4' })
const newPool = ref({ name: '', layout: 'striped', disks: [] as string[] })
const newDataset = ref({ pool: '', name: '' })
const newSnap = ref({ dataset: '', name: '' })
const newZvol = ref({ pool: '', name: '', size_gb: 10 })

// LUKS States
const encryptTarget = ref<string | null>(null)
const unlockTarget = ref<string | null>(null)
const luksPassword = ref('')
const luksMapper = ref('secure_vol0')

// Helper functions for disk assignment states
const isDiskAssigned = (disk: any) => {
  if (disk.fstype || disk.mountpoint) return true
  if (disk.children && disk.children.length > 0) {
    return disk.children.some((child: any) => child.fstype || child.mountpoint)
  }
  return false
}

const getDiskFSType = (disk: any) => {
  if (disk.fstype) return disk.fstype
  if (disk.children && disk.children.length > 0) {
    const childWithFs = disk.children.find((c: any) => c.fstype)
    if (childWithFs) {
      if (childWithFs.fstype === 'zfs_member') {
        return `ZFS Member (${childWithFs.label || 'pool01'})`
      }
      if (childWithFs.fstype === 'linux_raid_member') {
        return `RAID Member (${childWithFs.label || 'array'})`
      }
      return childWithFs.fstype
    }
  }
  return 'Unassigned'
}

const getDiskMountpoint = (disk: any) => {
  if (disk.mountpoint) return disk.mountpoint
  if (disk.children && disk.children.length > 0) {
    const mountedChildren = disk.children.filter((c: any) => c.mountpoint)
    if (mountedChildren.length > 0) {
      return mountedChildren.map((c: any) => c.mountpoint).join(', ')
    }
  }
  return '-'
}

// Computed unassigned disks filter
const availableDisks = computed(() => {
  return disks.value.filter(d => d.type === 'disk' && d.name !== 'sda' && !isDiskAssigned(d))
})

const fetchStorageData = async () => {
  try {
    const headers = { 'Authorization': `Bearer ${props.token}` }
    
    // Disks
    const disksRes = await fetch('/api/storage/disks', { headers })
    if (disksRes.ok) disks.value = await disksRes.json()

    // mdadm
    const mdadmRes = await fetch('/api/storage/mdadm', { headers })
    if (mdadmRes.ok) mdadmArrays.value = await mdadmRes.json()

    // zpools
    const zpoolRes = await fetch('/api/storage/zpool', { headers })
    if (zpoolRes.ok) zpools.value = await zpoolRes.json()

    // datasets
    const datasetsRes = await fetch('/api/storage/zfs/datasets', { headers })
    if (datasetsRes.ok) datasets.value = await datasetsRes.json()

    // snapshots
    const snapshotsRes = await fetch('/api/storage/zfs/snapshots', { headers })
    if (snapshotsRes.ok) snapshots.value = await snapshotsRes.json()

    // zvols
    const zvolRes = await fetch('/api/storage/zfs/zvol', { headers })
    if (zvolRes.ok) zvols.value = await zvolRes.json()

  } catch (e) {
    console.error('Failed fetching storage stats', e)
  }
}

// mdadm operations
const createMdadm = async () => {
  try {
    const url = `/api/storage/mdadm?name=${newMd.value.name}&level=${newMd.value.level}&fstype=${newMd.value.fstype}`
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(newMd.value.disks)
    })
    if (res.ok) {
      alert('RAID Array Built Successfully.')
      newMd.value = { name: '', level: 5, disks: [], fstype: 'ext4' }
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error creating array: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const destroyMdadm = async (name: string) => {
  if (!confirm(`Are you sure you want to stop and delete array /dev/${name}?`)) return
  try {
    const res = await fetch(`/api/storage/mdadm/${name}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      fetchStorageData()
    }
  } catch (e) {
    alert(e)
  }
}

// ZFS operations
const createZpool = async () => {
  try {
    const url = `/api/storage/zpool?name=${newPool.value.name}&layout=${newPool.value.layout}`
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(newPool.value.disks)
    })
    if (res.ok) {
      alert('ZFS Pool Constructed.')
      newPool.value = { name: '', layout: 'striped', disks: [] }
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const destroyZpool = async (name: string) => {
  if (!confirm(`Permanently destroy pool "${name}" and all ZFS data?`)) return
  try {
    const res = await fetch(`/api/storage/zpool/${name}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) fetchStorageData()
  } catch (e) {
    alert(e)
  }
}

const createDataset = async () => {
  try {
    const res = await fetch(`/api/storage/zfs/datasets?pool=${newDataset.value.pool}&name=${newDataset.value.name}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      newDataset.value = { pool: '', name: '' }
      fetchStorageData()
    }
  } catch (e) {
    alert(e)
  }
}

const destroyDataset = async (name: string) => {
  if (!confirm(`Are you sure you want to destroy ZFS dataset "${name}"?`)) return
  try {
    const res = await fetch(`/api/storage/zfs/datasets/${name}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) fetchStorageData()
  } catch (e) {
    alert(e)
  }
}

const createSnapshot = async () => {
  try {
    const res = await fetch(`/api/storage/zfs/snapshots?dataset=${newSnap.value.dataset}&name=${newSnap.value.name}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      newSnap.value = { dataset: '', name: '' }
      fetchStorageData()
    }
  } catch (e) {
    alert(e)
  }
}

const rollbackSnapshot = async (fullName: string) => {
  if (!confirm(`Rollback data to snap "${fullName}"? This action will destroy subsequent writes.`)) return
  try {
    const res = await fetch(`/api/storage/zfs/snapshots/rollback?snapshot=${fullName}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) alert('Rollback completed successfully.')
  } catch (e) {
    alert(e)
  }
}

const destroySnapshot = async (fullName: string) => {
  if (!confirm(`Delete snapshot "${fullName}"?`)) return
  try {
    const res = await fetch(`/api/storage/zfs/snapshots/${fullName}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Delete failed: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

// Zvol Operations
const createZvol = async () => {
  try {
    const res = await fetch('/api/storage/zfs/zvol', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(newZvol.value)
    })
    if (res.ok) {
      newZvol.value = { pool: newZvol.value.pool, name: '', size_gb: 10 }
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const destroyZvol = async (pool: string, name: string) => {
  if (!confirm(`Are you sure you want to destroy Zvol "${pool}/${name}"? All data will be lost.`)) return
  try {
    const res = await fetch(`/api/storage/zfs/zvol/${pool}/${name}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) fetchStorageData()
  } catch (e) {
    alert(e)
  }
}

// LUKS Triggers
const promptEncrypt = (name: string) => {
  encryptTarget.value = name
  luksPassword.value = ''
}

const promptUnlock = (name: string) => {
  unlockTarget.value = name
  luksPassword.value = ''
  luksMapper.value = 'secure_vol0'
}

const encryptDisk = async () => {
  try {
    const res = await fetch('/api/storage/luks/encrypt', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({
        path: encryptTarget.value.startsWith('zvol/') || encryptTarget.value.startsWith('md') 
          ? `/dev/${encryptTarget.value}` 
          : `/dev/${encryptTarget.value}`,
        passphrase: luksPassword.value
      })
    })
    if (res.ok) {
      alert('LUKS Volume Formatted.')
      encryptTarget.value = null
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('LUKS format error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const unlockDisk = async () => {
  try {
    const res = await fetch('/api/storage/luks/open', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({
        path: `/dev/${unlockTarget.value}`,
        name: luksMapper.value,
        passphrase: luksPassword.value
      })
    })
    if (res.ok) {
      alert('Volume unlocked successfully.')
      unlockTarget.value = null
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Unlock error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const lockDisk = async (mapperPath: string) => {
  const name = mapperPath.split('/').pop()
  if (!name) return
  if (!confirm(`Relock encrypted volume mapper target "${name}"?`)) return
  try {
    const res = await fetch('/api/storage/luks/close', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({ name })
    })
    if (res.ok) {
      fetchStorageData()
    }
  } catch (e) {
    alert(e)
  }
}

// Modal state variables
const selectedPool = ref<any>(null)
const zpoolMode = ref('add_vdev')
const vdevForm = ref({ layout: 'striped', disks: [] as string[] })
const replaceForm = ref({ oldDisk: '', newDisk: '' })
const raidzExpandForm = ref({ vdev: 'raidz1-0', newDisk: '' })

const selectedArray = ref<any>(null)
const mdadmAddDiskTarget = ref('')
const mdadmNewDevicesCount = ref<number | null>(null)

// Methods for pool management
const openZpoolManage = (pool: any) => {
  selectedPool.value = pool
  zpoolMode.value = 'add_vdev'
  vdevForm.value = { layout: 'striped', disks: [] }
  replaceForm.value = { oldDisk: pool.disks[0] || '', newDisk: '' }
  raidzExpandForm.value = { vdev: 'raidz1-0', newDisk: '' }
}

const submitAddVdev = async () => {
  if (vdevForm.value.disks.length === 0) return alert('Select at least one disk.')
  try {
    const res = await fetch(`/api/storage/zpool/${selectedPool.value.name}/expand-vdev?layout=${vdevForm.value.layout}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify(vdevForm.value.disks)
    })
    if (res.ok) {
      alert('VDev attached successfully.')
      selectedPool.value = null
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error adding vdev: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const submitReplaceDisk = async () => {
  if (!replaceForm.value.oldDisk || !replaceForm.value.newDisk) return alert('Select both disks.')
  try {
    const res = await fetch(`/api/storage/zpool/${selectedPool.value.name}/replace-disk?old_disk=${replaceForm.value.oldDisk}&new_disk=${replaceForm.value.newDisk}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${props.token}`
      }
    })
    if (res.ok) {
      alert('Disk replacement initiated successfully.')
      selectedPool.value = null
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error replacing disk: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const submitRaidzExpand = async () => {
  if (!raidzExpandForm.value.vdev || !raidzExpandForm.value.newDisk) return alert('Fill in all fields.')
  try {
    const res = await fetch(`/api/storage/zpool/${selectedPool.value.name}/expand-raidz?vdev=${raidzExpandForm.value.vdev}&new_disk=${raidzExpandForm.value.newDisk}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${props.token}`
      }
    })
    if (res.ok) {
      alert('RAIDZ expansion triggered successfully.')
      selectedPool.value = null
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error expanding RAIDZ: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

// Methods for mdadm management
const openMdadmManage = (array: any) => {
  selectedArray.value = array
  mdadmAddDiskTarget.value = ''
  mdadmNewDevicesCount.value = array.disks.length
}

const submitMdadmAddDisk = async () => {
  if (!mdadmAddDiskTarget.value) return alert('Select a disk to add.')
  try {
    const res = await fetch(`/api/storage/mdadm/${selectedArray.value.name}/add-disk?disk=${mdadmAddDiskTarget.value}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      alert('Disk added to array successfully.')
      selectedArray.value.disks.push(mdadmAddDiskTarget.value)
      mdadmAddDiskTarget.value = ''
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error adding disk: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const submitMdadmGrow = async () => {
  if (!mdadmNewDevicesCount.value) return alert('Specify number of active devices.')
  try {
    const res = await fetch(`/api/storage/mdadm/${selectedArray.value.name}/grow?new_num_devices=${mdadmNewDevicesCount.value}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      alert('Array grew successfully.')
      selectedArray.value = null
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error growing array: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const failMdadmDisk = async (arrayName: string, disk: string) => {
  if (!confirm(`Mark disk ${disk} as failed in array ${arrayName}?`)) return
  try {
    const res = await fetch(`/api/storage/mdadm/${arrayName}/fail-disk?disk=${disk}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      alert('Disk marked as failed.')
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

const removeMdadmDisk = async (arrayName: string, disk: string) => {
  if (!confirm(`Remove disk ${disk} from array ${arrayName}?`)) return
  try {
    const res = await fetch(`/api/storage/mdadm/${arrayName}/remove-disk?disk=${disk}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${props.token}` }
    })
    if (res.ok) {
      alert('Disk removed from array.')
      if (selectedArray.value) {
        selectedArray.value.disks = selectedArray.value.disks.filter((d: string) => d !== disk)
      }
      fetchStorageData()
    } else {
      const data = await res.json()
      alert('Error: ' + data.detail)
    }
  } catch (e) {
    alert(e)
  }
}

// ZFS Holds
const applyHold = async (snapName: string) => {
  const tag = prompt("Enter hold tag name (e.g. ransomware-lock, daily-hold):", "ransomware-lock")
  if (!tag) return
  try {
    const res = await fetch('/api/storage/zfs/snapshots/hold', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({ snapshot: snapName, tag })
    })
    if (res.ok) {
      fetchStorageData()
    }
  } catch (e) {
    alert(e)
  }
}

const releaseHold = async (snapName: string) => {
  const tag = prompt("Enter hold tag to release:", "ransomware-lock")
  if (!tag) return
  try {
    const res = await fetch('/api/storage/zfs/snapshots/release', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${props.token}`
      },
      body: JSON.stringify({ snapshot: snapName, tag })
    })
    if (res.ok) {
      fetchStorageData()
    }
  } catch (e) {
    alert(e)
  }
}

let pollInterval: any = null

onMounted(() => {
  fetchStorageData()
  pollInterval = setInterval(fetchStorageData, 5000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>
