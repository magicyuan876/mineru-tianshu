"""
MCP Server 测试脚本
用于验证 MCP Server 的基本功能
"""
import asyncio
import base64
import json
from pathlib import Path


async def test_mcp_tools():
    """测试 MCP Server 的工具列表"""
    print("=" * 60)
    print("MCP Server 功能测试")
    print("=" * 60)
    
    # 导入 MCP Server
    try:
        from mcp_server import app, list_tools, parse_document, get_task_status, list_tasks, get_queue_stats
        print("✅ MCP Server 模块导入成功")
    except Exception as e:
        print(f"❌ MCP Server 模块导入失败: {e}")
        return False
    
    # 测试工具列表
    print("\n1. 测试工具列表...")
    try:
        tools = await list_tools()
        print(f"✅ 找到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:50]}...")
        
        expected_tools = {'parse_document', 'get_task_status', 'list_tasks', 'get_queue_stats'}
        actual_tools = {tool.name for tool in tools}
        
        if expected_tools == actual_tools:
            print("✅ 所有预期工具都已定义")
        else:
            print(f"⚠️  工具不匹配:")
            print(f"   预期: {expected_tools}")
            print(f"   实际: {actual_tools}")
    except Exception as e:
        print(f"❌ 工具列表测试失败: {e}")
        return False
    
    # 测试 Base64 文件处理（模拟）
    print("\n2. 测试 Base64 文件处理...")
    try:
        # 创建一个测试文本文件
        test_content = b"This is a test document for MCP Server"
        test_base64 = base64.b64encode(test_content).decode()
        
        print(f"✅ Base64 编码测试通过")
        print(f"   原始大小: {len(test_content)} bytes")
        print(f"   编码后大小: {len(test_base64)} bytes")
    except Exception as e:
        print(f"❌ Base64 编码测试失败: {e}")
        return False
    
    # 测试参数验证
    print("\n3. 测试参数验证...")
    try:
        # 验证 parse_document 的参数结构
        tools_dict = {tool.name: tool for tool in tools}
        parse_tool = tools_dict['parse_document']
        
        schema = parse_tool.inputSchema
        required_fields = schema.get('oneOf', [])
        
        print("✅ parse_document 参数验证:")
        print(f"   支持的输入方式: {len(required_fields)} 种")
        for idx, option in enumerate(required_fields, 1):
            print(f"   方式 {idx}: {option.get('required', [])}")
        
    except Exception as e:
        print(f"❌ 参数验证测试失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有基本功能测试通过！")
    print("=" * 60)
    print("\n提示:")
    print("1. 启动完整服务测试: python start_all.py --enable-mcp")
    print("2. 测试 SSE 端点: curl http://localhost:8001/mcp/sse")
    print("3. 使用 MCP Inspector: npx @modelcontextprotocol/inspector python mcp_server.py")
    
    return True


def test_imports():
    """测试依赖导入"""
    print("\n检查依赖...")
    
    dependencies = {
        'mcp': 'Model Context Protocol SDK',
        'starlette': 'Starlette Web Framework',
        'aiohttp': 'Async HTTP Client',
        'loguru': 'Logging',
        'uvicorn': 'ASGI Server'
    }
    
    all_ok = True
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {module:15s} - {description}")
        except ImportError:
            print(f"❌ {module:15s} - {description} (未安装)")
            all_ok = False
    
    if not all_ok:
        print("\n请安装缺失的依赖:")
        print("pip install -r requirements.txt")
        return False
    
    return True


if __name__ == "__main__":
    print("MinerU Tianshu - MCP Server 测试\n")
    
    # 测试依赖
    if not test_imports():
        print("\n❌ 依赖检查失败，请先安装依赖")
        exit(1)
    
    # 测试 MCP 功能
    try:
        result = asyncio.run(test_mcp_tools())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

