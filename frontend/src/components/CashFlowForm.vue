<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CashFlowInputs, ParameterField } from '../types'

const props = defineProps<{ fields: ParameterField[]; disabled?: boolean }>()
const emit = defineEmits<{ submit: [inputs: CashFlowInputs] }>()
const values = ref<Record<string, string>>({}) // 资本金比例，按百分数显示
const ratioField = computed(() => props.fields.find(field => field.name === 'equity_ratio'))

watch(() => props.fields, () => {
  values.value = Object.fromEntries(props.fields.map(field => [
    field.name, field.value == null ? '' : String(field.value),
  ]))
}, { immediate: true })

function selectOnFocus(event: FocusEvent) {
  const target = event.target
  if (target instanceof HTMLInputElement) target.select()
}

function buildInputs(): CashFlowInputs {
  const factor = ratioField.value?.toToolFactor ?? 1
  return {
    equity_ratio: Number((Number(values.value.equity_ratio) * factor).toFixed(10)),
  }
}
</script>

<template>
  <form class="not-prose mt-4 space-y-4 text-sm" @submit.prevent="emit('submit', buildInputs())">
    <fieldset :disabled="disabled" class="space-y-4">
      <div class="rounded-2xl border border-blue-100 bg-blue-50/50 p-4">
        <h3 class="font-semibold text-slate-900">现金流量参数</h3>
        <p class="mt-1 text-xs leading-5 text-slate-500">
          资本金表只投入静态投资乘资本金比例，并偿还借款本金和利息；全投资表投入静态投资的 100%，没有借款本金和利息。
          两张表都按第1年 80%、第2年 20% 分年投入，并在最后一个运营年计入回收固定资产余值。
        </p>
      </div>

      <fieldset class="rounded-2xl border border-slate-200 p-4">
        <legend class="px-1 font-semibold text-slate-800">{{ ratioField?.group }}</legend>
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="block text-xs text-slate-700">
            {{ ratioField?.label }}（{{ ratioField?.unit }}）
            <input
              v-model="values.equity_ratio"
              type="number"
              step="any"
              required
              aria-label="资本金比例"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              @focus="selectOnFocus"
            />
          </label>
        </div>
      </fieldset>

      <div class="flex justify-end">
        <button type="submit" class="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">生成现金流量表</button>
      </div>
    </fieldset>
  </form>
</template>
