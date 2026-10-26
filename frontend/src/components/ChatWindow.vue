<script setup lang="ts">
import { nextTick, watch, ref } from 'vue'
import type { ChatMessage, ParameterField } from '../types'
import MessageBubble from './MessageBubble.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps<{
  title: string
  messages: ChatMessage[]
  loading: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  submitParameters: [fields: ParameterField[], values: Record<string, string>]
}>()

const scrollArea = ref<HTMLDivElement | null>(null)
const showToolList = ref(false)
const homeText = ref('')

const quickPrompts = [
  { icon: '⚡', title: '电加热购电成本', text: '根据蒸汽需求计算电加热器购电成本' },
  { icon: '♨️', title: '热泵购电成本', text: '根据蒸汽需求计算热泵购电成本' },
  { icon: '☀️', title: '风光制汽流量', text: '根据光伏或风电功率计算蒸汽流量' },
  { icon: '◈', title: '热泵 COP', text: '根据热泵循环参数计算 COP' },
]

const availableTools = [
  {
    icon: '⚡',
    title: '电加热器购电成本',
    description: '根据蒸汽需求计算电加热器输入功率和购电成本',
    prompt: '根据蒸汽需求计算电加热器购电成本',
  },
  {
    icon: '↺',
    title: '电加热器蒸汽流量',
    description: '根据指定购电成本反算可供给的蒸汽流量',
    prompt: '根据购电成本反算电加热器蒸汽流量',
  },
  {
    icon: '◈',
    title: '熔盐储量',
    description: '根据充热功率和储热时长计算所需熔盐质量',
    prompt: '计算熔盐储量',
  },
  {
    icon: '♨️',
    title: '热泵购电成本',
    description: '根据蒸汽需求和热泵循环参数计算购电成本',
    prompt: '根据蒸汽需求计算热泵购电成本',
  },
  {
    icon: '↺',
    title: '热泵蒸汽流量',
    description: '根据指定购电成本反算热泵可供给的蒸汽流量',
    prompt: '根据购电成本反算热泵蒸汽流量',
  },
  {
    icon: '◈',
    title: '热泵 COP',
    description: '根据热泵循环参数计算系统供热 COP',
    prompt: '根据热泵循环参数计算 COP',
  },
  {
    icon: '☀️',
    title: '风光制汽流量',
    description: '根据风电或光伏功率计算电加热器蒸汽流量',
    prompt: '根据光伏或风电功率计算蒸汽流量',
  },
]

function choosePrompt(prompt: string) {
  showToolList.value = false
  emit('send', prompt)
}

function submitHome() {
  if (props.loading) return
  const value = homeText.value.trim()
  if (!value) return
  emit('send', value)
  homeText.value = ''
}

function handleHomeKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submitHome()
  }
}

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    scrollArea.value?.scrollTo({ top: scrollArea.value.scrollHeight, behavior: 'smooth' })
  },
)
</script>

<template>
  <main class="flex h-full min-w-0 flex-1 flex-col bg-[#f4f7fb]">
    <div ref="scrollArea" class="min-h-0 flex-1 overflow-y-auto">
      <div v-if="messages.length === 0" class="flex min-h-full items-center justify-center px-6 py-12">
        <div class="w-full max-w-5xl">
          <div class="mx-auto max-w-2xl text-center">
            <span class="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-4 py-1.5 text-xs font-semibold text-blue-600">✦ AI 工业热源助手</span>
            <h2 class="mt-5 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">今天想完成什么热源计算？</h2>
            <p class="mt-3 text-sm leading-6 text-slate-500">描述你的工况、设备参数或预算，助手会自动整理需要填写的参数。</p>
          </div>

          <div class="mt-10 rounded-3xl border border-blue-100 bg-white p-5 shadow-xl shadow-blue-100/50 sm:p-7">
            <div class="flex min-h-24 items-end gap-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 px-4 py-3 transition focus-within:border-blue-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-blue-50">
              <textarea
                v-model="homeText"
                rows="3"
                :disabled="loading"
                placeholder="例如：根据 8 MW 光伏功率计算每天可以产生多少蒸汽"
                class="min-h-20 flex-1 resize-none bg-transparent px-1 py-1 text-sm leading-6 text-slate-700 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed"
                @keydown="handleHomeKeydown"
              />
              <button
                type="button"
                :disabled="loading || !homeText.trim()"
                aria-label="发送计算需求"
                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-lg text-white shadow-md shadow-blue-200 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
                @click="submitHome"
              >
                ↗
              </button>
            </div>
            <div class="mt-5 flex flex-wrap gap-2">
              <button v-for="prompt in quickPrompts" :key="prompt.title" type="button" class="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700" @click="choosePrompt(prompt.text)">
                <span class="mr-1.5">{{ prompt.icon }}</span>{{ prompt.title }}
              </button>
            </div>
          </div>

          <div class="mt-6 grid gap-3 sm:grid-cols-3">
            <button
              type="button"
              class="rounded-2xl border border-blue-100 bg-white px-5 py-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md"
              :aria-expanded="showToolList"
              aria-controls="available-tools"
              @click="showToolList = !showToolList"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-2xl font-bold text-blue-600">{{ availableTools.length }}</p>
                  <p class="mt-1 text-xs text-slate-500">可调用计算工具</p>
                </div>
                <span class="mt-1 rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-600">{{ showToolList ? '收起' : '查看' }}</span>
              </div>
            </button>
            <div class="rounded-2xl border border-white bg-white px-5 py-4 shadow-sm">
              <p class="text-2xl font-bold text-blue-600">kW / MW</p>
              <p class="mt-1 text-xs text-slate-500">统一功率单位体系</p>
            </div>
            <div class="rounded-2xl border border-white bg-white px-5 py-4 shadow-sm">
              <p class="text-2xl font-bold text-blue-600">COP</p>
              <p class="mt-1 text-xs text-slate-500">支持热泵循环分析</p>
            </div>
          </div>

          <div v-if="showToolList" id="available-tools" class="mt-4 rounded-3xl border border-blue-100 bg-white p-5 shadow-lg shadow-blue-100/40 sm:p-6">
            <div class="flex items-center justify-between gap-3">
              <div>
                <h3 class="text-base font-semibold text-slate-900">全部计算工具</h3>
                <p class="mt-1 text-xs text-slate-500">选择一个工具，开始填写对应的计算参数。</p>
              </div>
              <span class="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-600">{{ availableTools.length }} 项</span>
            </div>
            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              <button
                v-for="tool in availableTools"
                :key="tool.title"
                type="button"
                class="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50/60 p-4 text-left transition hover:border-blue-200 hover:bg-blue-50/70"
                @click="choosePrompt(tool.prompt)"
              >
                <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-lg shadow-sm">{{ tool.icon }}</span>
                <span class="min-w-0">
                  <span class="block text-sm font-semibold text-slate-800">{{ tool.title }}</span>
                  <span class="mt-1 block text-xs leading-5 text-slate-500">{{ tool.description }}</span>
                </span>
                <span class="ml-auto mt-1 text-slate-300">→</span>
              </button>
            </div>
          </div>

          <div class="mt-6">
            <div class="mb-3 flex items-end justify-between gap-3">
              <div>
                <h3 class="text-base font-semibold text-slate-900">常用工具</h3>
                <p class="mt-1 text-xs text-slate-500">快速开始常见的热源计算任务</p>
              </div>
              <span class="text-xs text-slate-400">常用场景</span>
            </div>
            <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <button v-for="prompt in quickPrompts" :key="`${prompt.title}-card`" type="button" class="group rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md" @click="choosePrompt(prompt.text)">
              <div class="flex items-center justify-between">
                <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-lg">{{ prompt.icon }}</span>
                <span class="text-slate-300 transition group-hover:text-blue-500">→</span>
              </div>
              <p class="mt-4 text-sm font-semibold text-slate-800">{{ prompt.title }}</p>
              <p class="mt-1 text-xs leading-5 text-slate-500">{{ prompt.text }}</p>
            </button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="mx-auto w-full max-w-5xl py-5 sm:py-8">
        <MessageBubble
          v-for="m in messages"
          :key="m.id"
          :message="m"
          @submit-parameters="(fields, values) => emit('submitParameters', fields, values)"
        />

        <div v-if="loading" class="mx-4 my-5 rounded-2xl border border-blue-100 bg-white px-5 py-4 shadow-sm sm:mx-6" role="status" aria-label="正在计算">
          <div class="flex items-center gap-3 text-sm text-slate-500">
            <span class="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-600">✦</span>
            <span>正在整理工况并计算，请稍候</span>
            <span class="ml-auto flex gap-1"><i class="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400" /><i class="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400 [animation-delay:0.15s]" /><i class="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400 [animation-delay:0.3s]" /></span>
          </div>
        </div>
      </div>
    </div>

    <ChatInput :disabled="loading" @send="(text) => emit('send', text)" />
  </main>
</template>
