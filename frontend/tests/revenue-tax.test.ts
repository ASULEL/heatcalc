import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createSSRApp, effectScope, ref } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createServer } from 'vite'
import { useRevenueTaxInputs } from '../src/composables/useRevenueTaxInputs.ts'
import { costResult } from './cost-fixtures.ts'
import { bankResult } from './fixtures.ts'
import { economicRevenueTaxResult, revenueTaxFields, revenueTaxInputs } from './revenue-tax-fixtures.ts'

test('税金输入将百分比转换为小数，空蒸汽量保持缺失，不改变购电来源', () => {
  const scope = effectScope()
  try {
    scope.run(() => {
      const state = useRevenueTaxInputs(ref(costResult), ref(revenueTaxFields))
      state.values.value.output_vat_rate = '6'
      state.values.value.income_amount_basis = 'tax_exclusive'
      state.annualRows.value[2]!.steam_revenue_by_year = '12345.123456789'
      const result = state.buildInputs()
      assert.equal(result.output_vat_rate, 0.06)
      assert.equal(result.steam_vat_rate, 0.09)
      assert.equal(result.income_amount_basis, 'tax_exclusive')
      assert.deepEqual(result.steam_revenue_by_year, [0, 0, 12345.123456789])
      assert.deepEqual(result.carbon_revenue_by_year, [0, 0, 0])
      assert.deepEqual(result.steam_volume_by_year, [null, null, null])
      assert.equal(state.annualRows.value[2]!.electricityCost, costResult.schedule[2]!.electricity_cost)
      assert.equal(costResult.inputs.total_electricity_by_year[2], 17651.8226)
    })
  } finally { scope.stop() }
})

test('批量收入只覆盖选定运营年，建设期与运营结束年份不生成收入', () => {
  const scope = effectScope()
  try {
    scope.run(() => {
      const cost = {
        ...costResult,
        schedule: Array.from({ length: 6 }, (_, index) => ({
          ...costResult.schedule[2]!, year: index + 1, phase: index < 2 ? '建设期' : '运营期',
        })),
      }
      const state = useRevenueTaxInputs(ref(cost), ref(revenueTaxFields))
      state.values.value.operating_years = '2'
      state.annualRows.value[2]!.steam_revenue_by_year = 600
      state.annualRows.value[2]!.steam_volume_by_year = 12.3456789
      state.applyToOperatingYears(state.annualRows.value[2]!)
      assert.deepEqual(state.buildInputs().steam_revenue_by_year, [0, 0, 600, 600, 0, 0])
      assert.deepEqual(state.buildInputs().steam_volume_by_year, [null, null, 12.3456789, 12.3456789, null, null])
      assert.deepEqual([...state.activeYears.value], [3, 4])
    })
  } finally { scope.stop() }
})

test('结果表显示收入分项、实缴税、抵扣余额与四位小数', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const html = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'tax-result', role: 'assistant', content: '计算完成', calculationResults: [economicRevenueTaxResult],
    } }))
    for (const label of ['收入及税金表', '不含税蒸汽收入', '不含税碳收益', '建设期抵扣剩余额度', '实缴增值税', '城建及教育附加']) {
      assert.ok(html.includes(label), label)
    }
    assert.match(html, />25\.6800</)
    assert.match(html, />2\.5680</)
    assert.match(html, />34\.3200</)
    assert.match(html, />—</)
    assert.doesNotMatch(html, /<h3[^>]*>成本计算表/)
  } finally { await server.close() }
})

test('历史税金表单回填已提交税率和收入，保留零值并设为只读', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const html = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'tax-history', role: 'assistant', content: '填写税金参数', parameterForm: revenueTaxFields,
      economicStep: { schemeId: 'scheme-1', step: 'revenue_tax', loanResult: bankResult, costResult },
      submitted: true, submittedRevenueTaxInputs: revenueTaxInputs,
    } }))
    assert.match(html, /第3步：收入及税金参数/)
    assert.match(html, /<fieldset disabled/)
    assert.match(html, /value="600"/)
    assert.match(html, /value="0\.1"/)
    assert.match(html, /value="10"/)
    assert.match(html, /value="0"/)
    assert.match(html, /同年成本表的不含税电费/)
    assert.match(html, /生成收入及税金表/)
    assert.doesNotMatch(html, /\[object Object\]/)
  } finally { await server.close() }
})
