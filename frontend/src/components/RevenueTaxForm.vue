<script setup lang="ts">
import { computed, toRef } from 'vue'
import type { CostCalculationResult, LoanCalculationResult, ParameterField, RevenueTaxInputs } from '../types'
import { revenueTaxAnnualFields, useRevenueTaxInputs } from '../composables/useRevenueTaxInputs'
import { formatMoney } from '../formatting'

const props = defineProps<{
  fields: ParameterField[]; loanResult: LoanCalculationResult; costResult: CostCalculationResult; disabled?: boolean
}>()
const emit = defineEmits<{ submit: [inputs: RevenueTaxInputs] }>()
const {
  values, annualRows, scalarFields, fieldsByName, availableYears, activeYears, applyToOperatingYears, buildInputs,
} = useRevenueTaxInputs(toRef(props, 'costResult'), toRef(props, 'fields'))
const initialCredit = computed(() => props.loanResult.summary.static_investment! * Number(values.value.construction_credit_ratio) * 0.01)
const groups = computed(() => [...new Set(scalarFields.value.map(field => field.group))])

function selectOnFocus(event: FocusEvent) {
  const target = event.target
  if (target instanceof HTMLInputElement) target.select()
}
</script>

<template>
  <form class="not-prose mt-4 space-y-4 text-sm" @submit.prevent="emit('submit', buildInputs())">
    <fieldset :disabled="disabled" class="space-y-4">
      <div class="rounded-2xl border border-blue-100 bg-blue-50/50 p-4">
        <h3 class="font-semibold text-slate-900">收入及税金参数</h3>
        <p class="mt-1 text-xs leading-5 text-slate-600">销售蒸汽并计入碳收益，购电进项税引用同年成本表的不含税电费。金额单位为万元，蒸汽量为万吨。</p>
        <p class="mt-2 text-xs text-slate-600">引用本方案借款表及成本表 · 静态投资 {{ formatMoney(loanResult.summary.static_investment!) }} 万元 · 初始建设期抵扣额度 {{ formatMoney(initialCredit) }} 万元</p>
      </div>

      <fieldset v-for="group in groups" :key="group" class="rounded-2xl border border-slate-200 p-4">
        <legend class="px-1 font-semibold text-slate-800">{{ group }}</legend>
        <div class="grid gap-3 sm:grid-cols-2">
          <label v-for="field in scalarFields.filter(item => item.group === group)" :key="field.name" class="block text-xs text-slate-700">
            {{ field.label }}（{{ field.unit }}）
            <select v-if="field.inputType === 'select'" v-model="values[field.name]" :aria-label="field.label" required class="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
              <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
            <input v-else v-model="values[field.name]" type="number" :aria-label="field.label" required :min="field.name === 'operating_years' ? 1 : 0" :max="field.name === 'operating_years' ? availableYears : 100" :step="field.name === 'operating_years' ? 1 : 'any'" class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm" @focus="selectOnFocus" />
          </label>
        </div>
      </fieldset>
      <p class="px-1 text-xs leading-5 text-slate-500">税率预填 Excel 示例，可修改。含税收入先分别除税；不含税收入直接相加。销项税对合计不含税收入统一计税；附加税以实缴增值税为基数。建设期额度按余额逐年抵扣。</p>

      <div class="overflow-hidden rounded-2xl border border-slate-200">
        <div class="border-b border-slate-100 px-4 py-3">
          <h4 class="font-semibold text-slate-800">各年收入输入</h4>
          <p class="mt-1 text-xs text-slate-500">蒸汽收入与碳收益使用上方选择的同一金额口径。蒸汽量可留空；没有碳收益时填写0。</p>
        </div>
        <div class="max-h-96 overflow-auto">
          <table class="w-full whitespace-nowrap text-xs">
            <thead class="sticky top-0 bg-slate-100 text-slate-600"><tr>
              <th scope="col" class="px-3 py-2 text-left">年份</th>
              <th scope="col" class="px-3 py-2 text-left">阶段</th>
              <th v-for="name in revenueTaxAnnualFields" :key="name" scope="col" class="px-3 py-2 text-left">{{ fieldsByName.get(name)?.label }}（{{ fieldsByName.get(name)?.unit }}）</th>
              <th scope="col" class="px-3 py-2 text-right">引用不含税电费</th>
              <th scope="col" class="px-3 py-2">批量填写</th>
            </tr></thead>
            <tbody class="divide-y divide-slate-100"><tr v-for="row in annualRows" :key="row.year" :class="!activeYears.has(row.year) ? 'bg-slate-50 text-slate-400' : ''">
              <th scope="row" class="px-3 py-2 text-left font-normal">{{ row.year }}</th>
              <td class="px-3 py-2">{{ row.phase === '建设期' ? '建设期' : activeYears.has(row.year) ? '运营期' : '运营结束' }}</td>
              <td v-for="name in revenueTaxAnnualFields" :key="name" class="px-2 py-2">
                <input v-if="activeYears.has(row.year)" v-model="row[name]" type="number" min="0" step="any" :required="name !== 'steam_volume_by_year'" :aria-label="`第${row.year}年${fieldsByName.get(name)?.label}`" class="w-32 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-right tabular-nums" @focus="selectOnFocus" />
                <span v-else class="block px-2 text-right">—</span>
              </td>
              <td class="px-3 py-2 text-right tabular-nums">{{ activeYears.has(row.year) ? formatMoney(row.electricityCost) : '—' }}</td>
              <td class="px-2 py-2"><button v-if="activeYears.has(row.year)" type="button" class="text-blue-600" @click="applyToOperatingYears(row)">应用到全部运营年</button></td>
            </tr></tbody>
          </table>
        </div>
      </div>
      <div class="flex justify-end"><button type="submit" class="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">生成收入及税金表</button></div>
    </fieldset>
  </form>
</template>
