import asyncio
import os
import json
from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server
from tavily import TavilyClient

# 1. 注册新 Server
app = Server("carfast-tavily-mcp")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="tavily_web_search",
            description="专为 AI 设计的实时联网搜索引擎。用于获取最新的新闻、报价、政策等实时数据。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "tavily_web_search":
        query = arguments.get("query")

        # 从环境变量或直接写死（为了测试方便，你可以先直接把 tvly-xxx 写在这里）
        api_key = os.environ.get("TAVILY_API_KEY", "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")

        if not api_key or api_key == "你的_TVLY_API_KEY_粘贴在这里":
            return [types.TextContent(type="text", text="系统错误: 未配置 Tavily API Key")]

        try:
            # 瞬间调用大模型专用的搜索 API
            client = TavilyClient(api_key=api_key)
            response = client.search(query, search_depth="basic", max_results=3)

            results = response.get("results", [])
            if not results:
                return [types.TextContent(type="text", text="未找到相关实时信息。")]

            # 组装为干净的 Markdown
            formatted_text = "【Tavily 实时联网检索结果】\n"
            for r in results:
                formatted_text += f"标题: {r.get('title')}\n内容摘要: {r.get('content')}\n来源: {r.get('url')}\n\n"

            return [types.TextContent(type="text", text=formatted_text)]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Tavily API 调用失败: {str(e)}")]
    else:
        raise ValueError(f"未知的工具: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())