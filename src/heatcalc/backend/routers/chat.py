from typing import Any

from fastapi import APIRouter, HTTPException
from openai import APITimeoutError
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["chat"])


# 请求体模型
class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{"role": "user", "content": "..."}, ...]
    parameter_values: dict[str, Any] | None = None
    calculation_results: list[dict[str, Any]] = Field(default_factory=list)  # 当前对话方案数据


# 响应体模型
class ChatResponse(BaseModel):
    response: str
    parameter_form: list[dict[str, Any]] = Field(default_factory=list)
    calculation_results: list[dict[str, Any]] = Field(default_factory=list)  # 本轮生成的计算数据


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
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
    try:
        reply_text, _, parameter_form, calculation_results = chat(
            req.message,
            messages,
            parameter_values=req.parameter_values,
            calculation_results=req.calculation_results,
        )
    except APITimeoutError as error:
        raise HTTPException(status_code=504, detail="模型响应超时，请重试。") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    # 3. 返回 AI 回复
    return ChatResponse(
        response=reply_text,
        parameter_form=parameter_form,
        calculation_results=calculation_results,
    )
