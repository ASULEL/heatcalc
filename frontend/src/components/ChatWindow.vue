<script setup lang="ts">
import { nextTick, watch, ref } from 'vue'
import type { ChatMessage } from '../types'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps<{
  messages: ChatMessage[]
  loading: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const scrollArea = ref<HTMLDivElement | null>(null)

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    scrollArea.value?.scrollTo({ top: scrollArea.value.scrollHeight, behavior: 'smooth' })
  },
)
</script>

<template>
  <div class="flex h-full flex-1 flex-col bg-white">
    <div ref="scrollArea" class="flex-1 overflow-y-auto">
      <div v-if="messages.length === 0" class="flex h-full items-center justify-center">
        <div class="text-center text-neutral-400">
          <p class="text-lg font-medium text-neutral-600">工业热源计算助手</p>
          <p class="mt-1 text-sm">描述蒸汽工况和设备参数，开始一次计算</p>
        </div>
      </div>

      <MessageBubble v-for="m in messages" :key="m.id" :message="m" />

      <div v-if="loading" class="px-4 py-5">
        <div class="flex items-center gap-2 text-sm text-neutral-400">
          <span class="h-2 w-2 animate-bounce rounded-full bg-neutral-400" />
          <span class="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:0.15s]" />
          <span class="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:0.3s]" />
        </div>
      </div>
    </div>

    <ChatInput @send="(text) => emit('send', text)" />
  </div>
</template>
