<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { Conversation, UserProfile } from '../types'

defineProps<{
  currentUser: UserProfile
  conversations: Conversation[]
  currentId: string | null
  hasMessages: boolean
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
  <aside class="flex h-full w-[248px] shrink-0 flex-col border-r border-slate-200 bg-[#f8fafc]">
    <div class="border-b border-slate-200/80 px-4 py-4">
      <button
        type="button"
        class="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-200 transition hover:bg-blue-700"
        @click="emit('create')"
      >
        <span class="text-lg leading-none">+</span> 新建对话
      </button>
    </div>

    <div class="border-b border-slate-200/80 px-4 py-4">
      <p class="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">当前计算</p>
      <div class="rounded-2xl border border-blue-100 bg-white p-3 shadow-sm">
        <div class="flex items-start gap-3">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-lg">⚙️</div>
          <div class="min-w-0">
            <p class="truncate text-sm font-semibold text-slate-800">{{ hasMessages ? '方案计算中' : '准备开始计算' }}</p>
            <p class="mt-1 truncate text-xs text-slate-500">{{ hasMessages ? '参数将由助手逐步收集' : '描述你的热源计算目标' }}</p>
          </div>
          <span class="ml-auto mt-1 h-2 w-2 shrink-0 rounded-full bg-emerald-400" />
        </div>
        <div class="mt-3 rounded-lg bg-slate-50 px-2.5 py-2 text-xs text-slate-500">
          电加热 · 热泵 · 风光制汽
        </div>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-3 py-4">
      <div class="mb-3 flex items-center justify-between px-1">
        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">历史对话</p>
        <span class="text-xs text-slate-400">{{ conversations.length }}</span>
      </div>

      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="group mb-2 flex items-center rounded-xl border text-sm transition"
        :class="conv.id === currentId ? 'border-blue-100 bg-white text-slate-800 shadow-sm' : 'border-transparent text-slate-500 hover:border-slate-200 hover:bg-white'"
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
            class="w-full rounded-lg border border-blue-300 bg-white px-2 py-1.5 text-sm outline-none focus:border-blue-500"
            @blur="finishRenaming(conv.id)"
            @keydown.esc.prevent="editingId = null"
          />
        </form>
        <button
          v-else
          type="button"
          class="min-w-0 flex-1 px-3 py-3 text-left"
          @click="emit('select', conv.id)"
        >
          <span class="flex items-center gap-2">
            <span class="h-1.5 w-1.5 shrink-0 rounded-full" :class="conv.id === currentId ? 'bg-blue-500' : 'bg-slate-300'" />
            <span class="truncate">{{ conv.title || '新对话' }}</span>
          </span>
        </button>
        <button
          v-if="editingId !== conv.id"
          type="button"
          class="hidden shrink-0 rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-blue-50 hover:text-blue-600 group-hover:block"
          :aria-label="`重命名对话：${conv.title || '新对话'}`"
          title="重命名对话"
          @click="startRenaming(conv)"
        >
          ⋯
        </button>
        <button
          type="button"
          class="mr-2 hidden shrink-0 rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-red-50 hover:text-red-600 group-hover:block"
          :aria-label="`删除对话：${conv.title || '新对话'}`"
          title="删除对话"
          @click="emit('delete', conv.id)"
        >
          ×
        </button>
      </div>
    </div>

    <section aria-label="当前用户" class="border-t border-slate-200/80 p-4">
      <div class="flex items-center gap-3 rounded-2xl bg-white p-3 shadow-sm">
        <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-50 text-sm font-bold text-blue-700">{{ currentUser.displayName.slice(0, 1) }}</div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-semibold text-slate-800" :title="currentUser.displayName">{{ currentUser.displayName }}</p>
          <p class="mt-0.5 text-xs text-slate-400">本地工作区</p>
        </div>
        <span class="h-2 w-2 rounded-full bg-emerald-400" />
      </div>
    </section>
  </aside>
</template>
