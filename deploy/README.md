# MinerU Tianshu 部署说明（生产环境）

> 本说明针对 **Linux（RPM 系，如 Kylin / RHEL / CentOS）+ NVIDIA GPU** 的**原生（非 Docker）部署**。
> 包含本仓库在原有 Tianshu 基础上**增强的功能**与**部署基础设施**。所有示例中的 `<...>` 均为占位符，请替换为你的实际值。

---

## 一、本次增强的功能（代码变更）

| 模块 | 改动 | 说明 |
|---|---|---|
| 后端 | `GET /api/v1/tasks/{id}/download` | 把合并后的完整结果打成 **ZIP**（含 result.md/json + 源文件 + 图片）下载；任务详情返回 `download_url` |
| 后端 | 并发调度 | `get_next_task` 增加**每用户并发上限 `MAX_WORKERS_PER_USER` + 公平调度**，避免单用户霸占全部 worker |
| 后端 | 自动选引擎 | `auto` 模式用启发式：纯文本 → `pipeline`；图片/扫描件 → `hybrid-auto-engine` |
| 后端 | MCP | 默认 `backend=auto`；`get_task_status` 返回 `download_url`；`allowed_hosts` 允许公网 IP |
| 前端 | 大文档预览 | `VirtualPdfViewer` 的 `MAX_PREVIEW_PAGES` 可配置（`VITE_MAX_PREVIEW_PAGES`，默认 50），超大 PDF 只预览前 N 页 |
| 前端 | 双向同步 | 修复 `extractV2Text`（字符串 content 提取）；只渲染有文本的块 |
| 前端 | 下载体验 | 任务详情“下载完整结果(Zip)”带加载态提示；任务列表每行支持单条删除 |

---

## 二、依赖与前置

- **系统**：Linux x86_64，**glibc 较老的系统请用 RustFS 的 MUSL 静态版**（避免 `GLIBC_2.39 not found`）。
- **GPU**：NVIDIA 驱动 + CUDA（本仓库按 A5000 24G 调优）。
- **RustFS**（对象存储，图片必需）：单二进制，从官网 `https://rustfs.com` 获取（**避免 raw.githubusercontent / github**），用 **MUSL 版**。
- **前端构建工具**：Node.js 20+、npm。

---

## 三、RustFS 对象存储（图片上传必需）

1. 下载 RustFS **MUSL 二进制**（`rustfs-linux-x86_64-musl-...`），放到 `/usr/local/bin/rustfs`。
2. 建数据目录（建议独立分区）：`mkdir -p /data/rustfs0`。
3. 创建 `/etc/default/rustfs`：
   ```bash
   cp deploy/rustfs/etc-default-rustfs.example /etc/default/rustfs
   # 编辑，把 CHANGE_ME_* 换成强随机值
   ```
4. 安装系统服务：
   ```bash
   cp deploy/systemd/rustfs.service /etc/systemd/system/rustfs.service
   systemctl daemon-reload && systemctl enable rustfs && systemctl start rustfs
   ```
5. 建桶并设公开读（用 minio-py 或 mc）：
   - bucket：`ts-img`，策略允许 anonymous `GetObject`，`PUBLIC_URL=http://<SERVER_IP>:9000`。

---

## 四、后端服务（systemd）

```bash
cp deploy/systemd/tianshu.service /etc/systemd/system/tianshu.service
# 编辑：把 /opt/mineru-tianshu 替换为你的项目路径；按需调 MAX_CONCURRENT_TASKS / MINERU_VIRTUAL_VRAM_SIZE / MAX_WORKERS_PER_USER
systemctl daemon-reload && systemctl start tianshu   # 不 enable，手动启动
```

### 关键环境变量（`backend/.env`）
| 变量 | 说明 |
|---|---|
| `MAX_CONCURRENT_TASKS` | worker 进程数（示例 3）|
| `MINERU_VIRTUAL_VRAM_SIZE` | 每 worker 显存预算（示例 7，**只能整数**）|
| `MAX_WORKERS_PER_USER` | 每用户最多同时占用的 worker 数（示例 2）|
| `RUSTFS_ENABLED` / `RUSTFS_ENDPOINT` / `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` / `RUSTFS_BUCKET` / `RUSTFS_PUBLIC_URL` | 对象存储配置 |
| `TIANSHU_ADMIN_PASSWORD` | 初始管理员密码 |
| `MCP_API_KEYS` / `TIANSHU_API_KEY` | MCP 接入密钥 / MCP 反调后端用的 key |

> 这些含密钥的 `.env` **不要入库**（已在 `.gitignore`）。

---

## 五、Nginx（前端 + 反向代理）

```bash
cp deploy/nginx/tianshu.conf /etc/nginx/conf.d/tianshu.conf
# 编辑：把 <SERVER_IP> 换成公网 IP、路径换成项目路径
# 若 /etc/nginx/mime.types 的 application/javascript 行没有 mjs，请补上：
#   application/javascript  js mjs;
nginx -t && systemctl reload nginx
```

**关键点**：一定要给 `.mjs` 正确的 MIME（`application/javascript`），否则浏览器会因严格 MIME 校验拒绝 PDF.js 的 worker，导致 PDF 预览失败。

---

## 六、MCP 接入（给 AI Agent 用）

- 地址（任选其一，已验证等价）：
  - 直连：`http://<SERVER_IP>:8002/sse`
  - 经 Nginx：`http://<SERVER_IP>/sse`
- 鉴权：请求头 `Authorization: Bearer <MCP_API_KEYS>` 或 `X-API-Key: <MCP_API_KEYS>`（**不支持 URL 传参鉴权**）。
- 为让公网/外网地址能通过 MCP 的 DNS 重绑定防护，需给 MCP 服务设置 `MCP_EXTRA_ALLOWED_HOSTS=<SERVER_IP>`（逗号分隔，可多个）。
- 通用配置：
  ```json
  {
    "mcpServers": {
      "mineru-tianshu": {
        "url": "http://<SERVER_IP>:8002/sse",
        "transport": "sse",
        "headers": { "Authorization": "Bearer <MCP_API_KEYS>" },
        "description": "MinerU Tianshu - 文档解析"
      }
    }
  }
  ```
- 快速连通测试：`curl -N -H "Authorization: Bearer <MCP_API_KEYS>" http://<SERVER_IP>:8002/sse`，正常应返回 `event: endpoint`。
- MCP `parse_document` 默认 `backend=auto`（自动选引擎），支持参数：`file_base64+file_name` 或 `file_url`，以及 `backend`、`lang`、`method`、`formula_enable`、`table_enable`、`priority`、`password`、`wait_for_completion`、`max_wait_seconds`。

---

## 七、访问地址

- Web 界面：`http://<SERVER_IP>/`
- API 文档：`http://<SERVER_IP>/docs`
- MCP：`http://<SERVER_IP>:8002/sse`
- 管理员可先通过平台重置 `TIANSHU_ADMIN_PASSWORD` 后用其对应用户登录。

---

## 八、注意事项 / 已知行为

- **服务不自启**：`tianshu`、`nginx` 默认 disabled，需手动 `systemctl start`；`rustfs` enabled 随开机。
- **大文档自动拆分**：>40 页 PDF 会拆成 20 页分片并行处理；父任务自动合并成一份完整结果，可下载 ZIP。
- **VLM/hybrid 较慢**：视觉模型逐页推理（实测约 0.03 页/秒），属正常。
- **MCP 会话**：同一 key 建议只给一个客户端；SSE 会话随连接失效，消失后客户端应重建连接。
- **模型自动休眠**：worker 空闲 5 分钟会卸载模型释放显存，来任务再加载。
