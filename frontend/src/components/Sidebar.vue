<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { Conversation, UserProfile } from '../types'

defineProps<{
  currentUser: UserProfile
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
  <div class="flex h-full w-64 shrink-0 flex-col border-r border-neutral-200 bg-neutral-50">
    <section aria-label="当前用户" class="flex shrink-0 items-center gap-3 border-b border-neutral-200 px-4 py-5">
      <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-800">
        <svg aria-hidden="true" class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21v-2a8 8 0 0 1 16 0v2" />
        </svg>
      </div>
      <div class="min-w-0 flex-1">
        <p class="text-xs leading-5 text-neutral-500">当前用户</p>
        <p class="mt-1 truncate text-sm font-semibold leading-6 text-neutral-900" :title="currentUser.displayName">{{ currentUser.displayName }}</p>
      </div>
    </section>

    <div class="shrink-0 border-b border-neutral-200 px-4 py-4">
      <button
        type="button"
        class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-700"
        @click="emit('create')"
      >
        + 新建对话
      </button>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto p-2">
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
