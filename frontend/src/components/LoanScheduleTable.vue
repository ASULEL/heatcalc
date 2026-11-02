<script setup lang="ts">
import type { LoanCalculationResult, LoanScheduleRow } from '../types'
import { formatMoney } from '../formatting'

defineProps<{ result: LoanCalculationResult }>()

const summaryFields = [ // 汇总卡片及中文含义，金额单位由结果提供
  { name: 'loan_amount', label: '贷款总额' },
  { name: 'construction_interest_total', label: '建设期利息' },
  { name: 'annual_principal', label: '每年等额还本' },
  { name: 'total_interest', label: '全周期利息' },
]
const columns: { name: keyof LoanScheduleRow; label: string }[] = [ // 年度金额列
  { name: 'beginning_balance', label: '年初借款余额' },
  { name: 'new_borrowing', label: '当年新增贷款' },
  { name: 'principal_repayment', label: '当年偿还本金' },
  { name: 'interest_expense', label: '当年利息' },
  { name: 'capitalized_interest', label: '资本化利息' },
  { name: 'cash_interest', label: '现金支付利息' },
  { name: 'ending_balance', label: '年末借款余额' },
]

</script>

<template>
  <section class="not-prose mt-4 min-w-0 rounded-2xl border border-blue-100 bg-white text-sm">
    <div class="border-b border-blue-100 px-4 py-3">
      <h3 class="font-semibold text-slate-900">借款还本付息表</h3>
      <p class="mt-1 text-xs text-slate-500">金额单位：{{ result.unit }} · 共 {{ result.schedule.length }} 年</p>
      <p class="mt-1 text-xs text-slate-500">已保存到当前对话方案，后续可引用整列数据；刷新页面后清空。</p>
    </div>

    <dl class="grid grid-cols-2 gap-3 p-4 lg:grid-cols-4">
      <div v-for="field in summaryFields" :key="field.name" class="rounded-xl bg-blue-50/70 px-3 py-2">
        <dt class="text-xs text-slate-500">{{ field.label }}</dt>
        <dd class="mt-1 font-semibold tabular-nums text-slate-900">{{ formatMoney(result.summary[field.name]!) }}</dd>
      </div>
    </dl>

    <div class="relative max-h-[32rem] overflow-auto rounded-b-2xl" tabindex="0" aria-label="逐年还本付息明细，可横向滚动">
      <table class="w-full whitespace-nowrap text-xs tabular-nums">
        <caption class="sr-only">借款还本付息逐年明细，金额单位：{{ result.unit }}</caption>
        <thead class="sticky top-0 bg-slate-100 text-slate-600">
          <tr>
            <th scope="col" class="px-3 py-3 text-left">年份</th>
            <th scope="col" class="px-3 py-3 text-left">阶段</th>
            <th v-for="column in columns" :key="column.name" scope="col" class="px-3 py-3 text-right">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="row in result.schedule" :key="row.year" class="even:bg-slate-50 hover:bg-blue-50">
            <th scope="row" class="px-3 py-2.5 text-left font-normal">{{ row.year }}</th>
            <td class="px-3 py-2.5 text-left">{{ row.phase }}</td>
            <td v-for="column in columns" :key="column.name" class="px-3 py-2.5 text-right">{{ formatMoney(row[column.name]) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
