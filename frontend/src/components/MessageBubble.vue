<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { marked } from 'marked'
import type { ChatMessage, CostScheduleInputs, ParameterField } from '../types'
import LoanScheduleTable from './LoanScheduleTable.vue'
import CostScheduleForm from './CostScheduleForm.vue'
import CostScheduleTable from './CostScheduleTable.vue'

const props = defineProps<{
  message: ChatMessage
  loading?: boolean
}>()

const emit = defineEmits<{
  submitParameters: [fields: ParameterField[], values: Record<string, string>, messageId: string]
  submitCostParameters: [inputs: CostScheduleInputs, messageId: string]
}>()

const parameterValues = ref<Record<string, string>>({})
const defaultFieldNames = ref(new Set<string>())
const costFields = computed(() => (props.message.parameterForm || []).map(field => ({
  ...field,
  value: props.message.submittedCostInputs?.[field.name as keyof CostScheduleInputs] ?? field.value,
}))) // 提交后保留本次输入，重新打开历史消息也可回看

watch(
  () => props.message.parameterForm,
  (fields) => {
    parameterValues.value = Object.fromEntries(
      (fields || []).map((field) => [field.name, props.message.submittedValues?.[field.name] ?? (field.value == null ? '' : String(field.value))]),
    )
    defaultFieldNames.value = new Set(
      (fields || []).filter((field) => field.isDefault).map((field) => field.name),
    )
  },
  { immediate: true },
)

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

const parameterGroups = computed(() => {
  const groups = new Map<string, { name: string; advanced: boolean; fields: ParameterField[] }>()

  for (const field of props.message.parameterForm || []) {
    const group = groups.get(field.group) || {
      name: field.group,
      advanced: field.advanced,
      fields: [],
    }
    group.fields.push(field)
    groups.set(field.group, group)
  }

  return [...groups.values()]
})

function submitParameters() {
  if (!props.message.parameterForm) return
  emit('submitParameters', props.message.parameterForm, parameterValues.value, props.message.id)
}

function markCustomValue(name: string) {
  defaultFieldNames.value.delete(name)
}

function selectDefaultValue(name: string, event: FocusEvent) {
  if (!defaultFieldNames.value.has(name)) return
  const target = event.target as HTMLInputElement | HTMLSelectElement
  if (target instanceof HTMLInputElement) target.select()
}
</script>

<template>
  <div class="flex w-full items-start gap-3 px-4 py-4 sm:px-6">
    <!-- 头像：assistant在左，user在右 -->
    <div
      v-if="message.role === 'assistant'"
      class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-blue-600 text-sm font-semibold text-white shadow-md shadow-blue-100"
    >
      ✦
    </div>

    <div
      class="min-w-0 rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed [overflow-wrap:anywhere]"
      :class="
        message.role === 'user'
          ? 'ml-auto w-fit max-w-2xl rounded-br-md bg-blue-600 text-white whitespace-pre-wrap shadow-lg shadow-blue-100'
          : 'mr-auto flex-1 max-w-4xl border border-blue-100 bg-white text-slate-900 shadow-sm prose prose-sm prose-slate'
      "
    >
      <!-- 用户消息：纯文本 -->
      <template v-if="message.role === 'user'">
        {{ message.content }}
      </template>
      <!-- AI消息：渲染Markdown -->
      <div v-else v-html="renderedContent" />

      <p v-if="message.economicStep || message.calculationResults?.length" class="mt-3 text-xs text-blue-600">
        {{ message.schemeName || '经济测算' }} · {{ message.economicStep?.step === 'loan' ? '第1步：借款参数' : message.economicStep?.step === 'cost' ? '第2步：成本参数' : '测算结果' }}
        <span v-if="message.submitted" class="ml-2 text-slate-400">已提交，以下为当时的参数</span>
      </p>
      <template v-for="(result, index) in message.calculationResults" :key="index">
        <LoanScheduleTable v-if="result.step === 'loan'" :result="result.loan_result" />
        <CostScheduleTable v-else-if="result.cost_result" :result="result.cost_result" />
      </template>

      <CostScheduleForm
        v-if="message.economicStep?.step === 'cost' && message.economicStep.loanResult"
        :fields="costFields"
        :loan-result="message.economicStep.loanResult"
        :disabled="message.submitted || loading"
        @submit="(inputs) => emit('submitCostParameters', inputs, message.id)"
      />

      <form
        v-else-if="message.parameterForm?.length"
        class="mt-4 space-y-3"
        @submit.prevent="submitParameters"
      >
        <fieldset :disabled="message.submitted || loading" class="space-y-3">
          <p v-if="message.economicStep?.step === 'loan'" class="text-xs text-slate-500">
            金额单位为万元；利率和比例使用小数，例如 0.03 表示 3%，0.8 表示 80%。预填值可修改，提交后直接计算。
          </p>
          <details
            v-for="group in parameterGroups"
            :key="group.name"
            :open="!group.advanced"
            class="overflow-hidden rounded-2xl border border-blue-100 bg-white shadow-sm"
          >
            <summary class="cursor-pointer list-none border-b border-blue-50 bg-blue-50/70 px-4 py-3 font-medium text-slate-800">
              <span class="mr-2 text-blue-600">▸</span>{{ group.name }}
            </summary>
            <div class="grid gap-3 p-4 sm:grid-cols-2">
              <label v-for="field in group.fields" :key="field.name" class="block">
                <span class="mb-1.5 flex items-center gap-2 text-sm text-neutral-700">
                  <span>{{ field.label }}</span>
                  <span v-if="defaultFieldNames.has(field.name)" class="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-600">Excel示例</span>
                </span>
                <span class="flex items-center gap-2">
                  <select
                    v-if="field.inputType === 'select'"
                    v-model="parameterValues[field.name]"
                    :aria-label="field.label"
                    class="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    @change="markCustomValue(field.name)"
                  >
                    <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                  <input
                    v-else
                    v-model="parameterValues[field.name]"
                    :aria-label="field.label"
                    class="min-w-0 flex-1 rounded-xl border border-slate-200 px-3 py-2 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    :placeholder="field.required ? '请输入' : '可选'"
                    @focus="selectDefaultValue(field.name, $event)"
                    @input="markCustomValue(field.name)"
                  />
                  <span class="w-20 shrink-0 text-xs text-neutral-500">{{ field.unit }}</span>
                </span>
              </label>
            </div>
          </details>
          <div class="flex justify-end">
            <button
              type="submit"
              class="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-blue-100 hover:bg-blue-700"
            >
              提交参数
            </button>
          </div>
        </fieldset>
      </form>
    </div>

    <!-- 用户头像在右侧 -->
    <div
      v-if="message.role === 'user'"
        class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-slate-800 text-sm font-semibold text-white"
    >
      U
    </div>
  </div>
</template>
