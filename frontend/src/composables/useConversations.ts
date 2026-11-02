import { computed, ref, shallowReactive } from 'vue'
import { formatMoney } from '../formatting.ts'
import type {
  CalculationResult, CashFlowInputs, ChatMessage, Conversation, CostScheduleInputs,
  EconomicRequest, IncomeTaxInputs, ParameterField, RevenueTaxInputs,
} from '../types'

interface RequestOptions {
  startScheme?: boolean // 从方案入口开始借款输入
  economicRequest?: EconomicRequest // 本次经济测算步骤
  sourceMessage?: ChatMessage // 提交来源，不依赖当前最新方案
  parameterSnapshot?: Record<string, string> // 借款输入快照
  costSnapshot?: CostScheduleInputs // 成本输入快照
  revenueTaxSnapshot?: RevenueTaxInputs
  incomeTaxSnapshot?: IncomeTaxInputs
  cashFlowSnapshot?: CashFlowInputs
}

const stepOrder = { loan: 0, cost: 1, revenue_tax: 2, income_tax: 3, cash_flow: 4 }

export function useConversations() {
  const conversations = ref<Conversation[]>([])
  const currentId = ref<string | null>(null)
  const pendingRequests = shallowReactive(new Map<string, AbortController>())
  const current = computed(() => conversations.value.find(c => c.id === currentId.value))
  const loading = computed(() => currentId.value !== null && pendingRequests.has(currentId.value))

  function createConversation() {
    const id = crypto.randomUUID()
    conversations.value.push({
      id, title: '新对话', hasCustomTitle: false, messages: [],
      scenario: { calculationResults: [], economicSchemes: [] },
    })
    currentId.value = id
    return id
  }

  function selectConversation(id: string) {
    if (conversations.value.some(c => c.id === id)) currentId.value = id
  }

  function renameConversation(id: string, title: string) {
    const conversation = conversations.value.find(c => c.id === id)
    const name = title.trim()
    if (!conversation || !name) return
    conversation.title = name
    conversation.hasCustomTitle = true
  }

  function deleteConversation(id: string) {
    const index = conversations.value.findIndex(c => c.id === id)
    if (index === -1) return
    pendingRequests.get(id)?.abort()
    pendingRequests.delete(id)
    conversations.value.splice(index, 1)
    if (currentId.value !== id) return
    const next = conversations.value[index] ?? conversations.value[index - 1]
    if (next) currentId.value = next.id
    else createConversation()
  }

  function appendReply(
    conversation: Conversation,
    data: { response: string; parameter_form?: ParameterField[]; calculation_results?: CalculationResult[] },
  ) {
    const results = data.calculation_results || [] // 本次结果，历史消息不读取方案的可变状态
    const fields = data.parameter_form || [] // 本次返回的下一步表单
    const schemes = conversation.scenario.economicSchemes
    const message: ChatMessage = {
      id: crypto.randomUUID(), role: 'assistant', content: data.response,
      parameterForm: fields.length ? fields : undefined, calculationResults: results,
    }

    for (const result of results) {
      const saved = conversation.scenario.calculationResults
      const index = saved.findIndex(item => item.scheme_id === result.scheme_id)
      if (index === -1) saved.push(result)
      else saved[index] = result

      for (const previous of conversation.messages) {
        const context = previous.economicStep
        if (context?.schemeId === result.scheme_id && !previous.submitted && stepOrder[context.step] >= stepOrder[result.step]) {
          previous.superseded = true
        }
      }

      let scheme = schemes.find(item => item.id === result.scheme_id)
      if (!scheme) {
        scheme = { id: result.scheme_id, name: `经济测算 ${schemes.length + 1}`, stage: 'loan' }
        schemes.push(scheme)
      }
      scheme.loanResult = structuredClone(result.loan_result)
      scheme.stage = result.step === 'loan' ? 'cost'
        : result.step === 'cost' ? 'revenue_tax'
          : result.step === 'revenue_tax' ? 'income_tax'
            : result.step === 'income_tax' ? 'cash_flow' : 'completed'
      if (result.step === 'loan') {
        delete scheme.costResult
        delete scheme.revenueTaxResult
        delete scheme.incomeTaxResult
        delete scheme.cashFlowResult
      } else if (result.step === 'cost') {
        delete scheme.revenueTaxResult
        delete scheme.incomeTaxResult
        delete scheme.cashFlowResult
      } else if (result.step === 'revenue_tax') {
        delete scheme.incomeTaxResult
        delete scheme.cashFlowResult
      } else if (result.step === 'income_tax') delete scheme.cashFlowResult
      if (result.cost_result) scheme.costResult = structuredClone(result.cost_result)
      if (result.revenue_tax_result) scheme.revenueTaxResult = structuredClone(result.revenue_tax_result)
      if (result.income_tax_result) scheme.incomeTaxResult = structuredClone(result.income_tax_result)
      if (result.cash_flow_result) scheme.cashFlowResult = structuredClone(result.cash_flow_result)
      message.schemeName = scheme.name
    }

    if (fields[0]?.toolName === 'calculate_economic_scheme') {
      const result = results.at(-1) // 后续表单只绑定本条回复保存的方案来源
      if (fields[0].schemeStep === 'cost' && result) {
        message.economicStep = {
          schemeId: result.scheme_id, step: 'cost', loanResult: structuredClone(result.loan_result),
        }
      } else if (fields[0].schemeStep === 'revenue_tax' && result?.cost_result) {
        message.economicStep = {
          schemeId: result.scheme_id, step: 'revenue_tax',
          loanResult: structuredClone(result.loan_result), costResult: structuredClone(result.cost_result),
        }
      } else if (fields[0].schemeStep === 'income_tax' && result?.revenue_tax_result) {
        message.economicStep = {
          schemeId: result.scheme_id, step: 'income_tax',
          loanResult: structuredClone(result.loan_result), costResult: structuredClone(result.cost_result!),
          revenueTaxResult: structuredClone(result.revenue_tax_result),
        }
      } else if (fields[0].schemeStep === 'cash_flow' && result?.income_tax_result) {
        message.economicStep = {
          schemeId: result.scheme_id, step: 'cash_flow',
          loanResult: structuredClone(result.loan_result), costResult: structuredClone(result.cost_result!),
          revenueTaxResult: structuredClone(result.revenue_tax_result!),
          incomeTaxResult: structuredClone(result.income_tax_result),
        }
      } else if (fields[0].schemeStep === 'loan') {
        const id = crypto.randomUUID()
        const name = `经济测算 ${schemes.length + 1}`
        schemes.push({ id, name, stage: 'loan' })
        message.schemeName = name
        message.economicStep = { schemeId: id, step: 'loan' }
      }
    }
    conversation.messages.push(message)
  }

  async function sendMessage(text: string, parameterValues?: object, options: RequestOptions = {}) {
    const message = text.trim()
    if (!message || options.sourceMessage?.submitted || options.sourceMessage?.superseded) return
    if (!current.value) createConversation()
    const conversation = current.value // 固定请求发起时的对话
    if (!conversation || pendingRequests.has(conversation.id)) return

    const history = conversation.messages.map(({ role, content }) => ({ role, content }))
    conversation.messages.push({ id: crypto.randomUUID(), role: 'user', content: message })
    if (conversation.messages.length === 1 && !conversation.hasCustomTitle) {
      conversation.title = message.slice(0, 30) + (message.length > 30 ? '...' : '')
    }

    const controller = new AbortController()
    pendingRequests.set(conversation.id, controller)
    const canAppendReply = () =>
      !controller.signal.aborted && conversations.value.some(c => c.id === conversation.id)

    try {
      const url = options.startScheme
        ? '/api/tools/calculate_economic_scheme/parameters'
        : options.economicRequest ? '/api/tools/calculate_economic_scheme' : '/api/chat'
      const savedSchemes = conversation.scenario.calculationResults.map(result => ({
        ...result,
        scheme_name: conversation.scenario.economicSchemes.find(scheme => scheme.id === result.scheme_id)!.name,
      }))
      const body = options.economicRequest ? { request: options.economicRequest } : {
        message, history, parameter_values: parameterValues,
        calculation_results: savedSchemes.length ? savedSchemes : undefined,
      }
      const res = await fetch(`http://127.0.0.1:8000${url}`, {
        method: options.startScheme ? 'GET' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: options.startScheme ? undefined : JSON.stringify(body),
        signal: controller.signal,
      })
      if (!res.ok) {
        const problem = await res.json().catch(() => null)
        const detail = typeof problem?.detail === 'string' ? `：${problem.detail}` : ''
        throw new Error(`请求失败：HTTP ${res.status}${detail}`)
      }
      const data = await res.json()
      if (typeof data.response !== 'string') throw new Error('回复格式无效')
      if (!canAppendReply()) return

      // 只在成功后冻结本次提交；失败时仍可修改并重试。
      if (options.sourceMessage) {
        options.sourceMessage.submitted = true
        options.sourceMessage.submittedValues = options.parameterSnapshot
        options.sourceMessage.submittedCostInputs = options.costSnapshot
        options.sourceMessage.submittedRevenueTaxInputs = options.revenueTaxSnapshot
        options.sourceMessage.submittedIncomeTaxInputs = options.incomeTaxSnapshot
        options.sourceMessage.submittedCashFlowInputs = options.cashFlowSnapshot
      }
      appendReply(conversation, data)
    } catch (err) {
      if (!canAppendReply()) return
      console.error('发送消息失败:', err)
      conversation.messages.push({
        id: crypto.randomUUID(), role: 'assistant',
        content: err instanceof Error && err.message.startsWith('请求失败') ? err.message : '请求失败，请稍后重试。',
      })
    } finally {
      pendingRequests.delete(conversation.id)
    }
  }

  function startEconomicScheme() {
    return sendMessage('开始经济测算', undefined, { startScheme: true })
  }

  function startNewEconomicScheme() {
    createConversation()
    return startEconomicScheme()
  }

  async function sendParameterValues(
    fields: ParameterField[], values: Record<string, string>, messageId?: string,
  ) {
    const source = current.value?.messages.find(message => message.id === messageId)
    const summary = fields.map(field => {
      const value = values[field.name] // 参数摘要按金额单位格式化，工具仍接收原始输入
      const display = value && field.unit.includes('元') ? formatMoney(value) : value || '未填写'
      return `${field.label}（${field.unit}）：${display}`
    }).join('\n')
    const toolValues = Object.fromEntries(fields.map(field => {
      const value = values[field.name]
      const factor = field.toToolFactor || 1
      return [field.name, value === '' ? value : factor === 1 ? value : Number(value) * factor]
    }))
    const economicRequest: EconomicRequest | undefined = source?.economicStep ? {
      step: 'loan', scheme_id: source.economicStep.schemeId, inputs: toolValues,
    } : undefined
    await sendMessage(`已提交参数：\n${summary}`, toolValues, {
      economicRequest, sourceMessage: source, parameterSnapshot: { ...values },
    })
  }

  async function sendCostValues(inputs: CostScheduleInputs, messageId: string) {
    const source = current.value!.messages.find(message => message.id === messageId)!
    const context = source.economicStep! // 由该消息保存的方案编号及借款表
    await sendMessage(
      `已提交成本参数：运营 ${inputs.operating_years} 年，折旧 ${inputs.depreciation_years} 年。`,
      undefined,
      {
        economicRequest: {
          step: 'cost', scheme_id: context.schemeId, loan_result: context.loanResult!, inputs,
        },
        sourceMessage: source, costSnapshot: structuredClone(inputs),
      },
    )
  }

  async function sendRevenueTaxValues(inputs: RevenueTaxInputs, messageId: string) {
    const source = current.value!.messages.find(message => message.id === messageId)!
    const context = source.economicStep!
    await sendMessage(
      `已提交收入及税金参数：运营期 ${inputs.operating_years} 年，收入为${inputs.income_amount_basis === 'tax_inclusive' ? '含税' : '不含税'}金额，销项税率 ${formatMoney(inputs.output_vat_rate * 100)}%。`,
      undefined,
      {
        economicRequest: {
          step: 'revenue_tax', scheme_id: context.schemeId,
          loan_result: context.loanResult!, cost_result: context.costResult!, inputs,
        },
        sourceMessage: source, revenueTaxSnapshot: structuredClone(inputs),
      },
    )
  }

  async function sendIncomeTaxValues(inputs: IncomeTaxInputs, messageId: string) {
    const source = current.value!.messages.find(message => message.id === messageId)!
    const context = source.economicStep!
    await sendMessage(
      `已提交所得税参数：所得税率 ${formatMoney(inputs.income_tax_rate * 100)}%。`,
      undefined,
      {
        economicRequest: {
          step: 'income_tax', scheme_id: context.schemeId,
          loan_result: context.loanResult!, cost_result: context.costResult!,
          revenue_tax_result: context.revenueTaxResult!, inputs,
        },
        sourceMessage: source, incomeTaxSnapshot: structuredClone(inputs),
      },
    )
  }

  async function sendCashFlowValues(inputs: CashFlowInputs, messageId: string) {
    const source = current.value!.messages.find(message => message.id === messageId)!
    const context = source.economicStep!
    await sendMessage(
      `已提交现金流量参数：资本金比例 ${formatMoney(inputs.equity_ratio * 100)}%。`,
      undefined,
      {
        economicRequest: {
          step: 'cash_flow', scheme_id: context.schemeId,
          loan_result: context.loanResult!, cost_result: context.costResult!,
          revenue_tax_result: context.revenueTaxResult!, income_tax_result: context.incomeTaxResult!,
          inputs,
        },
        sourceMessage: source, cashFlowSnapshot: structuredClone(inputs),
      },
    )
  }

  async function exportScheme(schemeId: string) {
    const scheme = current.value?.scenario.economicSchemes.find(item => item.id === schemeId)
    if (!scheme?.cashFlowResult) return
    const response = await fetch('http://127.0.0.1:8000/api/tools/calculate_economic_scheme/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scheme_name: scheme.name,
        loan_result: scheme.loanResult,
        cost_result: scheme.costResult,
        revenue_tax_result: scheme.revenueTaxResult,
        income_tax_result: scheme.incomeTaxResult,
        cash_flow_result: scheme.cashFlowResult,
      }),
    })
    if (!response.ok) throw new Error(`导出失败：HTTP ${response.status}`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `经济测算_${scheme.name}_${new Date().toISOString().slice(0, 10).replaceAll('-', '')}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    // 下载由浏览器异步接管，稍后释放，避免链接在文件读取前失效。
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  createConversation()
  return {
    conversations, currentId, current, loading, createConversation, selectConversation,
    renameConversation, deleteConversation, sendMessage, sendParameterValues, sendCostValues,
    sendRevenueTaxValues, sendIncomeTaxValues, sendCashFlowValues, exportScheme,
    startEconomicScheme, startNewEconomicScheme,
  }
}
