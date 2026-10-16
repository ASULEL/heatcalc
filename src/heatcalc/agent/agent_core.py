import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
from heatcalc.agent.tools import ALL_TOOLS
from heatcalc.agent.formatting import format_result_for_display

load_dotenv()

# 全局LLM实例（只初始化一次）
llm = ChatOpenAI(
    model="deepseek-v4.1-flash",
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("API_BASE_URL"),
    temperature=0,
)
llm_with_tools = llm.bind_tools(ALL_TOOLS)


def chat(user_input: str, messages: list) -> tuple[str, list]:
    """
    Agent核心逻辑：接收用户输入，返回Agent回复

    :param user_input: 用户输入的文本
    :param messages: 对话历史（LangChain的Message对象列表）
    :return: (agent回复文本, 更新后的messages列表)
    """
    messages.append(HumanMessage(content=user_input))

    max_iterations = 5
    for i in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            tool_func = next((t for t in ALL_TOOLS if t.name == tool_call['name']), None)
            if tool_func is None:
                continue

            raw_result = tool_func.invoke(tool_call['args'])
            display_result = format_result_for_display(raw_result)

            tool_message = ToolMessage(
                content=str(display_result),
                tool_call_id=tool_call['id']
            )
            messages.append(tool_message)

    return response.content, messages