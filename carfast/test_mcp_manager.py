import asyncio
import os
from app.services.mcp_manager import MCPManager


async def test_manager():
    # 1. 准备你的 MCP Server 路径 (把我们写好的两个武器都装上去)
    finance_server_path = os.path.join(os.getcwd(), "mcp_servers", "finance_server.py")
    tavily_server_path = os.path.join(os.getcwd(), "mcp_servers",
                                      "tavily_search_server.py")  # 如果你用的是免费版，就换成 web_search_server.py

    # 2. 实例化你的管理器
    manager = MCPManager([finance_server_path, tavily_server_path])

    try:
        # 3. 统一点火，拉起所有子进程
        print("🚀 正在拉起所有 MCP 微服务集群...")
        await manager.connect_all()

        # 4. 核心见证：提取转换后的 LangChain 工具
        print("\n⚙️ 正在向 MCP 集群索要工具清单并动态编译...")
        tools = await manager.get_all_langchain_tools()

        print(f"\n✅ 成功锻造了 {len(tools)} 把大模型专属武器！\n")
        print("=" * 50)

        # 5. 打印出来看看它们长什么样
        for t in tools:
            print(f"🔧 工具名称: {t.name}")
            print(f"📝 工具描述: {t.description}")
            print(f"📦 严谨的参数 Schema (供大模型阅读):")
            # 打印 Pydantic 生成的 JSON Schema
            print(t.args_schema.schema_json(indent=2))
            print("-" * 50)

    except Exception as e:
        print(f"❌ 发生异常: {e}")

    finally:
        # 6. 统一熄火，安全销毁进程
        await manager.close_all()
        print("\n🔴 所有 MCP 通道已安全关闭。")


if __name__ == "__main__":
    asyncio.run(test_manager())