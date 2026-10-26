import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from heatcalc.agent.tools import ALL_TOOLS
from heatcalc.agent.formatting import DISPLAY_DECIMALS, format_result_for_display

load_dotenv()

# 全局LLM实例（只初始化一次）
llm = ChatOpenAI(
    model="deepseek-v4.1-flash",
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("API_BASE_URL"),
    temperature=0,
)
llm_with_tools = llm.bind_tools(ALL_TOOLS)

AGENT_RULES = SystemMessage(
    content=(
        "你是工业热源计算助手，根据用户已知的工况、预算和待求结果自行选择计算工具。"
        "用“根据蒸汽需求计算电费”“根据电费预算计算蒸汽流量”“计算熔盐储量”"
        "等实际目的描述功能，不要要求用户选择“正算”或“反算”，"
        "也不要在常规回复中标注这些分类。"
        "用户询问计算原理时，再按需解释计算过程；"
        "缺少必要参数或计算目标不明确时，询问具体条件。"
        "单独计算 COP 时，使用 calculate_heat_pump_cop，"
        "根据用户给出的热泵输出热功率和循环参数计算。"
        "根据风电或光伏功率计算蒸汽流量时，使用 calculate_steam_flow_from_renewable_power。"
        "风光转换效率 renewable_conversion_efficiency 与电热效率 electrical_efficiency 分别提供，"
        "缺少任一效率时先向用户补问，不得自行填入 1 或其他示例值。"
        "计算热泵时，循环介质、循环压力、各段端差和压降、设备效率及机械损失"
        "都必须有用户提供的数值或用户明确同意采用的数值。"
        "缺少这些参数时，先列出缺项和所需单位并向用户补问，不要调用热泵计算工具。"
        "不得擅自使用示例参数、默认参数，也不得将未提供的压降或机械损失填成零。"
        "COP 循环中的压力和压降使用 kPa，温度和端差使用 °C，机械损失使用 kW。"
        "计算工具返回的 raw_result 是原始计算结果，"
        "display_result 是换算单位并舍入后的展示结果。"
        "最终回答中的计算结果必须采用 display_result 的 value 和 unit，"
        f"固定显示 {DISPLAY_DECIMALS} 位小数，不足时补零，"
        "不得自行取整、省略小数或进一步舍入。"
        "需要继续调用计算工具时，使用 raw_result 中未舍入的原始数值，"
        "并按工具参数要求的单位传入，不要用展示值代替原始值参与后续计算。"
    )
)


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
        response = llm_with_tools.invoke([AGENT_RULES, *messages])
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
                content=json.dumps(
                    {"raw_result": raw_result, "display_result": display_result},
                    ensure_ascii=False,
                ),
                tool_call_id=tool_call['id']
            )
            messages.append(tool_message)

    return response.content, messages
