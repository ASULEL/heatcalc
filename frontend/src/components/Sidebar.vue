<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { Conversation } from '../types'

defineProps<{
  conversations: Conversation[]
  currentId: string | null
}>()

const emit = defineEmits<{
  select: [id: string]
  create: []
  rename: [id: string, title: string]
  delete: [id: string]
}>()

const editingId = ref<string | null>(null)
const titleDraft = ref('')
const titleInputs = ref<HTMLInputElement[]>([])

async function startRenaming(conversation: Conversation) {
  editingId.value = conversation.id
  titleDraft.value = conversation.title
  await nextTick()
  titleInputs.value[0]?.focus()
  titleInputs.value[0]?.select()
}

function finishRenaming(id: string) {
  if (editingId.value !== id) return
  editingId.value = null
  emit('rename', id, titleDraft.value)
}
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
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="mb-1 flex items-center rounded-lg text-sm transition hover:bg-neutral-200"
        :class="conv.id === currentId ? 'bg-neutral-200 font-medium' : 'text-neutral-600'"
      >
        <form
          v-if="editingId === conv.id"
          class="min-w-0 flex-1 p-2"
          @submit.prevent="finishRenaming(conv.id)"
        >
          <input
            ref="titleInputs"
            v-model="titleDraft"
            type="text"
            aria-label="对话名称"
            class="w-full rounded border border-neutral-400 bg-white px-1 py-0.5 text-sm outline-none focus:border-neutral-600"
            @blur="finishRenaming(conv.id)"
            @keydown.esc.prevent="editingId = null"
          />
        </form>
        <button
          v-else
          type="button"
          class="min-w-0 flex-1 px-3 py-2.5 text-left"
          @click="emit('select', conv.id)"
        >
          <p class="truncate">{{ conv.title || '新对话' }}</p>
        </button>
        <button
          v-if="editingId !== conv.id"
          type="button"
          class="shrink-0 rounded px-2 py-1 text-xs text-neutral-500 transition hover:bg-neutral-300 hover:text-neutral-900"
          :aria-label="`重命名对话：${conv.title || '新对话'}`"
          title="重命名对话"
          @click="startRenaming(conv)"
        >
          命名
        </button>
        <button
          type="button"
          class="mr-2 shrink-0 rounded px-2 py-1 text-xs text-neutral-500 transition hover:bg-red-50 hover:text-red-600"
          :aria-label="`删除对话：${conv.title || '新对话'}`"
          title="删除对话"
          @click="emit('delete', conv.id)"
        >
          删除
        </button>
      </div>
    </div>
  </div>
</template>
