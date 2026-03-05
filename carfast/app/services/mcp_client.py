# app/services/mcp_client.py
import os
import logging
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class CarFastMCPClient:
    """
    CarFast 标准 MCP 客户端
    通过标准输入输出 (stdio) 拉起并连接独立的 MCP Server。
    """

    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.session = None
        self._exit_stack = AsyncExitStack()

    async def connect(self):
        """拉起子进程并建立通信通道"""
        logger.info(f"[MCP Client] 🚀 正在拉起 MCP Server: {self.server_script_path}")

        # 🌟 核心修复：强制 Windows 子进程的输入输出管道使用 UTF-8 编码！
        mcp_env = os.environ.copy()
        mcp_env["PYTHONIOENCODING"] = "utf-8"
        mcp_env["PYTHONUTF8"] = "1"

        # 定义拉起 Server 的命令
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path],
            env=mcp_env  # 🌟 把带有 UTF-8 基因的环境变量传进去
        )

        # 1. 建立基于 stdio 的底层传输管道
        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
        read_stream, write_stream = stdio_transport

        # 2. 在管道之上建立 MCP 会话层
        self.session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))

        # 3. 初始化握手
        await self.session.initialize()
        logger.info("[MCP Client] 🟢 MCP 握手成功！通道已建立。")

    async def list_tools(self):
        """向 Server 询问：你能干啥？"""
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """命令 Server 执行特定的工具"""
        logger.info(f"[MCP Client] 🛠️ 发起远程工具调用: {name} | 参数: {arguments}")
        result = await self.session.call_tool(name, arguments)

        # 解析 Server 返回的 Content
        # MCP 协议规定返回的是一个列表，我们取第一个 TextContent 的文本
        return result.content[0].text

    async def close(self):
        """优雅关闭通道，清理子进程"""
        try:
            await self._exit_stack.aclose()
        except BaseException:  # 🌟 改成 BaseException，连 CancelledError 一起吞掉
            pass
        logger.info("[MCP Client] 🔴 MCP 通道已关闭。")