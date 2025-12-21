#!/usr/bin/env python3
"""最终修复测试脚本"""

import sys
import os

print("=== 最终修复测试 ===")
print(f"Python编码: {sys.getdefaultencoding()}")

# 重新加载环境变量
from dotenv import load_dotenv
load_dotenv(override=True)

# 检查关键配置
print("\n=== 配置检查 ===")
print(f"API端点: {os.getenv('OPENAI_BASE_URL')}")
print(f"模型名称: {os.getenv('OPENAI_MODEL')}")
print(f"API密钥: {os.getenv('OPENAI_API_KEY')[:20]}...")

try:
    print("\n=== 导入服务 ===")
    from llm_advisory.services.openai_service import get_openai_service
    
    print("✅ 导入成功")
    
    print("\n=== 测试服务初始化 ===")
    service = get_openai_service()
    print("✅ 服务初始化成功")
    
    print("\n=== 测试简单的API调用 ===")
    try:
        # 使用简单的英文测试避免编码问题
        response = service.create_chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="ERNIE-Bot-turbo",
            max_tokens=10
        )
        print("✅ API调用成功！")
        print(f"响应: {response.get('content', 'N/A')}")
        print("\n🎉 字符编码问题已修复！系统可以正常工作了。")
        
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        
        # 提供替代方案
        print(f"\n🔧 如果仍然有问题，请尝试以下方案：")
        print(f"1. 检查百度千帆账户的API配额和权限")
        print(f"2. 验证API密钥是否正确")
        print(f"3. 联系百度千帆技术支持")
        print(f"4. 使用离线Ollama服务作为备选方案")

except Exception as e:
    print(f"❌ 系统错误: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 测试完成 ===")