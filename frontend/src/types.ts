export interface UserProfile {
  displayName: string
}

export interface ParameterField {
  name: string
  label: string
  unit: string
  group: string
  advanced: boolean
  value: string | number | null
  required: boolean
  isDefault?: boolean
  inputType?: 'text' | 'select'
  options?: Array<{ value: string; label: string }>
  toToolFactor?: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  parameterForm?: ParameterField[]
}

export interface Conversation {
  id: string
  title: string
  hasCustomTitle: boolean
  messages: ChatMessage[]
}
