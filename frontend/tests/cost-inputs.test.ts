import assert from 'node:assert/strict'
import { test } from 'node:test'
import { effectScope, nextTick, ref } from 'vue'
import { useCostInputs } from '../src/composables/useCostInputs.ts'
import { costFields, loanWithCalendar } from './cost-fixtures.ts'

test('成本输入沿用借款表年份，维修比例可分段，年度输入保留原始数值', () => {
  const scope = effectScope()
  try {
    scope.run(() => {
      const loan = loanWithCalendar(30, 2)
      const state = useCostInputs(ref(loan), ref(costFields))
      assert.equal(state.annualRows.value.length, 30)
      assert.deepEqual(state.periods.value, [
        { start_year: 3, end_year: 7, ratio: 0.003 },
        { start_year: 8, end_year: 12, ratio: 0.005 },
        { start_year: 13, end_year: 17, ratio: 0.007 },
        { start_year: 18, end_year: 22, ratio: 0.009 },
        { start_year: 23, end_year: 27, ratio: 0.011 },
        { start_year: 28, end_year: 30, ratio: 0.013 },
      ])
      state.annualRows.value[2]!.total_electricity_by_year = '2390.123456789'
      state.depreciationYears.value = 15
      state.periods.value[0]!.ratio = 0.004
      const inputs = state.buildInputs()
      assert.equal(state.loan.value.schedule[2]!.interest_expense, loan.schedule[2]!.interest_expense)
      assert.equal(inputs.total_electricity_by_year[2], 2390.123456789)
      assert.equal(inputs.depreciation_years, 15)
      assert.equal(inputs.maintenance_ratio_periods[0]!.ratio, 0.004)
      assert.deepEqual(inputs.water_cost_by_year, Array(30).fill(0))
      assert.deepEqual(inputs.total_electricity_by_year.slice(0, 2), [0, 0])
      assert.equal(inputs.amortization_expense_by_year.length, 30)
    })
  } finally {
    scope.stop()
  }
})

test('不同方案各自绑定借款来源，批量填写只影响本方案运营年', async () => {
  const scope = effectScope()
  try {
    const firstLoan = ref(loanWithCalendar(30, 2))
    const secondLoan = ref(loanWithCalendar(12, 4))
    const first = scope.run(() => useCostInputs(firstLoan, ref(costFields)))!
    const second = scope.run(() => useCostInputs(secondLoan, ref(costFields)))!
    second.annualRows.value[4]!.labor_cost_by_year = 300
    second.applyToOperatingYears(second.annualRows.value[4]!)
    assert.deepEqual(second.buildInputs().labor_cost_by_year, [...Array(4).fill(0), ...Array(8).fill(300)])
    assert.equal(first.buildInputs().labor_cost_by_year[2], 216)
    assert.equal(first.annualRows.value.length, 30)
    assert.equal(second.annualRows.value.length, 12)
    await nextTick()
    assert.equal(first.loan.value.inputs.schedule_years, 30)
    assert.equal(first.periods.value[0]!.start_year, 3)
    assert.equal(second.periods.value[0]!.start_year, 5)
  } finally {
    scope.stop()
  }
})

test('已知维修区间回填后可以编辑，不改变原参数数据', () => {
  const scope = effectScope()
  try {
    scope.run(() => {
      const fields = ref(costFields.map(field => field.name === 'maintenance_ratio_periods'
        ? { ...field, value: [{ start_year: 3, end_year: 30, ratio: 0.007 }] } : field))
      const state = useCostInputs(ref(loanWithCalendar(30, 2)), fields)
      state.periods.value[0]!.ratio = 0.009
      assert.deepEqual(fields.value.find(field => field.name === 'maintenance_ratio_periods')!.value, [
        { start_year: 3, end_year: 30, ratio: 0.007 },
      ])
    })
  } finally {
    scope.stop()
  }
})
