<template>
  <div class="w-full h-full bg-black/30 flex flex-col relative overflow-hidden">
    <!-- Terminal View Area -->
    <div ref="terminalContainer" class="flex-1 w-full h-full relative pointer-events-auto"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'

const props = defineProps({
  token: String
})

const terminalContainer = ref<HTMLElement | null>(null)
let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let socket: WebSocket | null = null
let resizeObserver: ResizeObserver | null = null

const initTerminal = () => {
  if (!terminalContainer.value) return

  // Create Xterm
  term = new Terminal({
    cursorBlink: true,
    fontFamily: 'Consolas, "Courier New", Courier, monospace',
    fontSize: 13,
    theme: {
      background: 'transparent',
      foreground: '#cbd5e1',
      cursor: '#3b82f6',
      selectionBackground: 'rgba(59, 130, 246, 0.3)',
      black: '#1e293b',
      red: '#ef4444',
      green: '#10b981',
      yellow: '#f59e0b',
      blue: '#3b82f6',
      magenta: '#8b5cf6',
      cyan: '#06b6d4',
      white: '#f8fafc'
    },
    allowProposedApi: true
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalContainer.value)
  fitAddon.fit()

  // Connect websocket
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/ws/terminal`
  socket = new WebSocket(wsUrl)

  socket.onopen = () => {
    // Send resize info
    if (term) {
      sendResize(term.cols, term.rows)
    }
  }

  socket.onmessage = (event) => {
    if (term) {
      term.write(event.data)
    }
  }

  socket.onclose = () => {
    if (term) {
      term.write('\r\n\x1b[31m[Session terminated. Reconnecting...]\x1b[0m\r\n')
    }
  }

  // Handle keys inputs
  term.onData((data) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'data', data }))
    }
  })

  // Watch container resize
  resizeObserver = new ResizeObserver(() => {
    if (fitAddon && term) {
      try {
        fitAddon.fit()
        sendResize(term.cols, term.rows)
      } catch (e) {}
    }
  })
  resizeObserver.observe(terminalContainer.value)
}

const sendResize = (cols: number, rows: number) => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'resize', cols, rows }))
  }
}

onMounted(() => {
  // Give container time to settle in layout
  setTimeout(initTerminal, 100)
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  if (socket) {
    socket.close()
  }
  if (term) {
    term.dispose()
  }
})
</script>
