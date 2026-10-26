<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const text = ref('')

function submit() {
  if (props.disabled) return
  const value = text.value.trim()
  if (!value) return
  emit('send', value)
  text.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  // Enter 发送，Shift+Enter 换行
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="bg-transparent px-4 pb-5 pt-3 sm:px-8">
    <div
      class="mx-auto flex max-w-4xl items-end gap-3 rounded-3xl border border-blue-100 bg-white px-4 py-3 shadow-xl shadow-blue-100/50 focus-within:border-blue-300 focus-within:ring-4 focus-within:ring-blue-50"
    >
      <textarea
        v-model="text"
        rows="2"
        placeholder="描述你的工况参数，或直接提问..."
        class="max-h-32 min-h-12 flex-1 resize-none bg-transparent px-2 py-1.5 text-[15px] leading-6 outline-none placeholder:text-slate-400"
        @keydown="handleKeydown"
      />
      <button
        type="button"
        class="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-lg text-white shadow-md shadow-blue-200 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="disabled || !text.trim()"
        @click="submit"
      >
        ↗
      </button>
    </div>
    <p class="mt-2 text-center text-xs text-slate-400">
      Enter 发送，Shift + Enter 换行
    </p>
  </div>
</template>
