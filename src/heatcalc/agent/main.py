import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from heatcalc.agent.tools import ALL_TOOLS
from heatcalc.agent.formatting import format_result_for_display

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-v4.1-flash",
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("API_BASE_URL"),
    temperature=0,
)

llm_with_tools = llm.bind_tools(ALL_TOOLS)

messages = []

print("=== 电加热器成本计算Agent ===")
print("输入 'exit' 或 'quit' 退出\n")

while True:
    user_input = input("用户: ").strip()
    if user_input.lower() in ['exit', 'quit', '退出']:
        print("再见！")
        break

    if not user_input:
        continue

    messages.append(HumanMessage(content=user_input))

    # Agent推理循环（和之前一样）
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

    print(f"\nAgent: {response.content}\n")


