# MinerU Tianshu - MCP 集成指南

本文档介绍如何使用 Model Context Protocol (MCP) 将 MinerU Tianshu 文档解析服务集成到 AI 助手（如 Claude Desktop）中。

## 什么是 MCP？

Model Context Protocol (MCP) 是 Anthropic 推出的开放协议，用于 AI 应用与外部数据源和工具的集成。通过 MCP，AI 助手可以：
- 调用外部工具和服务
- 访问实时数据
- 执行复杂的任务流程

## 快速开始

### 1. 启动 MCP Server

在启动 MinerU Tianshu 服务时，添加 `--enable-mcp` 参数：

```bash
cd backend
python start_all.py --enable-mcp
```

这将启动所有服务，包括：
- API Server (Port 8000)
- LitServe Worker Pool (Port 9000)
- Task Scheduler
- **MCP Server (Port 8001)** ← 新增

### 2. 配置 AI 客户端

#### Claude Desktop 配置

**Windows:**
编辑文件 `%APPDATA%\Claude\claude_desktop_config.json`

**macOS:**
编辑文件 `~/Library/Application Support/Claude/claude_desktop_config.json`

**Linux:**
编辑文件 `~/.config/Claude/claude_desktop_config.json`

添加以下配置：

```json
{
  "mcpServers": {
    "mineru-tianshu": {
      "url": "http://localhost:8001/sse",
      "transport": "sse"
    }
  }
}
```

**远程服务器：**

如果 MCP Server 部署在远程服务器上，将 `localhost` 替换为服务器 IP 或域名：

```json
{
  "mcpServers": {
    "mineru-tianshu": {
      "url": "http://your-server-ip:8001/sse",
      "transport": "sse"
    }
  }
}
```

### 3. 重启 Claude Desktop

配置完成后，重启 Claude Desktop 使配置生效。

### 4. 使用示例

在 Claude 对话框中，你可以直接使用自然语言请求文档解析：

**示例 1: 解析本地 PDF 文件**
```
请帮我解析这个 PDF 文件，提取其中的文字和公式：
C:/Users/user/documents/research_paper.pdf
```

Claude 会：
1. 读取本地文件
2. Base64 编码
3. 调用 `parse_document` 工具
4. 等待解析完成
5. 返回 Markdown 格式的结果

**示例 2: 解析网络文件**
```
帮我解析这篇论文：https://arxiv.org/pdf/2301.12345.pdf
```

Claude 会自动使用 URL 方式下载并解析。

**示例 3: 查询任务状态**
```
帮我查看任务 a1b2c3d4-e5f6-7890-abcd-ef1234567890 的状态
```

**示例 4: 查看队列统计**
```
现在文档解析服务的队列情况怎么样？
```

## 可用工具

MCP Server 暴露了 4 个工具：

### 1. parse_document
解析文档为 Markdown 格式。

**支持的输入方式：**
- `file_base64`: Base64 编码的文件内容（适用于 < 100MB 的文件）
- `file_url`: 公网可访问的文件 URL

**支持的文件格式：**
- PDF 和图片（使用 MinerU GPU 加速）
- Office 文档（Word、Excel、PowerPoint）
- 网页和文本（HTML、Markdown、TXT、CSV）

**参数：**
```json
{
  "file_base64": "JVBERi0x...",  // 或使用 file_url
  "file_name": "document.pdf",
  "backend": "pipeline",           // pipeline/vlm-transformers/vlm-vllm-engine
  "lang": "ch",                    // ch/en/korean/japan
  "formula_enable": true,          // 是否启用公式识别
  "table_enable": true,            // 是否启用表格识别
  "priority": 0,                   // 任务优先级 0-100
  "wait_for_completion": true,     // 是否等待完成
  "max_wait_seconds": 300          // 最大等待时间
}
```

### 2. get_task_status
查询任务状态和结果。

**参数：**
```json
{
  "task_id": "a1b2c3d4-...",
  "include_content": true          // 是否包含完整内容
}
```

### 3. list_tasks
列出最近的任务。

**参数：**
```json
{
  "status": "completed",           // 可选：pending/processing/completed/failed
  "limit": 10                      // 返回数量
}
```

### 4. get_queue_stats
获取队列统计信息。

**参数：**
```json
{}
```

## 高级配置

### 自定义端口

```bash
python start_all.py --enable-mcp --mcp-port 8888
```

然后在客户端配置中相应修改：
```json
{
  "mcpServers": {
    "mineru-tianshu": {
      "url": "http://localhost:8888/sse",
      "transport": "sse"
    }
  }
}
```

### 仅启动 MCP Server

如果 API Server 和 Worker 已经在运行，可以单独启动 MCP Server：

```bash
export API_BASE_URL=http://localhost:8000
export MCP_PORT=8001
python mcp_server.py
```

### 使用 Nginx 反向代理

如果需要通过域名访问或添加 HTTPS 支持：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # MCP Server SSE endpoint
    location /sse {
        proxy_pass http://localhost:8001/sse;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # SSE 需要的特殊设置
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
    
    # MCP Server messages endpoint
    location /messages {
        proxy_pass http://localhost:8001/messages;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

客户端配置：
```json
{
  "mcpServers": {
    "mineru-tianshu": {
      "url": "http://your-domain.com/sse",
      "transport": "sse"
    }
  }
}
```

## 环境变量

MCP Server 支持以下环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_BASE_URL` | API Server 地址 | `http://localhost:8000` |
| `MCP_PORT` | MCP Server 端口 | `8001` |
| `MCP_HOST` | MCP Server 监听地址 | `0.0.0.0` |

## 故障排查

### MCP Server 无法启动

检查端口是否被占用：
```bash
# Windows
netstat -ano | findstr :8001

# Linux/Mac
lsof -i :8001
```

查看日志：
```bash
# 单独启动 MCP Server 查看详细日志
python backend/mcp_server.py
```

### Claude Desktop 无法连接

1. 确认 MCP Server 正在运行：
   ```bash
   curl http://localhost:8001/sse
   ```

2. 检查配置文件格式是否正确（JSON 格式）

3. 查看 Claude Desktop 日志：
   - Windows: `%APPDATA%\Claude\logs\`
   - macOS: `~/Library/Logs/Claude/`
   - Linux: `~/.config/Claude/logs/`

### 文件传输失败

- 小文件：自动使用 Base64 编码
- 大文件（> 100MB）：会返回错误，建议先上传到服务器再使用 `server_path`
- 网络文件：确保 URL 可公开访问，不需要认证

### 任务一直 pending

1. 检查 Worker 是否正常运行：
   ```bash
   curl -X POST http://localhost:9000/predict \
     -H "Content-Type: application/json" \
     -d '{"action":"health"}'
   ```

2. 查看队列状态：
   ```bash
   curl http://localhost:8000/api/v1/queue/stats
   ```

## 安全建议

1. **生产环境**：建议使用 HTTPS + 认证
2. **防火墙**：限制 MCP Server 端口的访问范围
3. **文件大小限制**：默认 100MB，可在代码中调整
4. **速率限制**：建议在 Nginx 层添加速率限制

## 性能优化

1. **文件传输**：
   - 小文件使用 Base64（简单快速）
   - 大文件使用 URL 下载（节省带宽）

2. **并发处理**：
   - MCP Server 支持多客户端同时连接
   - Worker Pool 自动负载均衡

3. **缓存**：
   - 解析结果会保存在服务器（默认保留 7 天）
   - 可通过任务 ID 重复查询结果

## 开发和测试

### 使用 MCP Inspector 测试

```bash
npm install -g @modelcontextprotocol/inspector
npx @modelcontextprotocol/inspector python backend/mcp_server.py
```

### 使用 Python SDK 测试

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import base64

async def test_mcp():
    server_params = StdioServerParameters(
        command="python",
        args=["backend/mcp_server.py"],
        env={"API_BASE_URL": "http://localhost:8000"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 列出可用工具
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")
            
            # 调用解析工具
            with open("test.pdf", "rb") as f:
                file_content = base64.b64encode(f.read()).decode()
            
            result = await session.call_tool(
                "parse_document",
                {
                    "file_base64": file_content,
                    "file_name": "test.pdf",
                    "wait_for_completion": True
                }
            )
            
            print(result)

asyncio.run(test_mcp())
```

## 相关资源

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/download)
- [MinerU 文档](https://github.com/opendatalab/MinerU)
- [项目主页](../README.md)

## 许可证

遵循 MinerU Tianshu 主项目许可证（Apache License 2.0）

