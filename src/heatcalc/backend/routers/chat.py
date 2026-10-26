from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["chat"])


# 请求体模型
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{"role": "user", "content": "..."}, ...]
    parameter_values: dict[str, Any] | None = None


# 响应体模型
class ChatResponse(BaseModel):
    response: str
    parameter_form: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    接收用户消息和历史对话，调用Agent返回结果

    req.parameter_values 用于接收前端可填写参数表提交的值。
    """

    from heatcalc.agent.agent_core import chat
    from langchain_core.messages import HumanMessage, AIMessage

    # 1. 把前端传来的字典历史转成 LangChain Message 对象
    messages = []
    for msg in req.history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # 当前的 req.message 单独传入，agent_core 会将其追加到历史消息中。
    reply_text, updated_messages, parameter_form = chat(
        req.message,
        messages,
        parameter_values=req.parameter_values,
    )

    # 3. 返回 AI 回复
    return ChatResponse(response=reply_text, parameter_form=parameter_form)
