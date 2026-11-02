<script setup lang="ts">
import { toRef } from 'vue'
import type { CostScheduleInputs, LoanCalculationResult, ParameterField } from '../types'
import { annualCostFields, useCostInputs } from '../composables/useCostInputs'
import { formatMoney } from '../formatting'

const props = defineProps<{ fields: ParameterField[]; loanResult: LoanCalculationResult; disabled?: boolean }>()
const emit = defineEmits<{ submit: [inputs: CostScheduleInputs] }>()
const {
  loan, values, coreFields, coefficientFields,
  periods, annualRows, fieldsByName, addPeriod, applyToOperatingYears, buildInputs,
} = useCostInputs(toRef(props, 'loanResult'), toRef(props, 'fields'))

function selectOnFocus(event: FocusEvent) {
  const target = event.target
  if (target instanceof HTMLInputElement) target.select()
}
</script>

<template>
  <form class="not-prose mt-4 space-y-4 text-sm" @submit.prevent="emit('submit', buildInputs())">
    <fieldset :disabled="disabled" class="space-y-4">
      <div class="rounded-2xl border border-blue-100 bg-blue-50/50 p-4">
        <h3 class="font-semibold text-slate-900">成本计算参数</h3>
        <p class="mt-1 text-xs leading-5 text-slate-500">金额单位为万元。默认值为当前 Excel 案例，预填值可修改，聚焦后可直接输入替换；年份和长期借款利息直接关联本方案借款表。</p>
        <p class="mt-3 text-xs text-slate-600">
          引用本方案借款表 · 静态投资 {{ formatMoney(loanResult.inputs.static_investment!) }} 万元 · {{ loanResult.schedule.length }} 年
        </p>
        <div class="mt-3 grid gap-3 sm:grid-cols-2">
          <label v-for="field in coreFields" :key="field.name">
            <span>{{ field.label }}（{{ field.unit }}）</span>
            <input
              v-model="values[field.name]"
              type="number"
              :step="field.name.endsWith('_years') ? 1 : 'any'"
              required
              :aria-label="field.label"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
              @focus="selectOnFocus"
            />
          </label>
        </div>
      </div>

      <fieldset class="rounded-2xl border border-slate-200 p-4">
        <legend class="px-1 font-semibold text-slate-800">计价系数</legend>
        <p class="mb-3 text-xs leading-5 text-slate-500">
          计价基数 = 静态投资 × 可折旧比例 − 静态投资 × 建设期抵扣比例 + 建设期利息合计。
          保险费 = 基数 × 保险费率 ÷ 保险费除税系数；维修费 = 基数 × 比例 ÷ 含税换算系数。
        </p>
        <div class="grid gap-3 sm:grid-cols-2">
          <label v-for="field in coefficientFields" :key="field.name" class="block text-xs text-slate-700">
            {{ field.label }}（{{ field.unit }}）
            <input
              v-model="values[field.name]"
              type="number"
              step="any"
              required
              :aria-label="field.label"
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              @focus="selectOnFocus"
            />
          </label>
        </div>
      </fieldset>

      <fieldset v-if="loan" class="rounded-2xl border border-slate-200 p-4">
        <legend class="px-1 font-semibold text-slate-800">维修费比例区间</legend>
        <p class="mb-3 text-xs text-slate-500">使用项目年份，区间覆盖的年份按对应比例计算，未覆盖年份为 0。比例用小数填写，例如 0.003 表示 0.3%。</p>
        <div v-for="(period, index) in periods" :key="index" class="mb-2 grid grid-cols-[1fr_1fr_1fr_auto] gap-2">
          <label class="min-w-0 text-xs">开始年份<input v-model.number="period.start_year" type="number" step="1" required class="mt-1 w-full rounded-lg border border-slate-200 p-2" /></label>
          <label class="min-w-0 text-xs">结束年份<input v-model.number="period.end_year" type="number" step="1" required class="mt-1 w-full rounded-lg border border-slate-200 p-2" /></label>
          <label class="min-w-0 text-xs">比例<input v-model.number="period.ratio" type="number" step="any" required class="mt-1 w-full rounded-lg border border-slate-200 p-2" /></label>
          <button type="button" class="self-end rounded-lg px-2 py-2 text-xs text-slate-500 hover:bg-slate-100" @click="periods.splice(index, 1)">删除</button>
        </div>
        <button type="button" class="mt-1 text-xs font-medium text-blue-600" @click="addPeriod">＋ 添加区间</button>
      </fieldset>

      <div v-if="loan" class="overflow-hidden rounded-2xl border border-slate-200">
        <div class="border-b border-slate-100 px-4 py-3">
          <h4 class="font-semibold text-slate-800">各年费用输入</h4>
          <p class="mt-1 text-xs leading-5 text-slate-500">电费填写含税总额。水费、人工费、摊销费、流动资金借款利息按 Excel 预填 0；建设期和运营年数以外的年份为 0。</p>
          <p class="mt-1 text-xs text-slate-500">可逐年修改，也可将某一行应用到全部运营年。</p>
        </div>
        <div class="max-h-96 overflow-auto">
          <table class="w-full whitespace-nowrap text-xs">
            <thead class="sticky top-0 bg-slate-100 text-slate-600">
              <tr>
                <th scope="col" class="px-3 py-2 text-left">年份</th>
                <th v-for="name in annualCostFields" :key="name" scope="col" class="px-2 py-2 text-left">{{ fieldsByName.get(name)?.label }}</th>
                <th scope="col" class="px-2 py-2">批量填写</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="row in annualRows" :key="row.year" :class="row.phase === '建设期' ? 'bg-slate-50 text-slate-400' : ''">
                <th scope="row" class="px-3 py-2 text-left font-normal">{{ row.year }}</th>
                <td v-for="name in annualCostFields" :key="name" class="px-2 py-2">
                  <input v-model="row[name]" type="number" step="any" :required="row.phase === '运营期'" :disabled="row.phase === '建设期'" :aria-label="`第${row.year}年${fieldsByName.get(name)?.label}`" class="w-28 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-right tabular-nums disabled:bg-slate-50" @focus="selectOnFocus" />
                </td>
                <td class="px-2 py-2"><button v-if="row.phase === '运营期'" type="button" class="text-blue-600" @click="applyToOperatingYears(row)">应用到全部运营年</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="flex justify-end">
        <button type="submit" :disabled="!loan" class="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40">生成成本计算表</button>
      </div>
    </fieldset>
  </form>
</template>
