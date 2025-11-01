<div align="center">

# MinerU Tianshu 天枢

**企业级 AI 数据预处理平台**

支持文档、图片、音频等多模态数据处理 | GPU 加速 | MCP 协议

结合 Vue 3 前端 + FastAPI 后端 + LitServe GPU负载均衡

<p>
  <a href="https://github.com/magicyuan876/mineru-tianshu/stargazers">
    <img src="https://img.shields.io/github/stars/magicyuan876/mineru-tianshu?style=for-the-badge&logo=github&color=yellow" alt="Stars"/>
  </a>
  <a href="https://github.com/magicyuan876/mineru-tianshu/network/members">
    <img src="https://img.shields.io/github/forks/magicyuan876/mineru-tianshu?style=for-the-badge&logo=github&color=blue" alt="Forks"/>
  </a>
  <a href="https://github.com/magicyuan876/mineru-tianshu/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-Apache%202.0-green?style=for-the-badge" alt="License"/>
  </a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Vue-3.x-green?logo=vue.js&logoColor=white" alt="Vue"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115+-teal?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/CUDA-Supported-76B900?logo=nvidia&logoColor=white" alt="CUDA"/>
  <img src="https://img.shields.io/badge/MCP-Supported-orange" alt="MCP"/>
</p>

[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/819ff68b-5154-4717-9361-7db787d5a2f8)

[English](./README_EN.md) | 简体中文

<p>
  <a href="https://github.com/magicyuan876/mineru-tianshu">
    <img src="https://img.shields.io/badge/⭐_Star-项目-yellow?style=for-the-badge&logo=github" alt="Star"/>
  </a>
</p>

**如果这个项目对你有帮助，请点击右上角 ⭐ Star 支持一下，这是对开发者最大的鼓励！**

</div>

---

## 📝 最新更新

### 2025-10-30 🐳 Docker 部署 + 企业级认证系统

- ✅ **Docker 容器化部署支持**
  - **一键部署**：`make setup` 或运行部署脚本即可完成全栈部署
  - **多阶段构建**：优化镜像体积，分离依赖层和应用层
  - **GPU 支持**：NVIDIA CUDA 12.6 + Container Toolkit 集成
  - **服务编排**：前端、后端、Worker、MCP 完整编排（docker-compose）
  - **开发友好**：支持热重载、远程调试（debugpy）、实时日志
  - **生产就绪**：健康检查、数据持久化、零停机部署、资源限制
  - **跨平台脚本**：
    - Linux/Mac: `scripts/docker-setup.sh` 或 `Makefile`
    - Windows: `scripts/docker-setup.bat`
  - **完整文档**：`scripts/DOCKER_QUICK_START.txt`、`scripts/docker-commands.sh`
  - 详见：Docker 配置文件（`docker-compose.yml`、`backend/Dockerfile`、`frontend/Dockerfile`）

- ✅ **企业级用户认证与授权系统**
  - **JWT 认证**：安全的 Token 认证机制，支持 Access Token 和 Refresh Token
  - **用户数据隔离**：每个用户只能访问和管理自己的任务数据
  - **角色权限**：管理员（admin）和普通用户（user）角色
  - **API Key 管理**：用户可自助生成和管理 API 密钥，用于第三方集成
  - **用户管理**：管理员可管理所有用户、重置密码、启用/禁用账户
  - **SSO 预留接口**：支持 OIDC 和 SAML 2.0 单点登录（可选配置）
  - **前端集成**：登录/注册页面、用户中心、权限路由守卫
  - **数据库迁移**：自动为现有数据创建默认用户
  - 详见：`backend/auth/` 目录

### 2025-10-29 🧬 生物信息学格式支持

- ✅ **新增插件化格式引擎系统**
  - 支持专业领域文档格式的解析和结构化
  - 统一的引擎接口，易于扩展新格式
  - 为 RAG 应用提供 Markdown 和 JSON 双格式输出

- ✅ **生物信息学格式引擎**
  - **FASTA 格式**：DNA/RNA/蛋白质序列解析
    - 序列统计（数量、长度、平均值）
    - 碱基组成分析（A/T/G/C 比例）
    - 序列类型自动检测（DNA/RNA/蛋白质）
  - **GenBank 格式**：NCBI 基因序列注释格式
    - 完整的注释信息提取
    - 特征类型统计（gene/CDS/mRNA 等）
    - GC 含量计算和生物物种信息
  - 支持 BioPython 或内置解析器（可选依赖）
  - 详见：`backend/format_engines/README.md`

### 2025-10-27 🎨 水印去除支持（🧪 实验性）

- ✅ **智能水印检测与去除**
  - YOLO11x 专用检测模型 + LaMa 高质量修复
  - 支持图片（PNG/JPG/JPEG 等）和 PDF（可编辑/扫描件）
  - 前端可调参数：检测置信度、去除范围
  - 自动保存调试文件（检测可视化、掩码等）
  - 轻量模型，处理速度快，显存占用低

> **⚠️ 实验性功能**：某些特殊水印可能效果不佳，建议先小范围测试。  
> 📖 **详细说明**：[水印去除优化指南](backend/remove_watermark/README.md)

### 2025-10-24 🎬 视频处理支持

- ✅ **新增视频处理引擎**
  - 支持 MP4、AVI、MKV、MOV、WebM 等主流视频格式
  - **音频转写**：从视频中提取音频并转写为文字（基于 FFmpeg + SenseVoice）
  - **关键帧 OCR（🧪 实验性）**：自动提取视频关键帧并进行 OCR 识别
    - 场景检测：基于帧差异的自适应场景变化检测
    - 质量过滤：拉普拉斯方差 + 亮度评估
    - 图像去重：感知哈希（pHash）+ 汉明距离
    - 文本去重：编辑距离算法避免重复内容
    - 支持 PaddleOCR-VL 引擎
  - 支持多语言识别、说话人识别、情感识别
  - 输出带时间戳的文字稿（JSON 和 Markdown 格式）
  - 详见：`backend/video_engines/README.md`

### 2025-10-23 🎙️ 音频处理引擎

- ✅ **新增 SenseVoice 音频识别引擎**
  - 支持多语言识别（中文/英文/日文/韩文/粤语）
  - 内置说话人识别（Speaker Diarization）
  - 情感识别（中性/开心/生气/悲伤）
  - 输出 JSON 和 Markdown 格式
  - 详见：`backend/audio_engines/README.md`

### 2025-10-23 ✨

**🎯 支持内容结构化 JSON 格式输出**

- MinerU (pipeline) 和 PaddleOCR-VL 引擎现在支持输出结构化的 JSON 格式
- JSON 输出包含完整的文档内容结构信息（页面、段落、表格等）
- 用户可在任务详情页面切换查看 Markdown 或 JSON 格式
- 前端提供交互式 JSON 查看器，支持展开/收起、复制、下载等功能

**🎉 新增 PaddleOCR-VL 多语言 OCR 引擎**

- 支持 109+ 语言自动识别，无需手动指定语言
- 文档方向分类、文本图像矫正、版面区域检测等增强功能
- 原生 PDF 多页文档支持，模型自动下载管理
- 详细文档：[backend/paddleocr_vl/README.md](backend/paddleocr_vl/README.md)

### 2025-10-22

```
