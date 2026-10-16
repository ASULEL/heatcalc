from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["chat"])


# 请求体模型
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{"role": "user", "content": "..."}, ...]


# 响应体模型
class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    接收用户消息和历史对话，调用Agent返回结果

    TODO: 这里是你需要填写的部分
    1. 把 req.history 和 req.message 转换成你的 agent_core.chat() 需要的格式
    2. 调用 agent_core.chat(messages)
    3. 提取返回结果，封装成 ChatResponse 返回

    提示：
    - req.history 是个列表，每个元素是 {"role": "user"|"assistant", "content": "..."}
    - 你需要把当前的 req.message 也加到消息列表里（作为最后一条用户消息）
    - agent_core.chat() 的返回值格式你自己最清楚，按实际情况提取文本
    """

    # ===== 你的代码写在这里 =====
    # 示例伪代码（删掉这段，换成真实调用）：
    from heatcalc.agent.agent_core import chat
    from langchain_core.messages import HumanMessage, AIMessage

    # 1. 把前端传来的字典历史转成 LangChain Message 对象
    messages = []
    for msg in req.history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # 2. 调用 Agent（注意：当前的 req.message 单独传，不用加到 messages 里）
    reply_text, updated_messages = chat(req.message, messages)

    # 3. 返回 AI 回复
    return ChatResponse(response=reply_text)
