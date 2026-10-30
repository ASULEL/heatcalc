import assert from 'node:assert/strict'
import { test } from 'node:test'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createServer } from 'vite'
import { bankResult, economicLoanResult } from './fixtures.ts'
import { costFields, economicCostResult } from './cost-fixtures.ts'

test('消息中的原始借款数据渲染为表格，金额展示四位小数且保留原始数据', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const html = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'loan-message', role: 'assistant', content: '计算完成。', calculationResults: [economicLoanResult],
    } }))

    assert.match(html, /借款还本付息表/)
    assert.match(html, /当年利息/)
    assert.match(html, />751\.1962</)
    assert.match(html, />1902\.4445</)
    assert.match(html, /overflow-auto/)
    assert.match(html, /text-right/)
    assert.match(html, />0\.0000</)
    assert.equal((html.match(/<tr\b/g) || []).length, bankResult.schedule.length + 1)
    assert.equal(bankResult.schedule[1]!.interest_expense, 751.19616)
  } finally {
    await server.close()
  }
})

test('成本表显示 Excel 分组，成本参数使用年度输入表单', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const table = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'cost-result', role: 'assistant', content: '计算完成。', calculationResults: [economicCostResult],
    } }))
    assert.match(table, /经营成本/)
    assert.match(table, /折旧摊销/)
    assert.match(table, /财务成本/)
    assert.match(table, /colspan="5"/)
    assert.equal((table.match(/colspan="2"/g) || []).length, 2)
    assert.match(table, />4840\.5912</)
    assert.match(table, /流动资金借款利息/)
    assert.match(table, />85\.8000</)
    assert.match(table, />1488\.0812</)
    assert.match(table, />0\.0000</)
    assert.doesNotMatch(table, /<h3[^>]*>借款还本付息表/)

    const form = await renderToString(createSSRApp(MessageBubble, {
      message: { id: 'cost-form', role: 'assistant', content: '请填写成本参数。', parameterForm: costFields,
        economicStep: { schemeId: 'scheme-1', step: 'cost', loanResult: bankResult },
      },
    }))
    assert.match(form, /维修费比例区间/)
    assert.match(form, /各年费用输入/)
    assert.match(form, /第3年各年含税总电费/)
    assert.match(form, /2390\.4133/)
    assert.match(form, /生成成本计算表/)
    assert.doesNotMatch(form, /\[object Object\]/)
  } finally {
    await server.close()
  }
})

test('历史成本参数重新展示时保留提交值和固定来源，表单为只读', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: MessageBubble } = await server.ssrLoadModule('/src/components/MessageBubble.vue')
    const inputs = { ...economicCostResult.cost_result!.inputs, equipment_total_cost: 12345, depreciation_years: 15 }
    const html = await renderToString(createSSRApp(MessageBubble, { message: {
      id: 'history', role: 'assistant', content: '请填写成本参数。', parameterForm: costFields,
      economicStep: { schemeId: 'scheme-1', step: 'cost', loanResult: bankResult },
      submitted: true, submittedCostInputs: inputs,
    } }))
    assert.match(html, /请填写成本参数/)
    assert.match(html, /已提交，以下为当时的参数/)
    assert.match(html, /value="12345"/)
    assert.match(html, /value="15"/)
    assert.match(html, /<fieldset disabled/)
    assert.match(html, /引用本方案借款表/)
    assert.doesNotMatch(html, /请先在当前对话生成/)
    assert.doesNotMatch(html, /<select/)
  } finally {
    await server.close()
  }
})

test('方案页展示统一经济测算入口及各方案进度', async () => {
  const server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' })
  try {
    const { default: SchemePanel } = await server.ssrLoadModule('/src/components/SchemePanel.vue')
    const html = await renderToString(createSSRApp(SchemePanel, {
      loading: false,
      schemes: [
        { id: 'scheme-1', name: '经济测算 1', stage: 'completed', loanResult: bankResult, costResult: economicCostResult.cost_result },
        { id: 'scheme-2', name: '经济测算 2', stage: 'cost', loanResult: bankResult },
      ],
    }))
    assert.match(html, /新建经济测算/)
    assert.match(html, /经济测算 1/)
    assert.match(html, /经济测算 2/)
    assert.match(html, /已完成/)
    assert.match(html, /待填写成本参数/)
    assert.match(html, /继续填写/)
    assert.match(html, /查看结果/)
    assert.match(html, /34320\.0000 万元/)
  } finally {
    await server.close()
  }
})
