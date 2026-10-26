import json
import os
from typing import Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from heatcalc.agent.tools import ALL_TOOLS
from heatcalc.agent.formatting import DISPLAY_DECIMALS, format_result_for_display
from heatcalc.agent.parameter_specs import build_parameter_form

load_dotenv()


@tool
def request_parameter_form(
        tool_name: str,
        known_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """请求前端显示某个计算工具的可填写参数表。"""
    return {
        "tool_name": tool_name,
        "known_values": known_values or {},
    }

# 全局LLM实例（只初始化一次）
llm = ChatOpenAI(
    model="deepseek-v4.1-flash",
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("API_BASE_URL"),
    temperature=0,
)
llm_with_tools = llm.bind_tools([*ALL_TOOLS, request_parameter_form])

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
        "当用户描述了计算目标但没有提供全部必要参数时，先不要调用计算工具。"
        "先识别最匹配的计算工具，然后调用 request_parameter_form 请求前端显示可填写参数表。"
        "调用 request_parameter_form 时，tool_name 必须填写实际要使用的计算工具名，"
        "known_values 填入已经从用户描述或历史对话中得到的参数。"
        "参数表由前端显示，回复正文不要生成 Markdown 参数表，也不要展示内部工具参数名。"
        "未在参数表中提交的缺失参数不得使用默认值、示例值或自行猜测；"
        "参数表中已经提交的 Excel 示例值视为当前输入，空白字段仍需继续询问。"
        "用户补充参数后，将新参数与历史参数合并，只继续请求仍然缺少的参数表字段。"
        "所有必要参数齐全后，再调用对应的计算工具。"
        "如果用户一次性提供了全部参数，可以直接调用工具，不需要先展示参数表。"
        "计算热泵时，循环介质、循环压力、各段端差和压降、设备效率及机械损失"
        "都必须出现在用户消息或已提交的参数表中。"
        "缺少这些参数时，先列出缺项和所需单位并向用户补问，不要调用热泵计算工具。"
        "不得擅自使用示例参数、默认参数，也不得将未提供的压降或机械损失填成零。"
        "COP 循环中的压力和压降使用 kPa，温度和端差使用 °C，机械损失使用 kW。"
        "前端参数表可以按 Excel 显示 MPa 和 MWt，提交时会转换为工具所需的 kPa 和 kW。"
        "计算工具返回的 raw_result 是原始计算结果，"
        "display_result 是换算单位并舍入后的展示结果。"
        "最终回答中的计算结果必须采用 display_result 的 value 和 unit，"
        f"固定显示 {DISPLAY_DECIMALS} 位小数，不足时补零，"
        "不得自行取整、省略小数或进一步舍入。"
        "需要继续调用计算工具时，使用 raw_result 中未舍入的原始数值，"
        "并按工具参数要求的单位传入，不要用展示值代替原始值参与后续计算。"
    )
)


def chat(
        user_input: str,
        messages: list,
        parameter_values: dict[str, Any] | None = None,
) -> tuple[str, list, list[dict[str, Any]]]:
    """
    Agent核心逻辑：接收用户输入，返回Agent回复

    :param user_input: 用户输入的文本
    :param messages: 对话历史（LangChain的Message对象列表）
    :param parameter_values: 前端参数表提交的内部参数值
    :return: (agent回复文本, 更新后的messages列表, 前端参数表)
    """
    if parameter_values:
        user_input = (
            f"{user_input}\n"
            "用户刚刚通过参数表提交了以下参数，请按工具参数名读取：\n"
            f"{json.dumps(parameter_values, ensure_ascii=False)}"
        )
    messages.append(HumanMessage(content=user_input))

    max_iterations = 5
    parameter_form: list[dict[str, Any]] = []
    for i in range(max_iterations):
        response = llm_with_tools.invoke([AGENT_RULES, *messages])
        messages.append(response)

        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            if tool_call['name'] == request_parameter_form.name:
                form_request = request_parameter_form.invoke(tool_call['args'])
                target_tool = next(
                    (candidate for candidate in ALL_TOOLS if candidate.name == form_request["tool_name"]),
                    None,
                )
                parameter_form = build_parameter_form(
                    target_tool,
                    form_request.get("known_values"),
                ) if target_tool else []
                messages.append(
                    ToolMessage(
                        content=json.dumps(
                            {"parameter_form_requested": bool(parameter_form)},
                            ensure_ascii=False,
                        ),
                        tool_call_id=tool_call['id'],
                    )
                )
                continue

            tool_func = next((t for t in ALL_TOOLS if t.name == tool_call['name']), None)
            if tool_func is None:
                continue

            parameter_form = []
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

    return response.content, messages, parameter_form
