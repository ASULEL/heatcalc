import assert from 'node:assert/strict'
import { test, type TestContext } from 'node:test'
import { useConversations } from '../src/composables/useConversations.ts'
import type { CalculationResult, EconomicRequest, ParameterField } from '../src/types.ts'
import { bankResult, economicLoanResult } from './fixtures.ts'
import { costFields, costInputs, economicCostResult } from './cost-fixtures.ts'
import { economicRevenueTaxResult, revenueTaxFields, revenueTaxInputs } from './revenue-tax-fixtures.ts'
import { economicIncomeTaxResult, incomeTaxFields, incomeTaxInputs } from './income-tax-fixtures.ts'
import { cashFlowFields, cashFlowInputs, economicCashFlowResult } from './cash-flow-fixtures.ts'

interface PendingRequest {
  url: string
  body: {
    message?: string
    request?: EconomicRequest
    history?: { role: string; content: string }[]
    parameter_values?: Record<string, string | number>
    calculation_results?: CalculationResult[]
  }
  signal: AbortSignal | null | undefined
  resolve: (response: Response) => void
  reject: (error: Error) => void
}

function mockRequests(t: TestContext) {
  const requests: PendingRequest[] = []
  t.mock.method(globalThis, 'fetch', (url: unknown, init?: RequestInit) =>
    new Promise<Response>((resolve, reject) => {
      requests.push({
        url: String(url),
        body: JSON.parse(String(init?.body || '{}')),
        signal: init?.signal,
        resolve,
        reject,
      })
    }),
  )
  return requests
}

test('新建对话后，旧请求的回复仍写入原对话', async (t) => {
  const requests = mockRequests(t)
  // 即使同一毫秒内新建，对话和消息也不能使用相同 ID。
  t.mock.method(Date, 'now', () => 123)
  const state = useConversations()
  const original = state.current.value!
  const sending = state.sendMessage('原对话的问题')
  assert.equal(state.loading.value, true)

  const newId = state.createConversation()
  assert.notEqual(newId, original.id)
  assert.equal(state.loading.value, false)

  requests[0]!.resolve(Response.json({ response: '原对话的回答' }))
  await sending

  assert.equal(state.currentId.value, newId)
  assert.deepEqual(state.current.value!.messages, [])
  assert.deepEqual(original.messages.map((message) => message.content), [
    '原对话的问题',
    '原对话的回答',
  ])
  assert.notEqual(original.messages[0]!.id, original.messages[1]!.id)
})

test('切换对话后，请求失败提示仍属于原对话', async (t) => {
  const requests = mockRequests(t)
  t.mock.method(console, 'error', () => {})
  const state = useConversations()
  const original = state.current.value!
  const sending = state.sendMessage('原对话的问题')
  state.createConversation()

  requests[0]!.reject(new Error('网络连接失败'))
  await sending

  assert.deepEqual(state.current.value!.messages, [])
  assert.match(original.messages[1]!.content, /请求失败/)
  assert.equal(state.loading.value, false)
})

for (const firstToFinish of [0, 1]) {
  test(`两个对话并发请求，第 ${firstToFinish + 1} 个先完成时状态互不影响`, async (t) => {
    const requests = mockRequests(t)
    const state = useConversations()
    const first = state.current.value!
    const firstSending = state.sendMessage('问题 A')
    state.createConversation()
    const second = state.current.value!
    const secondSending = state.sendMessage('问题 B')
    const conversations = [first, second]
    const sending = [firstSending, secondSending]
    const remaining = 1 - firstToFinish

    requests[firstToFinish]!.resolve(Response.json({ response: `回答 ${firstToFinish}` }))
    await sending[firstToFinish]
    assert.equal(state.currentId.value, second.id)

    state.selectConversation(conversations[remaining]!.id)
    assert.equal(state.loading.value, true)
    state.selectConversation(conversations[firstToFinish]!.id)
    assert.equal(state.loading.value, false)

    requests[remaining]!.resolve(Response.json({ response: `回答 ${remaining}` }))
    await sending[remaining]

    assert.equal(state.loading.value, false)
    assert.equal(first.messages[1]!.content, '回答 0')
    assert.equal(second.messages[1]!.content, '回答 1')
    assert.deepEqual(requests[0]!.body.history, [])
    assert.deepEqual(requests[1]!.body.history, [])
  })
}

test('等待回复时，同一对话不能重复提交', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const sending = state.sendMessage('第一个问题')
  await state.sendMessage('重复提交的问题')

  assert.equal(requests.length, 1)
  assert.equal(state.current.value!.messages.length, 1)
  requests[0]!.resolve(Response.json({ response: '回答' }))
  await sending
})

test('新对话可以先命名，首次提问不会覆盖自定义名称', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  state.renameConversation(state.currentId.value!, '  热泵方案一  ')

  const sending = state.sendMessage('计算热泵购电成本')
  requests[0]!.resolve(Response.json({ response: '计算结果' }))
  await sending

  assert.equal(state.current.value!.title, '热泵方案一')
})

test('等待回复期间可以重命名，回复仍属于同一个对话', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const originalId = state.currentId.value!
  const sending = state.sendMessage('计算问题')
  state.renameConversation(originalId, '电加热器方案')
  state.createConversation()
  requests[0]!.resolve(Response.json({ response: '计算结果' }))
  await sending

  const original = state.conversations.value.find((c) => c.id === originalId)!
  assert.equal(original.title, '电加热器方案')
  assert.equal(original.messages[1]!.content, '计算结果')
  assert.deepEqual(state.current.value!.messages, [])
})

test('空名称和不存在的对话不会修改现有名称', () => {
  const state = useConversations()
  state.renameConversation(state.currentId.value!, '锅炉方案')
  state.renameConversation(state.currentId.value!, '   ')
  state.renameConversation('不存在的对话', '其他方案')

  assert.equal(state.current.value!.title, '锅炉方案')
})

test('后续提问只携带所属对话的历史消息', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const originalId = state.currentId.value!
  const firstSending = state.sendMessage('问题 A')
  requests[0]!.resolve(Response.json({ response: '回答 A' }))
  await firstSending

  state.createConversation()
  const secondSending = state.sendMessage('问题 B')
  requests[1]!.resolve(Response.json({ response: '回答 B' }))
  await secondSending

  state.selectConversation(originalId)
  const followUp = state.sendMessage('继续问题 A')
  assert.deepEqual(requests[2]!.body, {
    message: '继续问题 A',
    history: [
      { role: 'user', content: '问题 A' },
      { role: 'assistant', content: '回答 A' },
    ],
  })
  requests[2]!.resolve(Response.json({ response: '后续回答 A' }))
  await followUp
  assert.equal(state.current.value!.title, '问题 A')
})

test('删除当前对话后选择相邻对话，删完后提供新的空对话', () => {
  const state = useConversations()
  const firstId = state.currentId.value!
  const secondId = state.createConversation()
  const thirdId = state.createConversation()

  state.selectConversation(secondId)
  state.deleteConversation(secondId)
  assert.equal(state.currentId.value, thirdId)
  assert.deepEqual(state.conversations.value.map((c) => c.id), [firstId, thirdId])

  state.deleteConversation(firstId)
  assert.equal(state.currentId.value, thirdId)
  state.deleteConversation(thirdId)
  assert.equal(state.conversations.value.length, 1)
  assert.notEqual(state.currentId.value, thirdId)
  assert.equal(state.current.value!.title, '新对话')
  assert.deepEqual(state.current.value!.messages, [])
})

for (const outcome of ['success', 'failure']) {
  test(`删除等待回复的对话后，迟到的 ${outcome} 不会写入新对话`, async (t) => {
    const requests = mockRequests(t)
    const state = useConversations()
    const original = state.current.value!
    const sending = state.sendMessage('即将删除的问题')
    state.deleteConversation(original.id)
    const newId = state.currentId.value

    assert.equal(requests[0]!.signal?.aborted, true)
    assert.equal(state.loading.value, false)
    if (outcome === 'success') {
      // 模拟取消后仍有响应到达。
      requests[0]!.resolve(Response.json({ response: '迟到的回答' }))
    } else {
      requests[0]!.reject(new Error('请求已取消'))
    }
    await sending

    assert.equal(state.conversations.value.length, 1)
    assert.equal(state.currentId.value, newId)
    assert.deepEqual(state.current.value!.messages, [])
    assert.equal(original.messages.length, 1)
  })
}

test('删除后台请求中的对话不会清除当前对话的加载状态', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const originalId = state.currentId.value!
  const firstSending = state.sendMessage('问题 A')
  const currentId = state.createConversation()
  const secondSending = state.sendMessage('问题 B')

  state.deleteConversation(originalId)
  requests[0]!.resolve(Response.json({ response: '回答 A' }))
  await firstSending
  assert.equal(state.currentId.value, currentId)
  assert.equal(state.loading.value, true)

  requests[1]!.resolve(Response.json({ response: '回答 B' }))
  await secondSending
  assert.equal(state.loading.value, false)
  assert.deepEqual(state.current.value!.messages.map((m) => m.content), ['问题 B', '回答 B'])
})

test('后端 HTTP 错误显示失败提示，不写入空回复', async (t) => {
  const requests = mockRequests(t)
  t.mock.method(console, 'error', () => {})
  const state = useConversations()
  const sending = state.sendMessage('问题')
  requests[0]!.resolve(Response.json({ detail: '服务异常' }, { status: 500 }))
  await sending

  assert.match(state.current.value!.messages[1]!.content, /请求失败/)
  assert.equal(state.loading.value, false)
})

test('保存参数表并提交填写值', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const fields: ParameterField[] = [
    {
      name: 'renewable_power',
      label: '风电或光伏功率',
      unit: 'kW',
      group: '风光与电加热参数',
      advanced: false,
      value: null,
      required: true,
    },
  ]

  const firstSending = state.sendMessage('根据光伏功率计算蒸汽流量')
  requests[0]!.resolve(Response.json({ response: '请填写参数', parameter_form: fields }))
  await firstSending
  assert.deepEqual(state.current.value!.messages[1]!.parameterForm, fields)

  const secondSending = state.sendParameterValues(fields, { renewable_power: '8000' })
  assert.deepEqual(requests[1]!.body.parameter_values, { renewable_power: '8000' })
  requests[1]!.resolve(Response.json({ response: '参数已收到' }))
  await secondSending
  assert.match(state.current.value!.messages[2]!.content, /风电或光伏功率/)
})

test('提交表格显示单位时转换为工具单位', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const fields: ParameterField[] = [
    {
      name: 'charging_power',
      label: '热泵输出热功率',
      unit: 'MWt',
      group: '热泵基础参数',
      advanced: false,
      value: 100,
      required: true,
      isDefault: true,
      toToolFactor: 1000,
    },
  ]

  const sending = state.sendParameterValues(fields, { charging_power: '100' })
  assert.deepEqual(requests[0]!.body.parameter_values, { charging_power: 100000 })
  requests[0]!.resolve(Response.json({ response: '参数已收到' }))
  await sending
})

const loanFields: ParameterField[] = [{
  name: 'static_investment', label: '静态投资', unit: '万元',
  group: '计算参数', advanced: false, required: true, value: 34320,
  toolName: 'calculate_economic_scheme', schemeStep: 'loan',
}]

test('方案入口先展示借款表单，成功后新增成本步骤并归入原对话', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const original = state.current.value!
  const start = state.startEconomicScheme()
  assert.match(requests[0]!.url, /calculate_economic_scheme\/parameters$/)
  requests[0]!.resolve(Response.json({ response: '先填写借款参数', parameter_form: loanFields }))
  await start
  const source = original.messages[1]!
  const schemeId = source.economicStep!.schemeId
  const result = { ...economicLoanResult, scheme_id: schemeId }
  const sending = state.sendParameterValues(loanFields, { static_investment: '34320' }, source.id)
  assert.match(requests[1]!.url, /\/api\/tools\/calculate_economic_scheme$/)
  assert.deepEqual(requests[1]!.body.request, {
    step: 'loan', scheme_id: schemeId, inputs: { static_investment: '34320' },
  })
  state.createConversation()
  requests[1]!.resolve(Response.json({
    response: '请填写成本参数', calculation_results: [result], parameter_form: costFields,
  }))
  await sending
  assert.deepEqual(state.current.value!.scenario.economicSchemes, [])
  assert.equal(original.scenario.economicSchemes[0]!.stage, 'cost')
  assert.deepEqual(original.scenario.calculationResults, [result])
  assert.equal(source.content, '先填写借款参数')
  assert.equal(source.submitted, true)
  assert.deepEqual(source.submittedValues, { static_investment: '34320' })
  const next = original.messages[3]!
  assert.equal(next.economicStep!.schemeId, schemeId)
  assert.deepEqual(next.economicStep!.loanResult, bankResult)
  assert.equal(next.economicStep!.step, 'cost')

  state.selectConversation(original.id)
  const followUp = state.sendMessage('后面的表要用到当年利息这一列')
  assert.deepEqual(requests[2]!.body.calculation_results, [{ ...result, scheme_name: '经济测算 1' }])
  requests[2]!.resolve(Response.json({ response: '可以引用原始数据。' }))
  await followUp
})

test('方案页新建经济测算会切换到新的对话', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const original = state.current.value!

  const start = state.startNewEconomicScheme()
  const fresh = state.current.value!
  assert.notEqual(fresh.id, original.id)
  assert.deepEqual(original.messages, [])
  assert.equal(fresh.messages[0]!.content, '开始经济测算')
  assert.match(requests[0]!.url, /calculate_economic_scheme\/parameters$/)

  requests[0]!.resolve(Response.json({ response: '先填写借款参数', parameter_form: loanFields }))
  await start

  assert.equal(original.messages.length, 0)
  assert.equal(fresh.messages[1]!.content, '先填写借款参数')
  assert.equal(fresh.messages[1]!.economicStep!.step, 'loan')
})

test('重新测算创建新方案，后续结果不改变历史消息或历史借款来源', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const firstSending = state.sendMessage('开始经济测算')
  requests[0]!.resolve(Response.json({
    response: '已生成借款表，继续填写成本', calculation_results: [economicLoanResult], parameter_form: costFields,
  }))
  await firstSending
  const historical = state.current.value!.messages[1]!
  const snapshot = JSON.stringify(historical)
  const changed = {
    ...economicLoanResult, scheme_id: 'scheme-2',
    loan_result: { ...bankResult, inputs: { ...bankResult.inputs, static_investment: 50000 } },
  }
  const secondSending = state.sendMessage('重新经济测算')
  requests[1]!.resolve(Response.json({
    response: '新方案借款已完成', calculation_results: [changed], parameter_form: costFields,
  }))
  await secondSending
  assert.equal(JSON.stringify(historical), snapshot)
  assert.equal(historical.economicStep!.loanResult!.inputs.static_investment, 34320)
  assert.equal(state.current.value!.scenario.economicSchemes.length, 2)
  const costSending = state.sendCostValues(costInputs, historical.id)
  assert.equal(requests[2]!.body.request!.scheme_id, 'scheme-1')
  assert.equal(requests[2]!.body.request!.step, 'cost')
  const request = requests[2]!.body.request!
  if (request.step === 'cost') assert.equal(request.loan_result.inputs.static_investment, 34320)
  requests[2]!.resolve(Response.json({ response: '填写收入及税金参数', calculation_results: [economicCostResult], parameter_form: revenueTaxFields }))
  await costSending
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'revenue_tax')
  assert.equal(state.current.value!.scenario.economicSchemes[1]!.stage, 'cost')
  assert.deepEqual(historical.submittedCostInputs, costInputs)
  assert.equal(historical.content, '已生成借款表，继续填写成本')
  assert.equal(historical.economicStep!.loanResult!.inputs.static_investment, 34320)
  assert.equal(state.current.value!.messages.at(-1)!.calculationResults![0]!.cost_result!.schedule[2]!.depreciation_cost, 1690.1688648)
  const count = requests.length
  await state.sendCostValues(costInputs, historical.id)
  assert.equal(requests.length, count)
})

test('成本完成后税金表单绑定原方案，提交后保存税金结果与历史输入', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const opening = state.sendMessage('计算收入及税金')
  requests[0]!.resolve(Response.json({
    response: '填写税金参数', calculation_results: [economicCostResult], parameter_form: revenueTaxFields,
  }))
  await opening
  const source = state.current.value!.messages[1]!
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'revenue_tax')
  assert.equal(source.economicStep!.step, 'revenue_tax')
  assert.deepEqual(source.economicStep!.costResult, economicCostResult.cost_result)

  const another = state.sendMessage('另一方案的成本')
  requests[1]!.resolve(Response.json({
    response: '另一方案税金参数',
    calculation_results: [{ ...economicCostResult, scheme_id: 'scheme-2' }], parameter_form: revenueTaxFields,
  }))
  await another
  const sending = state.sendRevenueTaxValues(revenueTaxInputs, source.id)
  const request = requests[2]!.body.request!
  assert.equal(request.step, 'revenue_tax')
  assert.equal(request.scheme_id, 'scheme-1')
  if (request.step === 'revenue_tax') {
    assert.deepEqual(request.cost_result, economicCostResult.cost_result)
    assert.deepEqual(request.inputs, revenueTaxInputs)
  }
  requests[2]!.resolve(Response.json({
    response: '收入及税金已生成', calculation_results: [economicRevenueTaxResult], parameter_form: incomeTaxFields,
  }))
  await sending
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'income_tax')
  assert.equal(state.current.value!.scenario.economicSchemes[1]!.stage, 'revenue_tax')
  assert.deepEqual(source.submittedRevenueTaxInputs, revenueTaxInputs)
  assert.equal(source.submitted, true)
  assert.deepEqual(state.current.value!.scenario.economicSchemes[0]!.revenueTaxResult, economicRevenueTaxResult.revenue_tax_result)
  const incomeSource = state.current.value!.messages.at(-1)!
  assert.equal(incomeSource.economicStep!.step, 'income_tax')
  const incomeSending = state.sendIncomeTaxValues(incomeTaxInputs, incomeSource.id)
  const incomeRequest = requests[3]!.body.request!
  assert.equal(incomeRequest.step, 'income_tax')
  assert.equal(incomeRequest.scheme_id, 'scheme-1')
  if (incomeRequest.step === 'income_tax') {
    assert.deepEqual(incomeRequest.revenue_tax_result, economicRevenueTaxResult.revenue_tax_result)
    assert.deepEqual(incomeRequest.inputs, incomeTaxInputs)
  }
  requests[3]!.resolve(Response.json({
    response: '所得税已生成', calculation_results: [economicIncomeTaxResult], parameter_form: cashFlowFields,
  }))
  await incomeSending
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'cash_flow')
  assert.deepEqual(incomeSource.submittedIncomeTaxInputs, incomeTaxInputs)
  assert.equal(incomeSource.submitted, true)
  assert.deepEqual(state.current.value!.scenario.economicSchemes[0]!.incomeTaxResult, economicIncomeTaxResult.income_tax_result)
  const cashSource = state.current.value!.messages.at(-1)!
  assert.equal(cashSource.economicStep!.step, 'cash_flow')
  const cashSending = state.sendCashFlowValues(cashFlowInputs, cashSource.id)
  const cashRequest = requests[4]!.body.request!
  assert.equal(cashRequest.step, 'cash_flow')
  assert.equal(cashRequest.scheme_id, 'scheme-1')
  if (cashRequest.step === 'cash_flow') {
    assert.deepEqual(cashRequest.income_tax_result, economicIncomeTaxResult.income_tax_result)
    assert.deepEqual(cashRequest.inputs, cashFlowInputs)
  }
  requests[4]!.resolve(Response.json({ response: '现金流已生成', calculation_results: [economicCashFlowResult] }))
  await cashSending
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'completed')
  assert.deepEqual(cashSource.submittedCashFlowInputs, cashFlowInputs)
  assert.equal(cashSource.submitted, true)
  assert.deepEqual(state.current.value!.scenario.economicSchemes[0]!.cashFlowResult, economicCashFlowResult.cash_flow_result)
  const count = requests.length
  await state.sendCashFlowValues(cashFlowInputs, cashSource.id)
  assert.equal(requests.length, count)
  await state.sendIncomeTaxValues(incomeTaxInputs, incomeSource.id)
  assert.equal(requests.length, count)
  await state.sendRevenueTaxValues(revenueTaxInputs, source.id)
  assert.equal(requests.length, count)
})

test('税金提交的参数错误显示具体原因，原表单保留重试能力', async (t) => {
  const requests = mockRequests(t)
  t.mock.method(console, 'error', () => {})
  const state = useConversations()
  const opening = state.sendMessage('税金参数')
  requests[0]!.resolve(Response.json({ response: '填写参数', calculation_results: [economicCostResult], parameter_form: revenueTaxFields }))
  await opening
  const source = state.current.value!.messages[1]!
  const sending = state.sendRevenueTaxValues(revenueTaxInputs, source.id)
  requests[1]!.resolve(Response.json({ detail: '借款表和成本表的项目年份必须一致' }, { status: 422 }))
  await sending
  assert.match(state.current.value!.messages.at(-1)!.content, /项目年份必须一致/)
  assert.equal(source.submitted, undefined)
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'revenue_tax')
})

test('经济测算提交失败可以重试，成功才冻结历史输入', async (t) => {
  const requests = mockRequests(t)
  t.mock.method(console, 'error', () => {})
  const state = useConversations()
  const start = state.startEconomicScheme()
  requests[0]!.resolve(Response.json({ response: '借款参数', parameter_form: loanFields }))
  await start
  const source = state.current.value!.messages[1]!
  const failed = state.sendParameterValues(loanFields, { static_investment: '34320' }, source.id)
  requests[1]!.resolve(Response.json({}, { status: 500 }))
  await failed
  assert.equal(source.submitted, undefined)
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'loan')
  const retry = state.sendParameterValues(loanFields, { static_investment: '34320' }, source.id)
  requests[2]!.resolve(Response.json({
    response: '借款完成', parameter_form: costFields,
    calculation_results: [{ ...economicLoanResult, scheme_id: source.economicStep!.schemeId }],
  }))
  await retry
  assert.equal(source.submitted, true)
  assert.equal(state.current.value!.scenario.economicSchemes[0]!.stage, 'cost')
})

test('修改静态投资后引用新借款结果，旧成本表单失效且只发送最新方案数据', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const opening = state.sendMessage('开始经济测算')
  requests[0]!.resolve(Response.json({
    response: '请填写成本参数', calculation_results: [economicLoanResult], parameter_form: costFields,
  }))
  await opening
  const oldForm = state.current.value!.messages[1]!
  const originalSource = JSON.stringify(oldForm.economicStep)
  const updated = structuredClone(economicLoanResult)
  updated.loan_result.inputs.static_investment = 30458.8235
  updated.loan_result.summary.static_investment = 30458.8235

  const revising = state.sendMessage('将静态投资改成30458.8235')
  assert.deepEqual(requests[1]!.body.calculation_results, [{ ...economicLoanResult, scheme_name: '经济测算 1' }])
  requests[1]!.resolve(Response.json({
    response: '已更新借款表，请继续填写成本参数', calculation_results: [updated], parameter_form: costFields,
  }))
  await revising
  const latest = state.current.value!.messages.at(-1)!
  assert.equal(state.loading.value, false)
  assert.equal(oldForm.superseded, true)
  assert.equal(JSON.stringify(oldForm.economicStep), originalSource)
  assert.equal(latest.economicStep!.loanResult!.inputs.static_investment, 30458.8235)
  assert.deepEqual(state.current.value!.scenario.calculationResults, [updated])

  await state.sendCostValues(costInputs, oldForm.id)
  assert.equal(requests.length, 2)
  const submitting = state.sendCostValues(costInputs, latest.id)
  const request = requests[2]!.body.request!
  assert.equal(request.step, 'cost')
  if (request.step === 'cost') assert.equal(request.loan_result.inputs.static_investment, 30458.8235)
  requests[2]!.resolve(Response.json({
    response: '成本已重新计算', calculation_results: [{ ...economicCostResult, loan_result: updated.loan_result }],
    parameter_form: revenueTaxFields,
  }))
  await submitting
  assert.equal(state.current.value!.scenario.calculationResults.length, 1)
  const followUp = state.sendMessage('引用当前借款利息')
  assert.equal(requests[3]!.body.calculation_results!.length, 1)
  assert.equal(requests[3]!.body.calculation_results![0]!.loan_result.inputs.static_investment, 30458.8235)
  requests[3]!.resolve(Response.json({ response: '已引用最新结果' }))
  await followUp
})

test('完整方案联动重算后保存三张新表，其他方案与历史结果保留', async (t) => {
  const requests = mockRequests(t)
  const state = useConversations()
  const opening = state.sendMessage('生成收入税金表')
  requests[0]!.resolve(Response.json({ response: '已完成', calculation_results: [economicRevenueTaxResult] }))
  await opening
  const historical = state.current.value!.messages[1]!
  const history = JSON.stringify(historical)
  const other = { ...economicLoanResult, scheme_id: 'scheme-2' }
  const startingOther = state.sendMessage('另一个方案')
  requests[1]!.resolve(Response.json({ response: '填写成本参数', calculation_results: [other], parameter_form: costFields }))
  await startingOther
  const otherForm = state.current.value!.messages[3]!

  const loan = structuredClone(economicLoanResult)
  loan.loan_result.inputs.static_investment = 30458.8235
  const cost = { ...economicCostResult, loan_result: loan.loan_result }
  const tax = { ...economicRevenueTaxResult, loan_result: loan.loan_result }
  const revising = state.sendMessage('将经济测算1的静态投资改成30458.8235')
  requests[2]!.resolve(Response.json({ response: '已联动重算', calculation_results: [loan, cost, tax] }))
  await revising
  assert.equal(JSON.stringify(historical), history)
  assert.equal(otherForm.superseded, undefined)
  assert.deepEqual(state.current.value!.scenario.calculationResults, [tax, other])
  const scheme = state.current.value!.scenario.economicSchemes[0]!
  assert.equal(scheme.stage, 'income_tax')
  assert.deepEqual(scheme.loanResult, loan.loan_result)
  assert.deepEqual(scheme.costResult, cost.cost_result)
  assert.deepEqual(scheme.revenueTaxResult, tax.revenue_tax_result)
})

test('模型超时后显示原因并结束等待，可以继续发消息', async (t) => {
  const requests = mockRequests(t)
  t.mock.method(console, 'error', () => {})
  const state = useConversations()
  const sending = state.sendMessage('解释计算原理')
  requests[0]!.resolve(Response.json({ detail: '模型响应超时，请重试。' }, { status: 504 }))
  await sending
  assert.equal(state.loading.value, false)
  assert.match(state.current.value!.messages.at(-1)!.content, /模型响应超时/)
  const retry = state.sendMessage('重试解释')
  assert.equal(requests.length, 2)
  requests[1]!.resolve(Response.json({ response: '计算说明' }))
  await retry
  assert.equal(state.loading.value, false)
})
