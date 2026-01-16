"""
快速修复数据库 URL 格式
自动检测并修复 .env 文件中的 DB_URL 格式
"""
import os
from pathlib import Path


def fix_database_url():
    """修复 .env 文件中的数据库 URL"""
    
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env 文件不存在！")
        print("   请创建 .env 文件，参考 .env.example")
        return False
    
    # 读取 .env 文件
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for line in lines:
        # 检查 DB_URL 配置
        if line.strip().startswith('DB_URL='):
            if 'postgresql+asyncpg://' not in line:
                # 需要修复
                old_line = line
                new_line = line
                
                # 处理 postgres:// 格式
                if 'postgres://' in line:
                    new_line = line.replace('postgres://', 'postgresql+asyncpg://')
                    modified = True
                # 处理 postgresql:// 格式
                elif 'postgresql://' in line:
                    new_line = line.replace('postgresql://', 'postgresql+asyncpg://')
                    modified = True
                
                if modified:
                    print(f"🔧 发现需要修复的配置:")
                    print(f"   旧: {old_line.strip()}")
                    print(f"   新: {new_line.strip()}")
                
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    if modified:
        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("\n✅ .env 文件已修复！")
        return True
    else:
        print("✅ .env 文件格式正确，无需修复")
        return True


def check_asyncpg_installed():
    """检查 asyncpg 是否已安装"""
    try:
        import asyncpg
        print(f"✅ asyncpg 已安装 (版本: {asyncpg.__version__})")
        return True
    except ImportError:
        print("❌ asyncpg 未安装！")
        print("   请运行: pip install asyncpg")
        return False


def test_config():
    """测试配置是否正确"""
    try:
        from app.config import settings
        
        print("\n📋 当前数据库配置:")
        print(f"   DB_URL: {settings.DB_URL}")
        
        if settings.DB_URL.startswith('postgresql+asyncpg://'):
            print("✅ 数据库 URL 格式正确！")
            return True
        else:
            print("❌ 数据库 URL 格式错误！")
            print("   当前格式:", settings.DB_URL.split('://')[0])
            print("   需要格式: postgresql+asyncpg://")
            return False
            
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def main():
    print("=" * 60)
    print("  CarFast 数据库配置修复工具")
    print("=" * 60)
    print()
    
    # 步骤1: 检查并修复 .env 文件
    print("步骤 1/3: 检查 .env 文件...")
    env_ok = fix_database_url()
    print()
    
    # 步骤2: 检查 asyncpg
    print("步骤 2/3: 检查 asyncpg 安装...")
    asyncpg_ok = check_asyncpg_installed()
    print()
    
    # 步骤3: 测试配置
    print("步骤 3/3: 测试配置加载...")
    config_ok = test_config()
    print()
    
    # 总结
    print("=" * 60)
    print("  修复结果")
    print("=" * 60)
    
    all_ok = env_ok and asyncpg_ok and config_ok
    
    if all_ok:
        print("🎉 所有检查通过！可以启动应用了！")
        print()
        print("运行命令:")
        print("  uvicorn main:app --reload")
        print()
    else:
        print("⚠️  仍有问题需要解决:")
        if not env_ok:
            print("  - .env 文件问题")
        if not asyncpg_ok:
            print("  - asyncpg 未安装")
        if not config_ok:
            print("  - 配置格式错误")
        print()
        print("请根据上面的提示修复问题")
        print()
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
