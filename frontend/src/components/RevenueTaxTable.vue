<script setup lang="ts">
import type { RevenueTaxResult, RevenueTaxRow } from '../types'
import { formatMoney } from '../formatting'

defineProps<{ result: RevenueTaxResult }>()
type AmountField = keyof Omit<RevenueTaxRow, 'year' | 'phase' | 'steam_volume'>
const columns: Array<{ name: AmountField; label: string }> = [
  { name: 'steam_revenue_excluding_tax', label: '不含税蒸汽收入' },
  { name: 'carbon_revenue_excluding_tax', label: '不含税碳收益' },
  { name: 'revenue_excluding_tax', label: '不含税收益合计' },
  { name: 'output_vat', label: '销项税' },
  { name: 'electricity_cost', label: '不含税电费' },
  { name: 'input_vat', label: '进项税' },
  { name: 'vat_before_credit', label: '应缴增值税（抵扣前）' },
  { name: 'opening_construction_credit', label: '建设期抵扣年初余额' },
  { name: 'construction_credit_used', label: '当年建设期抵扣额' },
  { name: 'construction_credit_balance', label: '建设期抵扣剩余额度' },
  { name: 'vat_paid', label: '实缴增值税' },
  { name: 'surcharge', label: '城建及教育附加' },
]
const summaries = [
  { name: 'revenue_excluding_tax_total', label: '不含税收益合计' },
  { name: 'construction_credit_used_total', label: '建设期抵扣合计' },
  { name: 'final_construction_credit_balance', label: '建设期抵扣剩余额度' },
  { name: 'vat_paid_total', label: '实缴增值税合计' },
  { name: 'surcharge_total', label: '城建及教育附加合计' },
]
</script>

<template>
  <section class="not-prose mt-4 min-w-0 rounded-2xl border border-blue-100 bg-white text-sm">
    <div class="border-b border-blue-100 px-4 py-3">
      <h3 class="font-semibold text-slate-900">收入及税金表</h3>
      <p class="mt-1 text-xs text-slate-500">金额单位：{{ result.unit }} · 蒸汽量：万吨 · 运营期 {{ result.inputs.operating_years }} 年 · 原始数据已保存至当前方案</p>
      <p class="mt-1 text-xs text-slate-500">销项税率 {{ formatMoney(result.inputs.output_vat_rate * 100) }}% · 购电进项税率 {{ formatMoney(result.inputs.input_vat_rate * 100) }}% · 附加税系数 {{ formatMoney(result.inputs.surcharge_rate * 100) }}%</p>
    </div>
    <dl class="grid grid-cols-2 gap-3 p-4 lg:grid-cols-3">
      <div v-for="field in summaries" :key="field.name" class="rounded-xl bg-blue-50/70 px-3 py-2">
        <dt class="text-xs text-slate-500">{{ field.label }}</dt>
        <dd class="mt-1 font-semibold tabular-nums text-slate-900">{{ formatMoney(result.summary[field.name]!) }}</dd>
      </div>
    </dl>
    <div class="relative max-h-[32rem] overflow-auto" tabindex="0" aria-label="收入及税金年度明细，可横向滚动">
      <table class="w-full whitespace-nowrap text-xs tabular-nums">
        <caption class="sr-only">收入及税金表，按年计算购电进项税、建设期抵扣、实缴增值税和附加税</caption>
        <thead class="sticky top-0 bg-slate-100 text-slate-600"><tr>
          <th scope="col" class="px-3 py-3 text-left">年份</th>
          <th scope="col" class="px-3 py-3 text-left">阶段</th>
          <th scope="col" class="px-3 py-3 text-right">蒸汽量（万吨）</th>
          <th v-for="column in columns" :key="column.name" scope="col" class="px-3 py-3 text-right">{{ column.label }}</th>
        </tr></thead>
        <tbody class="divide-y divide-slate-100"><tr v-for="row in result.schedule" :key="row.year" class="even:bg-slate-50 hover:bg-blue-50">
          <th scope="row" class="px-3 py-2.5 text-left font-normal">{{ row.year }}</th>
          <td class="px-3 py-2.5">{{ row.phase }}</td>
          <td class="px-3 py-2.5 text-right">{{ row.steam_volume == null ? '—' : formatMoney(row.steam_volume) }}</td>
          <td v-for="column in columns" :key="column.name" class="px-3 py-2.5 text-right">{{ row.phase === '运营期' ? formatMoney(row[column.name]) : '—' }}</td>
        </tr></tbody>
      </table>
    </div>
  </section>
</template>
