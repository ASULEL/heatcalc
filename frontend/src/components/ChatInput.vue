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
  <div class="border-t border-neutral-200 bg-white px-4 py-4">
    <div
      class="mx-auto flex max-w-2xl items-end gap-2 rounded-2xl border border-neutral-300 bg-white px-3 py-2 shadow-sm focus-within:border-neutral-400"
    >
      <textarea
        v-model="text"
        rows="1"
        placeholder="描述你的工况参数，或直接提问..."
        class="flex-1 resize-none bg-transparent px-1 py-1.5 text-[15px] outline-none placeholder:text-neutral-400"
        @keydown="handleKeydown"
      />
      <button
        type="button"
        class="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-neutral-900 text-white transition hover:bg-neutral-700 disabled:opacity-40"
        :disabled="disabled || !text.trim()"
        @click="submit"
      >
        ↑
      </button>
    </div>
    <p class="mt-2 text-center text-xs text-neutral-400">
      Enter 发送，Shift + Enter 换行
    </p>
  </div>
</template>
