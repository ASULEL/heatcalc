<script setup lang="ts">
import type { IncomeTaxResult, IncomeTaxRow } from '../types'
import { formatMoney } from '../formatting'

defineProps<{ result: IncomeTaxResult }>()
type AmountField = keyof Omit<IncomeTaxRow, 'year' | 'phase'>
const columns: Array<{ name: AmountField; label: string }> = [
  { name: 'revenue', label: '营业收入' },
  { name: 'surcharge', label: '附加税' },
  { name: 'total_cost', label: '总成本' },
  { name: 'total_profit', label: '利润总额' },
  { name: 'current_year_loss', label: '本年亏损' },
  { name: 'carryforward_loss', label: '本年累计亏损' },
  { name: 'loss_offset', label: '弥补亏损' },
  { name: 'taxable_income', label: '应纳税所得额' },
  { name: 'income_tax', label: '所得税' },
  { name: 'net_profit', label: '净利润' },
]
const summaries = [
  { name: 'revenue_total', label: '营业收入合计' },
  { name: 'total_cost_total', label: '总成本合计' },
  { name: 'total_profit', label: '利润总额合计' },
  { name: 'income_tax_total', label: '所得税合计' },
  { name: 'net_profit_total', label: '净利润合计' },
  { name: 'final_carryforward_loss', label: '期末累计亏损' },
]
</script>

<template>
  <section class="not-prose mt-4 min-w-0 rounded-2xl border border-blue-100 bg-white text-sm">
    <div class="border-b border-blue-100 px-4 py-3">
      <h3 class="font-semibold text-slate-900">所得税计算表</h3>
      <p class="mt-1 text-xs text-slate-500">金额单位：{{ result.unit }} · 所得税率 {{ formatMoney(result.inputs.income_tax_rate * 100) }}% · 原始数据已保存至当前方案</p>
      <p class="mt-1 text-xs text-slate-500">亏损年度不缴税，累计亏损结转到以后年度，盈利时先弥补再计税；当前不设结转年限。</p>
    </div>
    <dl class="grid grid-cols-2 gap-3 p-4 lg:grid-cols-3">
      <div v-for="field in summaries" :key="field.name" class="rounded-xl bg-blue-50/70 px-3 py-2">
        <dt class="text-xs text-slate-500">{{ field.label }}</dt>
        <dd class="mt-1 font-semibold tabular-nums text-slate-900">{{ formatMoney(result.summary[field.name]!) }}</dd>
      </div>
    </dl>
    <div class="relative max-h-[32rem] overflow-auto" tabindex="0" aria-label="所得税年度明细，可横向滚动">
      <table class="w-full whitespace-nowrap text-xs tabular-nums">
        <caption class="sr-only">所得税计算表，按年列示营业收入、附加税、总成本、利润总额、亏损弥补、所得税和净利润</caption>
        <thead class="sticky top-0 bg-slate-100 text-slate-600"><tr>
          <th scope="col" class="px-3 py-3 text-left">年份</th>
          <th scope="col" class="px-3 py-3 text-left">阶段</th>
          <th v-for="column in columns" :key="column.name" scope="col" class="px-3 py-3 text-right">{{ column.label }}</th>
        </tr></thead>
        <tbody class="divide-y divide-slate-100"><tr v-for="row in result.schedule" :key="row.year" class="even:bg-slate-50 hover:bg-blue-50">
          <th scope="row" class="px-3 py-2.5 text-left font-normal">{{ row.year }}</th>
          <td class="px-3 py-2.5">{{ row.phase }}</td>
          <td v-for="column in columns" :key="column.name" class="px-3 py-2.5 text-right">{{ formatMoney(row[column.name]) }}</td>
        </tr></tbody>
      </table>
    </div>
  </section>
</template>
