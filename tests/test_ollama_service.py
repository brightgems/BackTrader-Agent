"""
Ollama 服务验证脚本
测试 LLM Advisory 与本地 Ollama 服务的集成
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_advisory.llm_advisor import check_llm_service_availability
from llm_advisory.services.ollama_service import get_ollama_service


def test_ollama_connection():
    """测试 Ollama 连接"""
    print("=== Ollama 连接测试 ===")
    
    try:
        service = get_ollama_service()
        
        # 测试基础连接
        if service.test_connection():
            print("✅ Ollama 服务连接成功")
        else:
            print("❌ Ollama 服务连接失败")
            return False
        
        # 获取可用模型
        models = service.get_available_models()
        if models:
            print(f"✅ 发现 {len(models)} 个模型:")
            for model in models:
                print(f"   - {model}")
        else:
            print("⚠️  未发现模型，请下载模型: ollama pull qwen3-vl")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


def test_chat_completion():
    """测试聊天完成功能"""
    print("\n=== 聊天完成测试 ===")
    
    try:
        service = get_ollama_service()
        
        messages = [
            {"role": "system", "content": "你是一个测试助手，请用中文回答。"},
            {"role": "user", "content": "请简单介绍一下量化交易"}
        ]
        
        response = service.create_chat_completion(
            messages=messages,
            model=os.getenv("OLLAMA_MODEL", default="qwen3-vl"),
            temperature=0.7,
            max_tokens=100
        )
        
        print("✅ 聊天完成测试成功")
        print(f"响应: {response['content'][:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ 聊天完成测试失败: {e}")
        return False


def test_advisory_integration():
    """测试 LLM Advisory 集成"""
    print("\n=== LLM Advisory 集成测试 ===")
    
    try:
        # 测试服务可用性检查
        result = check_llm_service_availability("ollama")
        
        print(f"服务状态: {'✅ 可用' if result['available'] else '❌ 不可用'}")
        print(f"提供商: {result['provider']}")
        print(f"可用提供商: {result.get('available_providers', [])}")
        
        if result['available']:
            print("✅ LLM Advisory 集成测试成功")
            return True
        else:
            print(f"❌ LLM Advisory 集成测试失败: {result['details']}")
            return False
            
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def test_trading_prompt():
    """测试交易相关的提示词"""
    print("\n=== 交易提示词测试 ===")
    
    try:
        service = get_ollama_service()
        
        # 模拟交易数据
        trading_data = """
        股票: AAPL
        当前价格: 150.25
        移动平均线(10日): 148.50
        移动平均线(30日): 145.80
        RSI(14): 65
        趋势: 上涨
        """
        
        system_prompt = """你是一名专业的量化交易分析师。请基于提供的交易数据给出分析建议。
        请用中文回答，格式为:
        信号: [bullish/bearish/neutral/none]
        信心: [0.0-1.0]
        分析: [简要分析]"""
        
        user_prompt = f"请分析以下交易数据:\n{trading_data}"
        
        response = service.generate_advisor_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="qwen3-vl"
        )
        
        print("✅ 交易提示词测试成功")
        print(f"响应长度: {len(response)} 字符")
        print(f"响应预览: {response[:300]}...")
        return True
        
    except Exception as e:
        print(f"❌ 交易提示词测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("Ollama 服务验证脚本")
    print("=" * 50)
    
    # 检查环境变量
    print("环境变量检查:")
    ollama_url = os.getenv('OLLAMA_BASE_URL', '未设置')
    ollama_model = os.getenv('OLLAMA_MODEL', '未设置')
    print(f"OLLAMA_BASE_URL: {ollama_url}")
    print(f"OLLAMA_MODEL: {ollama_model}")
    
    # 运行测试
    tests = [
        test_ollama_connection,
        test_chat_completion,
        test_advisory_integration,
        test_trading_prompt
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"测试异常: {e}")
            results.append(False)
    
    # 总结结果
    print("\n" + "=" * 50)
    print("测试总结:")
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total} 个测试")
    
    if passed == total:
        print("🎉 所有测试通过！Ollama 服务配置正确。")
        print("\n下一步:")
        print("1. 运行 examples/ollama_advisory_example.py")
        print("2. 集成到您的交易策略中")
    else:
        print("❌ 部分测试失败，请检查配置。")
        print("\n常见问题:")
        print("1. 确保 Ollama 已安装并运行")
        print("2. 下载模型: ollama pull qwen3-vl")
        print("3. 检查 .env 文件配置")
        print("4. 查看详细的错误信息")


if __name__ == "__main__":
    main()