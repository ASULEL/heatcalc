<script setup lang="ts">
import { ref } from 'vue'
import { useConversations } from './composables/useConversations'
import Sidebar from './components/Sidebar.vue'
import ChatWindow from './components/ChatWindow.vue'
import type { ParameterField, UserProfile } from './types'

// 接入用户管理后，在这里替换为实际获取的用户信息。
const currentUser: UserProfile = { displayName: '默认用户' }
const isDarkMode = ref(false)

const {
  conversations,
  currentId,
  current,
  loading,
  createConversation,
  selectConversation,
  renameConversation,
  deleteConversation,
  sendMessage,
  sendParameterValues,
} = useConversations()

function submitParameters(fields: ParameterField[], values: Record<string, string>) {
  sendParameterValues(fields, values)
}

function toggleTheme() {
  isDarkMode.value = !isDarkMode.value
}
</script>

<template>
  <div :class="['flex h-full flex-col bg-[#f4f7fb] text-slate-800', { dark: isDarkMode }]">
    <header class="flex h-[68px] shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/90 px-5 backdrop-blur sm:px-8">
      <div class="flex min-w-0 items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-200">
          <svg aria-hidden="true" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 17c4-1 7-4 9-9 2 1 4 3 5 6" />
            <path d="M5 20c4-1 7-4 9-9" />
          </svg>
        </div>
        <div class="min-w-0">
          <p class="truncate text-sm font-bold tracking-wide text-slate-900">工业热源助手</p>
          <p class="truncate text-[11px] text-slate-400">Heat Source Agent</p>
        </div>
      </div>

      <nav aria-label="主导航" class="hidden items-center gap-1 rounded-full bg-slate-100 p-1 text-sm font-medium text-slate-500 md:flex">
        <button type="button" class="rounded-full bg-blue-600 px-6 py-2 text-white shadow-md shadow-blue-200">对话</button>
        <button type="button" class="rounded-full px-5 py-2 transition hover:bg-white hover:text-slate-800">方案 <span class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-orange-400 align-middle" /></button>
        <button type="button" class="rounded-full px-5 py-2 transition hover:bg-white hover:text-slate-800">档案</button>
      </nav>

      <div class="flex items-center gap-2">
        <span class="hidden items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 sm:flex">
          <span class="h-2 w-2 rounded-full bg-emerald-500" />模型服务已连接
        </span>
        <button
          type="button"
          :aria-label="isDarkMode ? '切换浅色模式' : '切换夜间模式'"
          :title="isDarkMode ? '切换浅色模式' : '切换夜间模式'"
          class="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:border-blue-200 hover:text-blue-600"
          @click="toggleTheme"
        >
          {{ isDarkMode ? '☀' : '☾' }}
        </button>
        <div class="flex h-9 w-9 items-center justify-center rounded-full bg-blue-50 text-sm font-bold text-blue-700 ring-4 ring-blue-50">
          {{ currentUser.displayName.slice(0, 1) }}
        </div>
      </div>
    </header>

    <div class="flex min-h-0 flex-1">
      <Sidebar
        :current-user="currentUser"
        :conversations="conversations"
        :current-id="currentId"
        :has-messages="Boolean(current?.messages.length)"
        @create="createConversation"
        @select="selectConversation"
        @rename="renameConversation"
        @delete="deleteConversation"
      />
      <ChatWindow
        :title="current?.title || '新对话'"
        :messages="current?.messages || []"
        :loading="loading"
        @send="sendMessage"
        @submit-parameters="submitParameters"
      />
    </div>
  </div>
</template>
