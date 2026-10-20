<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { ChatMessage } from '../types'

const props = defineProps<{
  message: ChatMessage
}>()

// 配置 marked 选项
marked.setOptions({
  breaks: true, // 支持换行
  gfm: true, // GitHub Flavored Markdown
})

const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    return marked(props.message.content)
  }
  return props.message.content
})
</script>

<template>
  <div class="flex w-full items-start gap-3 px-4 py-4 sm:px-6">
    <!-- 头像：assistant在左，user在右 -->
    <div
      v-if="message.role === 'assistant'"
      class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-emerald-600 text-sm font-semibold text-white"
    >
      AI
    </div>

    <div
      class="min-w-0 rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed [overflow-wrap:anywhere]"
      :class="
        message.role === 'user'
          ? 'ml-auto w-fit max-w-2xl bg-neutral-800 text-white whitespace-pre-wrap'
          : 'mr-auto flex-1 bg-neutral-100 text-neutral-900 prose prose-sm prose-neutral max-w-3xl'
      "
    >
      <!-- 用户消息：纯文本 -->
      <template v-if="message.role === 'user'">
        {{ message.content }}
      </template>
      <!-- AI消息：渲染Markdown -->
      <div v-else v-html="renderedContent" />
    </div>

    <!-- 用户头像在右侧 -->
    <div
      v-if="message.role === 'user'"
      class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-neutral-700 text-sm font-semibold text-white"
    >
      U
    </div>
  </div>
</template>
