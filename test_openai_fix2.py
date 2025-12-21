#!/usr/bin/env python3
"""测试OpenAI服务修复脚本 - 更新版"""

import sys
import os
import traceback

print("=== OpenAI服务修复测试 v2 ===")
print(f"Python版本: {sys.version}")

# 强制重新加载环境变量
from dotenv import load_dotenv
load_dotenv(override=True)

# 检查环境变量
print("\n=== 环境变量检查 ===")
env_vars = ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL']
for var in env_vars:
    value = os.getenv(var)
    if value:
        # 隐藏敏感信息
        if 'KEY' in var or 'TOKEN' in var:
            masked = value[:10] + '...' if len(value) > 10 else '***'
            print(f"{var}: {masked}")
        else:
            print(f"{var}: {value}")
    else:
        print(f"{var}: (未设置)")

try:
    print("\n=== 导入OpenAI服务 ===")
    from llm_advisory.services.openai_service import get_openai_service
    
    print("✅ 导入成功")
    
    print("\n=== 初始化服务 ===")
    service = get_openai_service()
    print("✅ 服务初始化成功")
    
    print("\n=== 连接测试 ===")
    try:
        result = service.test_connection()
        print(f"连接测试结果: {'✅ 成功' if result else '❌ 失败'}")
    except Exception as e:
        print(f"❌ 连接测试错误: {e}")
        print("详细错误信息:")
        traceback.print_exc()
        
    # 简单测试 - 使用更简单的数据
    print("\n=== 简单请求测试 ===")
    try:
        print("发送测试请求...")
        test_response = service.create_chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("✅ 请求成功")
        print(f"响应: {test_response.get('content', 'N/A')}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        traceback.print_exc()

except Exception as e:
    print(f"❌ 严重错误: {e}")
    traceback.print_exc()

print("\n=== 测试完成 ===")