import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createServer } from 'vite'
import { bankResult } from './fixtures.ts'
import { costResult } from './cost-fixtures.ts'
import { revenueTaxResult } from './revenue-tax-fixtures.ts'
import { incomeTaxResult } from './income-tax-fixtures.ts'
import { cashFlowFields, cashFlowInputs, cashFlowResult, economicCashFlowResult } from './cash-flow-fixtures.ts'

test('现金流表单预填资本金比例30%，历史提交只读', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const form = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'cash-form', role: 'assistant', content: '请填写现金流参数。', parameterForm: cashFlowFields,
      economicStep: {
        schemeId: 'scheme-1', step: 'cash_flow', loanResult: bankResult, costResult,
        revenueTaxResult, incomeTaxResult,
      },
    } }))
    assert.match(form, /现金流量参数/)
    assert.match(form, /资本金比例/)
    assert.match(form, /value="30"/)
    assert.match(form, /生成现金流量表/)
    assert.doesNotMatch(form, /导出 Excel/)

    const history = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'cash-history', role: 'assistant', content: '请填写现金流参数。', parameterForm: cashFlowFields,
      economicStep: {
        schemeId: 'scheme-1', step: 'cash_flow', loanResult: bankResult, costResult,
        revenueTaxResult, incomeTaxResult,
      },
      submitted: true, submittedCashFlowInputs: cashFlowInputs,
    } }))
    assert.match(history, /已提交，以下为当时的参数/)
    assert.match(history, /<fieldset disabled/)
    assert.match(history, /value="30"/)
  } finally {
    await server.close()
  }
})

test('现金流表显示IRR、回收期和年度明细，结果消息同时显示两张表', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: CashFlowTable } = await server.ssrLoadModule('/src/components/CashFlowTable.vue')
    const table = await renderToString(createSSRApp(CashFlowTable, {
      result: cashFlowResult.capital, equityRatio: 0.30,
    }))
    assert.match(table, /资本金现金流量表/)
    assert.match(table, /内部收益率（IRR）/)
    assert.match(table, /10\.00%/)
    assert.match(table, /0\.86 年/)
    assert.match(table, /回收固定资产余值/)
    assert.match(table, /累计净现金流量/)
    assert.match(table, /预计静态投资回收期（年）/)
    assert.match(table, />145\.0000</)
    assert.match(table, /资本金比例 30\.0000%/)

    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const bubble = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'cash-result', role: 'assistant', content: '经济测算完成。',
      calculationResults: [economicCashFlowResult],
    } }))
    assert.match(bubble, /资本金现金流量表/)
    assert.match(bubble, /全投资现金流量表/)
    assert.doesNotMatch(bubble, /所得税计算表/)
    assert.doesNotMatch(bubble, /收入及税金表/)
    assert.match(bubble, /<button[^>]*>导出 Excel<\/button>/)
    assert.match(bubble, /下载该方案最新的全部测算表格/)

    const { default: ChatWindow } = await server.ssrLoadModule('/src/components/ChatWindow.vue')
    const exporting = await renderToString(createSSRApp(ChatWindow, {
      title: '经济测算', loading: false, exportingSchemeId: 'scheme-1',
      messages: [{ id: 'completed', role: 'assistant', content: '经济测算完成。', calculationResults: [economicCashFlowResult] }],
    }))
    assert.match(exporting, /<button[^>]*disabled[^>]*>正在导出…<\/button>/)
    const failed = await renderToString(createSSRApp(ChatWindow, {
      title: '经济测算', loading: false,
      exportError: { schemeId: 'scheme-1', message: '导出失败，请重试。' },
      messages: [{ id: 'completed', role: 'assistant', content: '经济测算完成。', calculationResults: [economicCashFlowResult] }],
    }))
    assert.match(failed, /role="alert"[^>]*>导出失败，请重试。/)
  } finally {
    await server.close()
  }
})

test('年度预计回收期单独展示，运营结束后各金额留空，未回收时明确说明', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: CashFlowTable } = await server.ssrLoadModule('/src/components/CashFlowTable.vue')
    const result = structuredClone(cashFlowResult.capital)
    result.summary.static_payback_period = null
    result.schedule[2]!.estimated_payback_period = 8.75
    result.schedule[2]!.payback_period = null
    // 历史结果即使还保存着金额，结束后的行也不能显示。
    result.schedule.push({ ...result.schedule[2]!, year: 4, phase: '运营结束' })
    const html = await renderToString(createSSRApp(CashFlowTable, { result }))
    assert.match(html, /运营期内未回收/)
    assert.match(html, />8\.75</)
    const endedRow = html.match(/<tbody[^>]*>([\s\S]*?)<\/tbody>/)![1]!.match(/<tr\b[^>]*>[\s\S]*?<\/tr>/g)!.at(-1)!
    const cells = [...endedRow.matchAll(/<td\b[^>]*>(.*?)<\/td>/g)].map(match => match[1])
    assert.equal(cells[0], '运营结束')
    assert.equal(cells.length, 13)
    assert.ok(cells.slice(1).every(value => value === ''))
  } finally {
    await server.close()
  }
})
