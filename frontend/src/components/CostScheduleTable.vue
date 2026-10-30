<script setup lang="ts">
import type { CostCalculationResult, CostScheduleRow } from '../types'
import { formatMoney } from '../formatting'

defineProps<{ result: CostCalculationResult }>()

type CostAmountField = keyof Omit<CostScheduleRow, 'year' | 'phase' | 'maintenance_ratio'>
const groups: { label: string; columns: { name: CostAmountField; label: string }[] }[] = [ // Excel 分组表头
  { label: '经营成本', columns: [
    { name: 'electricity_cost', label: '电费' },
    { name: 'water_cost', label: '水费' },
    { name: 'labor_cost', label: '人工费' },
    { name: 'insurance_cost', label: '保险费' },
    { name: 'maintenance_cost', label: '维修费' },
  ] },
  { label: '折旧摊销', columns: [
    { name: 'depreciation_cost', label: '折旧费' },
    { name: 'amortization_expense', label: '摊销费' },
  ] },
  { label: '财务成本', columns: [
    { name: 'long_term_loan_interest', label: '长期借款利息' },
    { name: 'working_capital_loan_interest', label: '流动资金借款利息' },
  ] },
]
const columns = groups.flatMap(group => group.columns) // 逐项费用列
const summaryFields = [ // 全周期成本汇总
  { name: 'operating_cost_total', label: '经营成本合计' },
  { name: 'depreciation_amortization_total', label: '折旧摊销合计' },
  { name: 'financial_cost_total', label: '财务成本合计' },
  { name: 'total_cost', label: '总成本合计' },
]
</script>

<template>
  <section class="not-prose mt-4 min-w-0 overflow-hidden rounded-2xl border border-blue-100 bg-white text-sm">
    <div class="border-b border-blue-100 px-4 py-3">
      <h3 class="font-semibold text-slate-900">成本计算表</h3>
      <p class="mt-1 text-xs text-slate-500">金额单位：{{ result.unit }} · 年份与引用的借款表一致 · 折旧年限 {{ result.inputs.depreciation_years }} 年</p>
      <p class="mt-1 text-xs text-slate-500">原始数据已保存到当前对话方案，后续可引用各费用整列数据；刷新后清空。</p>
    </div>
    <dl class="grid grid-cols-2 gap-3 p-4 lg:grid-cols-4">
      <div v-for="field in summaryFields" :key="field.name" class="rounded-xl bg-blue-50/70 px-3 py-2">
        <dt class="text-xs text-slate-500">{{ field.label }}</dt>
        <dd class="mt-1 font-semibold tabular-nums text-slate-900">{{ formatMoney(result.summary[field.name]!) }}</dd>
      </div>
    </dl>
    <div class="relative max-h-[32rem] overflow-auto" tabindex="0" aria-label="成本计算年度明细，可横向滚动">
      <table class="w-full whitespace-nowrap text-xs tabular-nums">
        <caption class="sr-only">成本计算表，经营成本、折旧摊销和财务成本，金额单位：{{ result.unit }}</caption>
        <thead class="sticky top-0 bg-slate-100 text-slate-600">
          <tr>
            <th rowspan="2" scope="col" class="px-3 py-3 text-left">年份</th>
            <th rowspan="2" scope="col" class="px-3 py-3 text-right">维修费比例</th>
            <th v-for="group in groups" :key="group.label" :colspan="group.columns.length" scope="colgroup" class="border-l border-slate-200 px-3 py-2 text-center">{{ group.label }}</th>
            <th rowspan="2" scope="col" class="px-3 py-3 text-right">总成本</th>
          </tr>
          <tr><th v-for="column in columns" :key="column.name" scope="col" class="px-3 py-2 text-right">{{ column.label }}</th></tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="row in result.schedule" :key="row.year" class="even:bg-slate-50 hover:bg-blue-50">
            <th scope="row" class="px-3 py-2.5 text-left font-normal">{{ row.year }}</th>
            <td class="px-3 py-2.5 text-right">{{ row.phase === '建设期' ? '—' : row.maintenance_ratio.toFixed(3) }}</td>
            <td v-for="column in columns" :key="column.name" class="px-3 py-2.5 text-right">{{ row.phase === '建设期' ? '—' : formatMoney(row[column.name]) }}</td>
            <td class="px-3 py-2.5 text-right font-semibold">{{ row.phase === '建设期' ? '—' : formatMoney(row.total_cost) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
