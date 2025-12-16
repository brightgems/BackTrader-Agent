# Ollama 安装和配置指南

## 概述

Ollama 是一个强大的本地 LLM 部署工具，允许您在本地运行大型语言模型而无需依赖云端 API。本指南将帮助您设置 Ollama 以配合 Backtrader LLM Advisory 使用。

## 安装 Ollama

### Windows 系统

1. **下载安装程序**
   ```bash
   # 访问 Ollama 官网下载 Windows 版本
   # https://ollama.ai/download
   ```

2. **安装过程**
   - 运行下载的 `.exe` 安装程序
   - 按照安装向导完成安装
   - 安装完成后，Ollama 服务会自动启动

3. **验证安装**
   ```bash
   # 打开命令提示符或 PowerShell
   ollama --version
   ```

### macOS 系统

1. **使用 Homebrew 安装**
   ```bash
   brew install ollama
   ```

2. **或下载安装程序**
   ```bash
   # 从官网下载 macOS 版本
   # https://ollama.ai/download
   ```

3. **启动服务**
   ```bash
   ollama serve
   ```

### Linux 系统

1. **使用 curl 安装**
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **启动服务**
   ```bash
   systemctl start ollama
   # 或
   ollama serve
   ```

## 下载模型

### 常用模型推荐

```bash
# 基础模型 (轻量级，适合开发)
ollama pull qwen3-vl

# 代码理解模型
ollama pull codellama

```

### 模型管理命令

```bash
# 查看已下载模型
ollama list

# 删除模型
ollama rm <model-name>

# 复制模型
ollama cp <source> <destination>
```

## 配置 Backtrader LLM Advisory

### 环境变量配置

创建或编辑 `.env` 文件：

```bash
# 使用 Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-vl

# 可选：备用 OpenAI 配置
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_API_KEY=your_token_here
```

### Python 代码配置

```python
from llm_advisory.bt_advisory import BacktraderLLMAdvisory

# 使用 Ollama 配置
advisory = BacktraderLLMAdvisory(
    api_key="not-required",  # Ollama 不需要 API 密钥
    base_url="http://localhost:11434",
    model="qwen3-vl"  # 使用的模型名称
)
```

## 测试连接

### 基本连接测试

```python
from llm_advisory.services.ollama_service import get_ollama_service

def test_ollama_connection():
    service = get_ollama_service()
    if service.test_connection():
        print("✅ Ollama 连接成功")
        models = service.get_available_models()
        print(f"可用模型: {models}")
    else:
        print("❌ Ollama 连接失败")

test_ollama_connection()
```

### 集成测试

```python
from llm_advisory.llm_advisor import check_llm_service_availability

def test_integration():
    result = check_llm_service_availability("ollama")
    print(f"服务可用: {result['available']}")
    print(f"提供商: {result['provider']}")
    print(f"详情: {result['details']}")

test_integration()
```

## 性能优化

### 模型选择建议

| 模型 | 内存需求 | 响应速度 | 适用场景 |
|------|----------|----------|----------|
| qwen3-vl:7b | ~4GB | 快 | 开发测试 |
| qwen3-vl:13b | ~8GB | 中等 | 生产环境 |
| codellama | ~4GB | 快 | 代码分析 |
| qwen:7b | ~4GB | 快 | 中文场景 |

### 系统优化

1. **内存优化**
   ```bash
   # 限制模型使用的 GPU 内存
   OLLAMA_GPU_LAYERS=20 ollama run qwen3-vl
   ```

2. **性能监控**
   ```bash
   # 查看资源使用情况
   ollama ps
   ```

## 故障排除

### 常见问题

1. **连接被拒绝**
   ```
   错误：无法连接到 http://localhost:11434
   ```
   **解决方案：** 确保 Ollama 服务正在运行
   ```bash
   ollama serve
   ```

2. **模型未找到**
   ```
   错误：模型 'qwen3-vl' 未找到
   ```
   **解决方案：** 下载模型
   ```bash
   ollama pull qwen3-vl
   ```

3. **内存不足**
   ```
   错误：内存不足
   ```
   **解决方案：** 使用更小的模型或增加系统内存

4. **响应时间过长**
   **解决方案：** 
   - 使用更小的模型
   - 减少 `max_tokens` 参数
   - 检查系统资源使用情况

### 调试技巧

1. **启用详细日志**
   ```bash
   ollama serve --verbose
   ```

2. **检查服务状态**
   ```bash
   # Windows
   netstat -an | findstr 11434
   
   # Linux/Mac
   lsof -i :11434
   ```

3. **测试 API 端点**
   ```bash
   curl http://localhost:11434/api/tags
   ```

## 高级配置

### 自定义模型设置

创建自定义模型配置：

```bash
# 创建 Modelfile
cat > Modelfile << EOF
FROM qwen3-vl

# 设置系统提示词
SYSTEM """你是一名专业的量化交易分析师..."""

# 设置参数
PARAMETER temperature 0.7
PARAMETER num_predict 500
EOF

# 创建自定义模型
ollama create trading-advisor -f Modelfile
```

### 集成到策略中

```python
from llm_advisory.advisors import BacktraderPersonaAdvisor

# 使用自定义模型
advisor = BacktraderPersonaAdvisor(
    person_name="量化专家",
    personality="专业量化交易分析",
    provider="ollama",
    model="trading-advisor"  # 自定义模型
)
```

## 安全考虑

1. **本地部署优势**
   - 数据不离开本地环境
   - 无 API 调用限制
   - 更好的隐私保护

2. **资源管理**
   - 监控内存使用
   - 设置合理的超时时间
   - 定期清理不需要的模型

## 下一步

1. 完成 Ollama 安装和模型下载
2. 运行 `examples/ollama_advisory_example.py` 测试连接
3. 根据需求调整模型和参数配置
4. 集成到您的交易策略中

如有问题，请参考 Ollama 官方文档或项目 issues。
```