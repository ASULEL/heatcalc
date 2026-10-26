import { computed, ref, shallowReactive } from 'vue'
import type { Conversation, ParameterField } from '../types'

export function useConversations() {
  const conversations = ref<Conversation[]>([])
  const currentId = ref<string | null>(null)
  const pendingRequests = shallowReactive(new Map<string, AbortController>())

  const current = computed(() => conversations.value.find((c) => c.id === currentId.value))
  const loading = computed(() => currentId.value !== null && pendingRequests.has(currentId.value))

  function createConversation() {
    const id = crypto.randomUUID()
    conversations.value.push({ id, title: '新对话', hasCustomTitle: false, messages: [] })
    currentId.value = id
    return id
  }

  function selectConversation(id: string) {
    if (conversations.value.some((c) => c.id === id)) {
      currentId.value = id
    }
  }

  function renameConversation(id: string, title: string) {
    const conversation = conversations.value.find((c) => c.id === id)
    const name = title.trim()
    if (!conversation || !name) return

    conversation.title = name
    conversation.hasCustomTitle = true
  }

  function deleteConversation(id: string) {
    const index = conversations.value.findIndex((c) => c.id === id)
    if (index === -1) return

    pendingRequests.get(id)?.abort()
    pendingRequests.delete(id)
    conversations.value.splice(index, 1)

    if (currentId.value !== id) return

    const next = conversations.value[index] ?? conversations.value[index - 1]
    if (next) {
      currentId.value = next.id
    } else {
      createConversation()
    }
  }

  async function sendMessage(text: string, parameterValues?: Record<string, string | number>) {
    const message = text.trim()
    if (!message) return
    if (!current.value) createConversation()

    // 请求始终使用发起时的对话，后续切换选中项不会改变回复归属。
    const conversation = current.value
    if (!conversation || pendingRequests.has(conversation.id)) return

    const history = conversation.messages.map(({ role, content }) => ({ role, content }))
    conversation.messages.push({ id: crypto.randomUUID(), role: 'user', content: message })
    if (conversation.messages.length === 1 && !conversation.hasCustomTitle) {
      conversation.title = message.slice(0, 30) + (message.length > 30 ? '...' : '')
    }

    const controller = new AbortController()
    pendingRequests.set(conversation.id, controller)
    const canAppendReply = () =>
      !controller.signal.aborted && conversations.value.some((c) => c.id === conversation.id)

    try {
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history, parameter_values: parameterValues }),
        signal: controller.signal,
      })
      if (!res.ok) throw new Error(`请求失败：HTTP ${res.status}`)

      const data = await res.json()
      if (typeof data.response !== 'string') throw new Error('回复格式无效')
      if (!canAppendReply()) return

      conversation.messages.push({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response,
        parameterForm: Array.isArray(data.parameter_form) ? data.parameter_form : undefined,
      })
    } catch (err) {
      if (!canAppendReply()) return
      console.error('发送消息失败:', err)
      conversation.messages.push({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '抱歉，请求失败，请稍后重试。',
      })
    } finally {
      pendingRequests.delete(conversation.id)
    }
  }

  async function sendParameterValues(fields: ParameterField[], values: Record<string, string>) {
    const summary = fields
      .map((field) => `${field.label}（${field.unit}）：${values[field.name] || '未填写'}`)
      .join('\n')
    const toolValues = Object.fromEntries(
      fields.map((field) => {
        const value = values[field.name]
        const factor = field.toToolFactor || 1
        return [field.name, value === '' ? value : factor === 1 ? value : Number(value) * factor]
      }),
    )
    await sendMessage(`已提交参数：\n${summary}`, toolValues)
  }

  createConversation()

  return {
    conversations,
    currentId,
    current,
    loading,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
    sendParameterValues,
  }
}
