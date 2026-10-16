<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Conversation, ChatMessage } from './types'
import Sidebar from './components/Sidebar.vue'
import ChatWindow from './components/ChatWindow.vue'

const conversations = ref<Conversation[]>([])
const currentId = ref<string | null>(null)
const loading = ref(false)

const current = computed(() => conversations.value.find((c) => c.id === currentId.value))

function createConversation() {
  const id = Date.now().toString()
  conversations.value.push({ id, title: '新对话', messages: [] })
  currentId.value = id
}

function selectConversation(id: string) {
  currentId.value = id
}

async function sendMessage(text: string) {
  if (!current.value) {
    createConversation()
  }
  if (!current.value) return

  const userMessage: ChatMessage = {
    id: Date.now().toString(),
    role: 'user',
    content: text,
  }
  current.value.messages.push(userMessage)

  // 用第一条用户消息作为对话标题
  if (current.value.messages.filter((m) => m.role === 'user').length === 1) {
    current.value.title = text.slice(0, 30) + (text.length > 30 ? '...' : '')
  }

  loading.value = true

  try {
    const res = await fetch('http://127.0.0.1:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        history: current.value.messages.slice(0, -1), // 传历史消息
      }),
    })
    const data = await res.json()
    const assistantMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content: data.response,
    }

    current.value.messages.push(assistantMessage)
  } catch (err) {
    console.error('发送消息失败:', err)
    const errorMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '抱歉，请求失败，请稍后重试。',
    }
    current.value.messages.push(errorMessage)
  } finally {
    loading.value = false
  }
}

// 初始化一个默认对话
createConversation()
</script>

<template>
  <div class="flex h-full">
    <Sidebar
      :conversations="conversations"
      :current-id="currentId"
      @create="createConversation"
      @select="selectConversation"
    />
    <ChatWindow :messages="current?.messages || []" :loading="loading" @send="sendMessage" />
  </div>
</template>
