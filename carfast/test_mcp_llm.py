import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage  # 🌟 必须导入这个，用于存放工具的执行结果
from app.services.mcp_manager import MCPManager


async def test_llm_with_mcp():
    # 1. 初始化你的大模型
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ.get("DEEPSEEK_API_KEY", "填入你的API_KEY"),  # 记得确保这里有正确的 Key
        base_url="https://api.deepseek.com",
        max_tokens=1024
    )

    # 2. 拉起 MCP 武器库
    finance_server_path = os.path.join(os.getcwd(), "mcp_servers", "finance_server.py")
    tavily_server_path = os.path.join(os.getcwd(), "mcp_servers", "tavily_search_server.py")
    manager = MCPManager([finance_server_path, tavily_server_path])

    try:
        await manager.connect_all()
        mcp_tools = await manager.get_all_langchain_tools()

        # 把 MCP 工具直接“绑”在大模型身上
        llm_with_tools = llm.bind_tools(mcp_tools)

        print("\n" + "=" * 50)
        user_query = "我想买一辆车，贷25万，分36期，年利率4.5%，帮我算算月供。另外，帮我上网查查今天雷军发了什么微博。"
        print(f"👨‍🦰 用户说: {user_query}")
        print("=" * 50 + "\n")

        print("🤖 大模型正在思考并决定调用什么工具...")

        try:
            # 🌟 关键修改 1：我们不能只传字符串，必须构造一个“消息列表”，因为后续要把工具结果塞进去
            messages = [("user", user_query)]

            # 第一次调用大模型 (索要工具清单)
            ai_msg = await llm_with_tools.ainvoke(messages)

            # 🌟 关键修改 2：把大模型决定调用工具的这个“念头”，存入历史记录
            messages.append(ai_msg)

            # 看看大模型决定干什么
            if ai_msg.tool_calls:
                print(f"🎯 大模型决定调用 {len(ai_msg.tool_calls)} 个工具！")

                # 🌟 关键修改 3：真正去遍历并执行每一个工具！
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    tool_id = tool_call['id']  # LangChain 需要这个 ID 来对齐结果

                    print(f"\n   ⚙️ 正在通过 MCP 管道执行工具: {tool_name}...")
                    print(f"   📦 提取参数: {tool_args}")

                    # 从我们动态生成的工具列表中，找到对应的工具对象
                    selected_tool = next((t for t in mcp_tools if t.name == tool_name), None)

                    if selected_tool:
                        # 真正执行！(这里底层会通过 stdio 发送 JSON-RPC 给子进程)
                        tool_result = await selected_tool.ainvoke(tool_args)
                        print(f"   ✅ 工具返回成功 (截断展示): {str(tool_result)[:60]}...")

                        # 把工具返回的结果封装成 ToolMessage，并塞入消息列表
                        messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))

                # 🌟 关键修改 4：带着工具计算好的结果，第二次去问大模型！
                print("\n🧠 大模型已经拿到所有数据，正在生成最终人类语言回答...\n")
                final_msg = await llm_with_tools.ainvoke(messages)

                print("=" * 50)
                print("🎉 最终回答:\n")
                print(final_msg.content)
                print("=" * 50)

            else:
                print("大模型觉得不需要用工具，直接回答了：", ai_msg.content)

        except Exception as e:
            print(f"\n❌ 破案了！执行过程发生异常: {e}\n")

    finally:
        await manager.close_all()


if __name__ == "__main__":
    asyncio.run(test_llm_with_mcp())