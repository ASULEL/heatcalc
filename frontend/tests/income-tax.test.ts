import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createServer } from 'vite'
import { bankResult } from './fixtures.ts'
import { costResult } from './cost-fixtures.ts'
import { revenueTaxResult } from './revenue-tax-fixtures.ts'
import { economicIncomeTaxResult, incomeTaxFields, incomeTaxInputs, incomeTaxResult } from './income-tax-fixtures.ts'

test('所得税表单预填25%，历史提交只读', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const form = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'income-form', role: 'assistant', content: '请填写所得税参数。', parameterForm: incomeTaxFields,
      economicStep: {
        schemeId: 'scheme-1', step: 'income_tax', loanResult: bankResult,
        costResult, revenueTaxResult,
      },
    } }))
    assert.match(form, /所得税参数/)
    assert.match(form, /所得税率/)
    assert.match(form, /value="25"/)
    assert.match(form, /生成所得税表/)

    const history = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'income-history', role: 'assistant', content: '请填写所得税参数。', parameterForm: incomeTaxFields,
      economicStep: { schemeId: 'scheme-1', step: 'income_tax', loanResult: bankResult, costResult, revenueTaxResult },
      submitted: true, submittedIncomeTaxInputs: incomeTaxInputs,
    } }))
    assert.match(history, /已提交，以下为当时的参数/)
    assert.match(history, /<fieldset disabled/)
    assert.match(history, /value="25"/)
  } finally {
    await server.close()
  }
})

test('所得税表显示年度明细与汇总，结果消息不重复显示收入税金表', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: IncomeTaxTable } = await server.ssrLoadModule('/src/components/IncomeTaxTable.vue')
    const table = await renderToString(createSSRApp(IncomeTaxTable, { result: incomeTaxResult }))
    assert.match(table, /所得税计算表/)
    assert.match(table, /营业收入/)
    assert.match(table, /弥补亏损/)
    assert.match(table, /应纳税所得额/)
    assert.match(table, />97\.5000</)
    assert.match(table, />292\.5000</)
    assert.match(table, /所得税率 25\.0000%/)

    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const bubble = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'income-result', role: 'assistant', content: '经济测算完成。',
      calculationResults: [economicIncomeTaxResult],
    } }))
    assert.match(bubble, /所得税计算表/)
    assert.doesNotMatch(bubble, /收入及税金表/)
  } finally {
    await server.close()
  }
})
