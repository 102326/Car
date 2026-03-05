import asyncio
import json
from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server

# 1. 初始化一个 MCP Server 实例
app = Server("carfast-finance-mcp")


# 2. 向外暴露能力 (List Tools)：告诉大模型我能干什么、需要什么参数
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="calculate_car_loan",
            description="金融工具：计算汽车贷款的等额本息月供",
            inputSchema={
                "type": "object",
                "properties": {
                    "principal": {"type": "number", "description": "贷款本金(元)"},
                    "months": {"type": "integer", "description": "分期期数(月)"},
                    "annual_rate": {"type": "number", "description": "年化利率(例如 0.05 表示 5%)"}
                },
                "required": ["principal", "months", "annual_rate"]
            }
        )
    ]


# 3. 核心执行逻辑 (Call Tool)：当大模型决定调用时，执行具体代码
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "calculate_car_loan":
        principal = arguments.get("principal", 0)
        months = arguments.get("months", 0)
        annual_rate = arguments.get("annual_rate", 0.0)

        if months <= 0:
            return [types.TextContent(type="text", text="错误: 期数必须大于0")]

        # 等额本息计算逻辑
        monthly_rate = annual_rate / 12
        if monthly_rate == 0:
            monthly_payment = principal / months
        else:
            monthly_payment = principal * monthly_rate * ((1 + monthly_rate) ** months) / (
                        ((1 + monthly_rate) ** months) - 1)

        total_payment = monthly_payment * months
        total_interest = total_payment - principal

        # 构造返回给大模型的结构化结果
        result = {
            "status": "success",
            "monthly_payment": round(monthly_payment, 2),
            "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2)
        }

        # MCP 规范：返回内容必须包装在特定的 Content 对象中
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
    else:
        raise ValueError(f"未知的工具调用: {name}")


# 4. 启动 Server，使用 stdio (标准输入输出) 进行通信
async def main():
    # 使用 stdio_server 建立基于管道的通信通道
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())