export interface UserProfile {
  displayName: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface Conversation {
  id: string
  title: string
  hasCustomTitle: boolean
  messages: ChatMessage[]
}
