#!/usr/bin/env python3
# start_agent.py
"""
智能购车管家 Agent 快速启动脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))


async def interactive_chat():
    """
    交互式对话模式
    """
    from app.agents.smart_car_concierge import create_smart_car_concierge
    
    print("\n" + "="*80)
    print("🚗 易车智能购车管家 - 交互式对话模式")
    print("="*80)
    print("\n提示:")
    print("  - 输入 'exit' 或 'quit' 退出")
    print("  - 输入 'reset' 重置对话")
    print("  - 输入 'profile' 查看当前用户画像")
    print("\n" + "="*80 + "\n")
    
    # 创建 Agent
    agent = create_smart_car_concierge()
    session_state = None
    
    while True:
        try:
            # 获取用户输入
            user_input = input("👤 您: ").strip()
            
            # 退出命令
            if user_input.lower() in ['exit', 'quit', '退出']:
                print("\n感谢使用易车智能购车管家！再见！👋\n")
                break
            
            # 重置对话
            if user_input.lower() in ['reset', '重置']:
                session_state = None
                print("\n✅ 对话已重置\n")
                continue
            
            # 查看用户画像
            if user_input.lower() in ['profile', '画像']:
                if session_state:
                    profile = session_state.get("user_profile", {})
                    print("\n📊 当前用户画像:")
                    print(f"  - 预算: {profile.get('budget_min', '未知')}-{profile.get('budget_max', '未知')}万")
                    print(f"  - 城市: {profile.get('city', '未知')}")
                    print(f"  - 偏好: {profile.get('preferences', {})}")
                    print(f"  - 购车意图: {profile.get('purchase_intent', '未知')}")
                    print()
                else:
                    print("\n⚠️ 暂无用户画像数据\n")
                continue
            
            # 空输入
            if not user_input:
                continue
            
            # 执行对话
            print("\n🤖 AI: ", end="", flush=True)
            result = await agent.chat(user_input, session_state)
            
            # 打印回复
            print(result["answer"])
            print()
            
            # 更新会话状态
            session_state = result["state"]
            
        except KeyboardInterrupt:
            print("\n\n感谢使用易车智能购车管家！再见！👋\n")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")
            import traceback
            traceback.print_exc()


async def single_query(message: str):
    """
    单次查询模式
    """
    from app.agents.smart_car_concierge import create_smart_car_concierge
    
    print(f"\n👤 用户: {message}\n")
    
    agent = create_smart_car_concierge()
    result = await agent.chat(message)
    
    print(f"🤖 AI: {result['answer']}\n")
    print(f"📊 用户画像: {result['metadata']['user_profile']}\n")


async def run_demo():
    """
    演示模式：预设对话
    """
    from app.agents.smart_car_concierge import create_smart_car_concierge
    
    print("\n" + "="*80)
    print("🎬 演示模式：智能购车管家对话示例")
    print("="*80 + "\n")
    
    agent = create_smart_car_concierge()
    
    demo_conversations = [
        "你好",
        "我预算20万左右，想买辆家用SUV",
        "比亚迪秦PLUS怎么样？",
        "这款车有什么优惠吗？",
        "谢谢"
    ]
    
    session_state = None
    
    for i, message in enumerate(demo_conversations, 1):
        print(f"【对话 {i}】")
        print(f"👤 用户: {message}\n")
        
        result = await agent.chat(message, session_state)
        
        print(f"🤖 AI: {result['answer']}\n")
        print(f"📊 意图: {result['metadata'].get('intent', '未知')}\n")
        print("-" * 80 + "\n")
        
        session_state = result["state"]
        
        # 暂停一下，模拟真实对话
        await asyncio.sleep(0.5)
    
    print("="*80)
    print("演示完成！")
    print("="*80 + "\n")


def print_usage():
    """打印使用说明"""
    print("""
使用方法:

1. 交互式对话模式（推荐）:
   python start_agent.py

2. 单次查询模式:
   python start_agent.py --query "20万左右的SUV有哪些推荐"

3. 演示模式:
   python start_agent.py --demo

4. 启动 API 服务:
   python start_agent.py --server

5. 运行测试:
   python start_agent.py --test
""")


async def start_server():
    """启动 FastAPI 服务"""
    import uvicorn
    
    print("\n" + "="*80)
    print("🚀 启动易车智能购车管家 API 服务")
    print("="*80)
    print("\nAPI 文档: http://localhost:8000/docs")
    print("健康检查: http://localhost:8000/api/agent/health")
    print("\n按 Ctrl+C 停止服务\n")
    print("="*80 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


async def run_tests():
    """运行测试"""
    print("\n" + "="*80)
    print("🧪 运行测试套件")
    print("="*80 + "\n")
    
    import subprocess
    result = subprocess.run([sys.executable, "test_agent.py"])
    
    return result.returncode


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="易车智能购车管家 Agent")
    parser.add_argument("--query", "-q", type=str, help="单次查询模式")
    parser.add_argument("--demo", "-d", action="store_true", help="演示模式")
    parser.add_argument("--server", "-s", action="store_true", help="启动 API 服务")
    parser.add_argument("--test", "-t", action="store_true", help="运行测试")
    
    args = parser.parse_args()
    
    if args.query:
        # 单次查询模式
        asyncio.run(single_query(args.query))
    elif args.demo:
        # 演示模式
        asyncio.run(run_demo())
    elif args.server:
        # 启动服务
        asyncio.run(start_server())
    elif args.test:
        # 运行测试
        exit_code = asyncio.run(run_tests())
        sys.exit(exit_code)
    else:
        # 默认：交互式对话模式
        try:
            asyncio.run(interactive_chat())
        except KeyboardInterrupt:
            print("\n\n感谢使用！👋\n")


if __name__ == "__main__":
    main()
