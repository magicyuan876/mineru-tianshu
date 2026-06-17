# 任务级 RustFS 开关 与 图片交接接口

> 一对**配套使用**的能力，用于把"文档解析"与"图片归属"解耦，让下游接入方能够完整接管解析结果中的图片。

## 1. 背景与问题

天枢默认会在解析完成后，把结果中的图片**自动上传到自带的 RustFS 对象存储**，并将 Markdown / JSON 里的图片引用替换成 RustFS 的公网 URL。对于"天枢独立使用"的场景，这非常方便——拿到的 Markdown 开箱即用、图片链接直接可访问。

但当天枢作为一个**文档解析微服务**被其他系统集成时，这个默认行为会带来问题。典型的接入方往往**自带对象存储 / CDN，并有自己的多租户、目录命名和生命周期管理**，它需要把图片放进**自己的命名空间**（例如 `{租户}/images/{文档}/{文件名}`），而不是停留在天枢的 RustFS 里。

如果图片留在天枢侧，会出现三类问题：

1. **归属与隔离**：租户数据散落在接入方管不到的存储里，无法纳入自身的权限、租户隔离体系。
2. **生命周期耦合**：天枢一旦清理输出目录或回收 RustFS 桶，接入方已入库文档引用的图片就会全部失效（404）。
3. **可控性缺失**：鉴权、CDN 加速、备份、删除等都不在接入方手里。

为了解决这些问题，天枢提供了这一对配套能力：

- **任务级 RustFS 开关 `use_rustfs`** —— 让天枢在该任务中**不抢占图片所有权**；
- **图片交接接口 `GET /tasks/{task_id}/images`** —— 让接入方**把图片完整接管过去**。

二者必须成对使用，缺一不可。

---

## 2. 能力一：任务级 RustFS 开关 `use_rustfs`

### 作用

在**单次任务粒度**上控制天枢是否把图片上传到自带 RustFS。原先只有全局环境变量 `RUSTFS_ENABLED` 能控制，无法按调用方区分；而同一个天枢实例往往需要同时服务两类场景：

- "图片我自己用 RustFS"的场景（默认上传）；
- "图片归接入方自己管"的场景（关闭上传、保留本地）。

任务级开关让这两类需求可以共存于同一部署。

### 取值语义（三态）

提交任务时通过表单参数 `use_rustfs` 传入：

| 取值 | 行为 |
|------|------|
| 不传（`None`） | **向后兼容**：由环境变量 `RUSTFS_ENABLED` 决定（默认开启） |
| `true` | 强制上传到 RustFS，并把图片引用替换为 RustFS URL |
| `false` | **不上传**，图片保留在本地输出目录，引用维持本地相对路径，通过文件服务 `/files/output/...` 提供下载 |

> 设计要点：默认值是 `None` 而非 `true`，因此**不指定该参数的旧调用方行为完全不变**——仍由 `RUSTFS_ENABLED` 全局控制。

### 覆盖范围

该开关贯穿了所有解析引擎的输出规范化路径（MinerU Pipeline、PaddleOCR-VL、音频、视频、MarkItDown、格式引擎，以及大文件拆分后的父任务合并），也覆盖自研的 Office（xlsx/pptx）与 Markdown 原生解析路径。无论文档走哪条处理链，`use_rustfs` 的语义保持一致。

---

## 3. 能力二：图片交接接口 `GET /tasks/{task_id}/images`

### 作用

当一个任务以 `use_rustfs=false` 完成后，Markdown 里只剩**本地相对路径**。接入方需要知道"这个结果里到底有哪些图、去哪下载"，才能把它们搬到自己的存储。该接口正是为此提供一份**可下载的图片清单**。

### 关键设计：只返回"被引用"的图片

接口会解析结果中的 `result.md`，提取 Markdown 语法 `![alt](url)` 与 HTML `<img src="...">` 中**实际引用**到的图片文件名，**只返回这些图片**。解析引擎产生的中间产物图、未被正文引用的临时图都会被过滤掉——避免接入方下载并入库一堆无用文件。

### 接口契约

```
GET /api/v1/tasks/{task_id}/images
Authorization: Bearer <token>
```

**权限**：沿用任务查看权限模型——用户只能查看自己的任务；拥有 `TASK_VIEW_ALL` 的管理员可查看全部。

**响应**（任务 `completed` 且有被引用图片时）：

```json
{
  "success": true,
  "task_id": "xxxx",
  "status": "completed",
  "images": [
    {
      "filename": "abc123.jpg",
      "download_url": "/api/v1/files/output/<相对路径>/images/abc123.jpg",
      "size": 20480
    }
  ],
  "total": 1
}
```

**边界行为**：

- 任务非 `completed`：返回空列表 + 当前 `status`。
- 结果已被清理（无 `result_path`）：返回空列表，附 `message: "Result files have been cleaned up"`。
- 图片目录不存在：返回空列表。
- 落在输出根目录之外的文件：跳过，不返回。

随后接入方即可逐条通过 `download_url`（指向天枢文件服务 `/files/output/...`）下载图片二进制，存入自己的存储并改写 Markdown 中的图片路径。

---

## 4. 二者如何协同

```
┌─────────────┐   submit(use_rustfs=false)   ┌──────────────────────┐
│  接入方系统  │ ───────────────────────────▶ │  天枢：解析，图片留本地  │
└─────────────┘                              └──────────────────────┘
       │                                                │
       │            GET /tasks/{id}/images              │
       │  ◀──────────  返回被引用图片清单  ───────────────│
       │            （filename + download_url）          │
       │                                                │
       │   逐张 GET download_url 下载二进制               │
       │  ◀──────────────────────────────────────────── │
       │                                                │
       ▼
  存入自有对象存储 {租户}/images/{文档}/{文件名}
  并改写 Markdown 图片路径为自有存储路径
```

- `use_rustfs=false` 让天枢**不抢图片所有权**，图片以原始文件形式保留。
- `/tasks/{id}/images` 让接入方**精确拿到该接管哪些图、从哪下载**。

少了开关，图片会被替换成天枢 RustFS 的 URL，接入方无从接管；少了接口，接入方拿到本地相对路径却无法枚举和定位图片。因此两者是**一对不可拆分的能力**。

---

## 5. 兼容性说明

- **不影响既有调用方**：`use_rustfs` 默认 `None`，沿用 `RUSTFS_ENABLED` 全局开关；不调用新接口、不传新参数的客户端行为零变化。
- **独立部署不受影响**：天枢单独使用时，默认仍会上传 RustFS、返回可直接访问的 URL。
- **本地保留模式依赖文件服务**：`use_rustfs=false` 时图片通过 `/files/output/...` 暴露，需确保该文件服务路由对解析输出目录可访问。

---

## 6. 快速上手

```bash
# 1) 提交任务，关闭 RustFS 上传（图片留本地）
curl -X POST "$HOST/api/v1/tasks/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "use_rustfs=false"
# → { "task_id": "xxxx", ... }

# 2) 轮询直到任务 completed
curl "$HOST/api/v1/tasks/xxxx" -H "Authorization: Bearer $TOKEN"

# 3) 拉取被引用的图片清单
curl "$HOST/api/v1/tasks/xxxx/images" -H "Authorization: Bearer $TOKEN"
# → { "images": [ { "filename": "...", "download_url": "/api/v1/files/output/...", "size": ... } ], "total": N }

# 4) 逐张下载并接管到自有存储
curl "$HOST<download_url>" -H "Authorization: Bearer $TOKEN" -o abc123.jpg
```
