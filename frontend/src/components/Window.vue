<template>
  <div 
    v-show="!minimized"
    ref="windowRef"
    :style="windowStyle"
    @mousedown="emit('focus')"
    class="absolute flex flex-col rounded-xl overflow-hidden glass-panel border border-white/10 shadow-2xl transition-shadow duration-300"
    :class="active ? 'window-active' : 'window-inactive'"
  >
    <!-- Titlebar -->
    <div 
      @mousedown="startDrag"
      class="flex items-center justify-between px-4 py-3 bg-white/5 border-b border-white/5 cursor-move select-none"
    >
      <div class="flex items-center gap-2">
        <slot name="icon"></slot>
        <span class="text-sm font-semibold tracking-wide text-slate-200">{{ title }}</span>
      </div>
      
      <!-- Window Controls -->
      <div class="flex items-center gap-2">
        <button 
          @click.stop="emit('minimize')" 
          class="w-3.5 h-3.5 rounded-full bg-yellow-500/20 border border-yellow-500/40 hover:bg-yellow-500 flex items-center justify-center group transition duration-150"
        >
          <span class="w-1 h-1 bg-yellow-900 rounded-full opacity-0 group-hover:opacity-100"></span>
        </button>
        <button 
          @click.stop="toggleMaximize" 
          class="w-3.5 h-3.5 rounded-full bg-green-500/20 border border-green-500/40 hover:bg-green-500 flex items-center justify-center group transition duration-150"
        >
          <span class="w-1 h-1 bg-green-900 rounded-full opacity-0 group-hover:opacity-100"></span>
        </button>
        <button 
          @click.stop="emit('close')" 
          class="w-3.5 h-3.5 rounded-full bg-red-500/20 border border-red-500/40 hover:bg-red-500 flex items-center justify-center group transition duration-150"
        >
          <span class="w-1.5 h-1.5 text-[8px] text-red-950 font-bold leading-none opacity-0 group-hover:opacity-100 flex items-center justify-center">&times;</span>
        </button>
      </div>
    </div>

    <!-- Content Area -->
    <div class="flex-1 overflow-auto bg-slate-950/40 relative">
      <slot></slot>
    </div>

    <!-- Resize Handle -->
    <div 
      v-if="!isMaximized"
      @mousedown.stop="startResize"
      class="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize flex items-end justify-end p-0.5 pointer-events-auto"
    >
      <svg class="w-2 h-2 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 19H5m14-6H11" />
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  title: String,
  width: { type: Number, default: 800 },
  height: { type: Number, default: 500 },
  x: { type: Number, default: 100 },
  y: { type: Number, default: 100 },
  zIndex: { type: Number, default: 10 },
  active: Boolean,
  minimized: Boolean
})

const emit = defineEmits(['close', 'minimize', 'focus', 'update:x', 'update:y', 'update:width', 'update:height'])

const windowRef = ref<HTMLElement | null>(null)
const posX = ref(props.x)
const posY = ref(props.y)
const sizeW = ref(props.width)
const sizeH = ref(props.height)
const isMaximized = ref(false)

const windowStyle = computed(() => {
  if (isMaximized.value) {
    return {
      top: '40px',
      left: '0px',
      width: '100vw',
      height: 'calc(100vh - 40px - 64px)', // Deduct global menu and taskbar
      zIndex: props.zIndex
    }
  }
  return {
    top: `${posY.value}px`,
    left: `${posX.value}px`,
    width: `${sizeW.value}px`,
    height: `${sizeH.value}px`,
    zIndex: props.zIndex
  }
})

// Toggle Maximize
const toggleMaximize = () => {
  isMaximized.value = !isMaximized.value
}

// Drag functionality
let startMouseX = 0
let startMouseY = 0
let startPosX = 0
let startPosY = 0

const startDrag = (e: MouseEvent) => {
  if (isMaximized.value) return
  emit('focus')
  
  startMouseX = e.clientX
  startMouseY = e.clientY
  startPosX = posX.value
  startPosY = posY.value
  
  document.addEventListener('mousemove', dragHandler)
  document.addEventListener('mouseup', stopDragHandler)
}

const dragHandler = (e: MouseEvent) => {
  const dx = e.clientX - startMouseX
  const dy = e.clientY - startMouseY
  
  // Boundary constraints (allow partially dragging offscreen, but not fully)
  const newX = Math.max(-sizeW.value + 100, Math.min(window.innerWidth - 100, startPosX + dx))
  const newY = Math.max(40, Math.min(window.innerHeight - 100, startPosY + dy)) // Menu is at top (40px)
  
  posX.value = newX
  posY.value = newY
  
  emit('update:x', newX)
  emit('update:y', newY)
}

const stopDragHandler = () => {
  document.removeEventListener('mousemove', dragHandler)
  document.removeEventListener('mouseup', stopDragHandler)
}

// Resize functionality
let startSizeW = 0
let startSizeH = 0

const startResize = (e: MouseEvent) => {
  emit('focus')
  startMouseX = e.clientX
  startMouseY = e.clientY
  startSizeW = sizeW.value
  startSizeH = sizeH.value
  
  document.addEventListener('mousemove', resizeHandler)
  document.addEventListener('mouseup', stopResizeHandler)
}

const resizeHandler = (e: MouseEvent) => {
  const dx = e.clientX - startMouseX
  const dy = e.clientY - startMouseY
  
  const newW = Math.max(400, startSizeW + dx)
  const newH = Math.max(300, startSizeH + dy)
  
  sizeW.value = newW
  sizeH.value = newH
  
  emit('update:width', newW)
  emit('update:height', newH)
}

const stopResizeHandler = () => {
  document.removeEventListener('mousemove', resizeHandler)
  document.removeEventListener('mouseup', stopResizeHandler)
}

onMounted(() => {
  // Center window on creation
  posX.value = Math.max(20, (window.innerWidth - sizeW.value) / 2 + (props.zIndex % 10) * 15)
  posY.value = Math.max(60, (window.innerHeight - sizeH.value - 100) / 2 + (props.zIndex % 10) * 15)
})
</script>
