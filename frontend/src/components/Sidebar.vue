<script setup lang="ts">
import type { Conversation } from '../types'

defineProps<{
  conversations: Conversation[]
  currentId: string | null
}>()

const emit = defineEmits<{
  select: [id: string]
  create: []
}>()
</script>

<template>
  <div class="flex h-full w-64 flex-col border-r border-neutral-200 bg-neutral-50">
    <div class="border-b border-neutral-200 px-4 py-4">
      <button
        type="button"
        class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-700"
        @click="emit('create')"
      >
        + 新建对话
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-2">
      <button
        v-for="conv in conversations"
        :key="conv.id"
        type="button"
        class="mb-1 w-full rounded-lg px-3 py-2.5 text-left text-sm transition hover:bg-neutral-200"
        :class="conv.id === currentId ? 'bg-neutral-200 font-medium' : 'text-neutral-600'"
        @click="emit('select', conv.id)"
      >
        <p class="truncate">{{ conv.title || '新对话' }}</p>
      </button>
    </div>
  </div>
</template>
