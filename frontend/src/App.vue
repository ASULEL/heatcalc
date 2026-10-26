<script setup lang="ts">
import { useConversations } from './composables/useConversations'
import Sidebar from './components/Sidebar.vue'
import ChatWindow from './components/ChatWindow.vue'
import type { UserProfile } from './types'

// 接入用户管理后，在这里替换为实际获取的用户信息。
const currentUser: UserProfile = { displayName: '默认用户' }

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
} = useConversations()
</script>

<template>
  <div class="flex h-full">
    <Sidebar
      :current-user="currentUser"
      :conversations="conversations"
      :current-id="currentId"
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
    />
  </div>
</template>
