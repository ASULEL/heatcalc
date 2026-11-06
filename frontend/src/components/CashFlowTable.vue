<script setup lang="ts">
import type { CashFlowRow, CashFlowTableResult } from '../types'
import { formatMoney } from '../formatting'

defineProps<{ result: CashFlowTableResult; equityRatio?: number }>()
type AmountField = keyof Omit<CashFlowRow, 'year' | 'phase' | 'payback_period' | 'estimated_payback_period'>
const columns: Array<{ name: AmountField; label: string }> = [
  { name: 'revenue', label: '营业收入' },
  { name: 'residual_value', label: '回收固定资产余值' },
  { name: 'inflow', label: '现金流入合计' },
  { name: 'construction_investment', label: '建设投资' },
  { name: 'principal_repayment', label: '借款本金偿还' },
  { name: 'interest', label: '借款利息' },
  { name: 'operating_cost', label: '经营成本' },
  { name: 'surcharge', label: '附加税' },
  { name: 'income_tax', label: '所得税' },
  { name: 'net_cash_flow', label: '净现金流量' },
  { name: 'cumulative_cash_flow', label: '累计净现金流量' },
]
const summaries = [
  { name: 'net_cash_flow_total', label: '净现金流量合计' },
  { name: 'construction_investment_total', label: '建设投资合计' },
  { name: 'residual_value', label: '回收固定资产余值' },
]
const rate = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(2)}%`
const years = (value: number | null | undefined) => value == null ? '—' : value.toFixed(2)
const payback = (value: number | null | undefined) => value == null ? '运营期内未回收' : `${value.toFixed(2)} 年`
</script>

<template>
  <section class="not-prose mt-4 min-w-0 rounded-2xl border border-blue-100 bg-white text-sm">
    <div class="border-b border-blue-100 px-4 py-3">
      <h3 class="font-semibold text-slate-900">{{ result.title }}</h3>
      <p class="mt-1 text-xs text-slate-500">
        金额单位：{{ result.unit }} · 内部收益率 <span class="font-semibold text-blue-700">{{ rate(result.summary.irr as number | null) }}</span>
        · 静态投资回收期 <span class="font-semibold text-blue-700">{{ payback(result.summary.static_payback_period) }}</span>
        <span v-if="equityRatio != null"> · 资本金比例 {{ formatMoney(equityRatio * 100) }}%</span>
      </p>
      <p class="mt-1 text-xs leading-5 text-slate-500">预计回收期按当年净现金流水平估算；首次回本后停止列示。余值按期末剩余账面价值估算，只在最后运营年回收一次。</p>
    </div>
    <dl class="grid grid-cols-2 gap-3 p-4 lg:grid-cols-3">
      <div class="rounded-xl bg-blue-50/70 px-3 py-2">
        <dt class="text-xs text-slate-500">内部收益率（IRR）</dt>
        <dd class="mt-1 font-semibold tabular-nums text-slate-900">{{ rate(result.summary.irr as number | null) }}</dd>
      </div>
      <div class="rounded-xl bg-blue-50/70 px-3 py-2">
        <dt class="text-xs text-slate-500">静态投资回收期</dt>
        <dd class="mt-1 font-semibold tabular-nums text-slate-900">{{ payback(result.summary.static_payback_period) }}</dd>
      </div>
      <div v-for="field in summaries" :key="field.name" class="rounded-xl bg-blue-50/70 px-3 py-2">
        <dt class="text-xs text-slate-500">{{ field.label }}</dt>
        <dd class="mt-1 font-semibold tabular-nums text-slate-900">{{ formatMoney(result.summary[field.name] as number) }}</dd>
      </div>
    </dl>
    <div class="relative max-h-[32rem] overflow-auto" tabindex="0" :aria-label="`${result.title}年度明细，可横向滚动`">
      <table class="w-full whitespace-nowrap text-xs tabular-nums">
        <caption class="sr-only">{{ result.title }}，按年列示现金流入、建设投资、借款偿还、经营成本、税和净现金流量</caption>
        <thead class="sticky top-0 bg-slate-100 text-slate-600"><tr>
          <th scope="col" class="px-3 py-3 text-left">年份</th>
          <th scope="col" class="px-3 py-3 text-left">阶段</th>
          <th v-for="column in columns" :key="column.name" scope="col" class="px-3 py-3 text-right">{{ column.label }}</th>
          <th scope="col" class="px-3 py-3 text-right">预计静态投资回收期（年）</th>
        </tr></thead>
        <tbody class="divide-y divide-slate-100"><tr v-for="row in result.schedule" :key="row.year" class="even:bg-slate-50 hover:bg-blue-50">
          <th scope="row" class="px-3 py-2.5 text-left font-normal">{{ row.year }}</th>
          <td class="px-3 py-2.5">{{ row.phase }}</td>
          <td v-for="column in columns" :key="column.name" class="px-3 py-2.5 text-right">{{ row.phase === '运营结束' || row[column.name] == null ? '' : formatMoney(row[column.name]!) }}</td>
          <td class="px-3 py-2.5 text-right">{{ row.phase === '运营结束' || row.estimated_payback_period == null ? '' : years(row.estimated_payback_period) }}</td>
        </tr></tbody>
      </table>
    </div>
  </section>
</template>
