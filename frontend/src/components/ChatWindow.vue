<script setup lang="ts">
import { nextTick, watch, ref } from 'vue'
import type { ChatMessage } from '../types'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps<{
  title: string
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
  <main class="flex h-full min-w-0 flex-1 flex-col bg-white">
    <header class="shrink-0 border-b border-emerald-100 bg-linear-to-r from-emerald-50/80 via-white to-white">
      <div class="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
        <div class="flex min-w-0 items-center gap-3">
          <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-700 text-white shadow-sm">
            <svg aria-hidden="true" class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
              <path d="M6 15c-4-4 4-5 0-10M12 15c-4-4 4-5 0-10M18 15c-4-4 4-5 0-10M4 20h16" />
            </svg>
          </div>
          <div class="min-w-0">
            <h1 class="text-base font-semibold tracking-wide text-neutral-900 sm:text-lg">工业热源计算助手</h1>
            <p class="mt-1 truncate text-xs text-neutral-500" :title="title">{{ title }}</p>
          </div>
        </div>
        <ul aria-label="支持的计算类型" class="hidden shrink-0 items-center gap-2 text-xs text-emerald-800 lg:flex">
          <li v-for="label in ['电加热', '热泵', '熔盐储热']" :key="label" class="rounded-full border border-emerald-100 bg-emerald-50/70 px-3 py-1.5">
            {{ label }}
          </li>
        </ul>
      </div>
    </header>

    <div ref="scrollArea" class="min-h-0 flex-1 overflow-y-auto">
      <div v-if="messages.length === 0" class="flex min-h-full items-center justify-center px-6 py-12">
        <div class="text-center text-neutral-400">
          <p class="text-lg font-medium text-neutral-600">工业热源计算助手</p>
          <p class="mt-1 text-sm">描述蒸汽工况和设备参数，开始一次计算</p>
        </div>
      </div>

      <div v-else class="mx-auto w-full max-w-5xl py-4 sm:py-6">
        <MessageBubble v-for="m in messages" :key="m.id" :message="m" />

        <div v-if="loading" class="px-4 py-5 sm:px-6" role="status" aria-label="正在计算">
          <div class="flex items-center gap-2 text-sm text-neutral-400">
            <span class="h-2 w-2 animate-bounce rounded-full bg-neutral-400" />
            <span class="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:0.15s]" />
            <span class="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:0.3s]" />
          </div>
        </div>
      </div>
    </div>

    <ChatInput :disabled="loading" @send="(text) => emit('send', text)" />
  </main>
</template>
