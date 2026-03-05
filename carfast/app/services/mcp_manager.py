# app/services/mcp_manager.py

import logging
from typing import List, Dict, Any
from langchain_core.tools import StructuredTool
from pydantic import create_model, Field

# 引入我们上一节课写的底层客户端
from app.services.mcp_client import CarFastMCPClient

logger = logging.getLogger(__name__)


class MCPManager:
    """
    MCP 集群管理器与 LangChain 适配器。
    负责管理多个 MCP Server，并将它们的能力动态转化为 LangChain 工具。
    """

    def __init__(self, server_paths: List[str]):
        self.server_paths = server_paths
        self.clients: List[CarFastMCPClient] = []

    async def connect_all(self):
        """拉起并连接所有注册的 MCP Server"""
        for path in self.server_paths:
            client = CarFastMCPClient(path)
            await client.connect()
            self.clients.append(client)
        logger.info(f"[MCP Manager] 成功接入 {len(self.clients)} 个 MCP 微服务！")

    async def get_all_langchain_tools(self) -> List[StructuredTool]:
        """
        核心魔术：向所有 Server 询问能力，并动态转换为 LangChain 工具！
        """
        langchain_tools = []

        for client in self.clients:
            # 1. 询问 MCP Server：你能干什么？
            mcp_tools = await client.list_tools()

            for mcp_tool in mcp_tools:
                # 2. 将 MCP 的 JSON Schema 动态编译为 Pydantic 数据模型
                # 这是因为 LangChain 强制要求工具输入必须是 Pydantic 格式
                fields = {}
                properties = mcp_tool.inputSchema.get("properties", {})
                required = mcp_tool.inputSchema.get("required", [])

                for prop_name, prop_info in properties.items():
                    prop_type = Any  # 默认类型
                    if prop_info.get("type") == "string":
                        prop_type = str
                    elif prop_info.get("type") in ["integer", "number"]:
                        prop_type = float

                    # 判断是否必填
                    default_value = ... if prop_name in required else None
                    fields[prop_name] = (prop_type,
                                         Field(default=default_value, description=prop_info.get("description", "")))

                # 动态生成 Pydantic Model 类
                DynamicInputModel = create_model(f"{mcp_tool.name}Input", **fields)

                # 3. 构造真正的执行函数 (闭包闭环)
                # 当大模型决定调用这个工具时，实际会执行这个 wrapper 函数
                async def _tool_caller(client=client, name=mcp_tool.name, **kwargs):
                    logger.info(f"[大模型触发 MCP 调用] 工具: {name}, 参数: {kwargs}")
                    return await client.call_tool(name, kwargs)

                # 4. 包装成 LangChain 标准工具
                lc_tool = StructuredTool.from_function(
                    coroutine=_tool_caller,
                    name=mcp_tool.name,
                    description=mcp_tool.description,
                    args_schema=DynamicInputModel
                )
                langchain_tools.append(lc_tool)

        logger.info(f"[MCP Manager] 已动态装载 {len(langchain_tools)} 个大模型原生工具。")
        return langchain_tools

    async def close_all(self):
        """优雅关闭所有 MCP 通道"""
        for client in self.clients:
            await client.close()
        self.clients.clear()  # 清空列表