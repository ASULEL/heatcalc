<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EconomicScheme } from '../types'
import LoanScheduleTable from './LoanScheduleTable.vue'
import CostScheduleTable from './CostScheduleTable.vue'
import RevenueTaxTable from './RevenueTaxTable.vue'
import IncomeTaxTable from './IncomeTaxTable.vue'
import CashFlowTable from './CashFlowTable.vue'
import { formatMoney } from '../formatting'

const props = defineProps<{
  schemes: EconomicScheme[]
  loading: boolean
  exportingSchemeId?: string | null
  exportError?: { schemeId: string; message: string } | null
}>()
defineEmits<{ start: []; resume: [schemeId: string]; export: [schemeId: string] }>()
const selectedId = ref<string | null>(null) // 当前查看的方案
const selected = computed(() => props.schemes.find(scheme => scheme.id === selectedId.value))
const stageLabels = {
  loan: '待填写借款参数', cost: '待填写成本参数', revenue_tax: '待填写收入及税金参数',
  income_tax: '待填写所得税参数', cash_flow: '待填写现金流量参数', completed: '已完成',
}
</script>

<template>
  <main class="min-w-0 flex-1 overflow-auto bg-[#f4f7fb] p-5 sm:p-8">
    <div class="mx-auto max-w-5xl space-y-6">
      <div>
        <h2 class="text-xl font-semibold text-slate-900">方案</h2>
        <p class="mt-2 text-sm text-slate-500">选择测算方案，按顺序完成参数填写与计算。</p>
      </div>
      <section class="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
        <h3 class="font-semibold text-slate-900">经济测算</h3>
        <p class="mt-2 text-sm text-slate-500">借款还本付息表 → 成本计算表 → 收入及税金表 → 所得税表 → 资本金/全投资现金流量表</p>
        <p class="mt-2 text-xs text-slate-500">各表共用方案数据，保留每一步的参数和原始结果。</p>
        <button type="button" :disabled="loading" class="mt-4 rounded-xl bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-40" @click="$emit('start')">新建经济测算</button>
      </section>
      <section>
        <h3 class="font-semibold text-slate-900">当前对话的方案</h3>
        <p v-if="!schemes.length" class="mt-3 text-sm text-slate-500">暂无方案，选择上方经济测算开始填写。</p>
        <div class="mt-3 grid gap-3 sm:grid-cols-2">
          <article v-for="scheme in schemes" :key="scheme.id" class="rounded-2xl border bg-white p-4" :class="selectedId === scheme.id ? 'border-blue-400' : 'border-slate-200'">
            <h4 class="font-medium text-slate-900">{{ scheme.name }}</h4>
            <p class="mt-1 text-xs text-slate-500">{{ stageLabels[scheme.stage] }}</p>
            <p v-if="scheme.loanResult" class="mt-2 text-xs text-slate-500">静态投资 {{ formatMoney(scheme.loanResult.inputs.static_investment!) }} 万元 · {{ scheme.loanResult.schedule.length }} 年</p>
            <div class="mt-3 flex gap-4 text-sm text-blue-600">
              <button v-if="scheme.loanResult" type="button" @click="selectedId = scheme.id">查看结果</button>
              <button v-if="scheme.cashFlowResult" type="button" :disabled="loading || !!exportingSchemeId" class="disabled:opacity-40" @click="$emit('export', scheme.id)">{{ exportingSchemeId === scheme.id ? '正在导出…' : '导出 Excel' }}</button>
              <button v-if="scheme.stage !== 'completed'" type="button" :disabled="loading" class="disabled:opacity-40" @click="$emit('resume', scheme.id)">继续填写</button>
            </div>
            <p v-if="exportError?.schemeId === scheme.id" role="alert" class="mt-3 text-sm text-red-600">{{ exportError.message }}</p>
          </article>
        </div>
      </section>
      <section v-if="selected" :key="selected.id">
        <h3 class="font-semibold text-slate-900">{{ selected.name }}</h3>
        <LoanScheduleTable v-if="selected.loanResult" :result="selected.loanResult" />
        <CostScheduleTable v-if="selected.costResult" :result="selected.costResult" />
        <RevenueTaxTable v-if="selected.revenueTaxResult" :result="selected.revenueTaxResult" />
        <IncomeTaxTable v-if="selected.incomeTaxResult" :result="selected.incomeTaxResult" />
        <template v-if="selected.cashFlowResult">
          <CashFlowTable :result="selected.cashFlowResult.capital" :equity-ratio="selected.cashFlowResult.inputs.equity_ratio" />
          <CashFlowTable :result="selected.cashFlowResult.total_investment" />
        </template>
      </section>
    </div>
  </main>
</template>
