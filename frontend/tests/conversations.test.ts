import assert from 'node:assert/strict'
import { test, type TestContext } from 'node:test'
import { useConversations } from '../src/composables/useConversations.ts'
import type { ParameterField } from '../src/types.ts'

interface PendingRequest {
  body: {
    message: string
    history: { role: string; content: string }[]
    parameter_values?: Record<string, string | number>
  }
  signal: AbortSignal | null | undefined
  resolve: (response: Response) => void
  reject: (error: Error) => void
}

function mockRequests(t: TestContext) {
  const requests: PendingRequest[] = []
  t.mock.method(globalThis, 'fetch', (_url: unknown, init?: RequestInit) =>
    new Promise<Response>((resolve, reject) => {
      requests.push({
        body: JSON.parse(String(init?.body)),
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
