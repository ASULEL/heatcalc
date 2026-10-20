<script setup lang="ts">
import { useConversations } from './composables/useConversations'
import Sidebar from './components/Sidebar.vue'
import ChatWindow from './components/ChatWindow.vue'

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
