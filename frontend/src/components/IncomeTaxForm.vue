<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { IncomeTaxInputs, ParameterField } from '../types'

const props = defineProps<{ fields: ParameterField[]; disabled?: boolean }>()
const emit = defineEmits<{ submit: [inputs: IncomeTaxInputs] }>()
const values = ref<Record<string, string>>({}) // 所得税率，按百分数显示
const rateField = computed(() => props.fields.find(field => field.name === 'income_tax_rate'))

watch(() => props.fields, () => {
  values.value = Object.fromEntries(props.fields.map(field => [
    field.name, field.value == null ? '' : String(field.value),
  ]))
}, { immediate: true })

function selectOnFocus(event: FocusEvent) {
  const target = event.target
  if (target instanceof HTMLInputElement) target.select()
}

function buildInputs(): IncomeTaxInputs {
  const factor = rateField.value?.toToolFactor ?? 1
  return {
    income_tax_rate: Number((Number(values.value.income_tax_rate) * factor).toFixed(10)),
  }
}
</script>

<template>
  <form class="not-prose mt-4 space-y-4 text-sm" @submit.prevent="emit('submit', buildInputs())">
    <fieldset :disabled="disabled" class="space-y-4">
      <div class="rounded-2xl border border-blue-100 bg-blue-50/50 p-4">
        <h3 class="font-semibold text-slate-900">所得税参数</h3>
        <p class="mt-1 text-xs leading-5 text-slate-500">
          营业收入取收入及税金表的不含税收入合计，附加税取实缴增值税对应的城建及教育附加，总成本取成本计算表。
          利润总额 = 营业收入 − 附加税 − 总成本；亏损年度不缴税，结转以后年度盈利时先弥补再计税。
        </p>
      </div>

      <fieldset class="rounded-2xl border border-slate-200 p-4">
        <legend class="px-1 font-semibold text-slate-800">{{ rateField?.group }}</legend>
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="block text-xs text-slate-700">
            {{ rateField?.label }}（{{ rateField?.unit }}）
            <input
              v-model="values.income_tax_rate"
              type="number"
              step="any"
              required
              aria-label="所得税率"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              @focus="selectOnFocus"
            />
          </label>
        </div>
      </fieldset>

      <div class="flex justify-end">
        <button type="submit" class="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">生成所得税表</button>
      </div>
    </fieldset>
  </form>
</template>
