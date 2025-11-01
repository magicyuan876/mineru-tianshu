<div align="center">

# MinerU Tianshu 天枢

**Enterprise-grade AI Data Preprocessing Platform**

Multi-modal Data Processing (Documents, Images, Audio) | GPU Acceleration | MCP Protocol

Vue 3 Frontend + FastAPI Backend + LitServe GPU Load Balancing

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

English | [简体中文](./README.md)

<p>
  <a href="https://github.com/magicyuan876/mineru-tianshu">
    <img src="https://img.shields.io/badge/⭐_Star-This_Project-yellow?style=for-the-badge&logo=github" alt="Star"/>
  </a>
</p>

**If you find this project helpful, please ⭐ Star it! Your support means a lot!**

</div>

---

## 📝 Latest Updates

### 2025-10-30 🐳 Docker Deployment + Enterprise Authentication

- ✅ **Docker Containerization Support**
  - **One-Click Deployment**: Complete full-stack deployment with `make setup` or deployment scripts
  - **Multi-Stage Build**: Optimized image size, separated dependency and application layers
  - **GPU Support**: NVIDIA CUDA 12.6 + Container Toolkit integration
  - **Service Orchestration**: Complete orchestration of frontend, backend, Worker, MCP (docker-compose)
  - **Developer Friendly**: Hot reload, remote debugging (debugpy), real-time logs
  - **Production Ready**: Health checks, data persistence, zero-downtime deployment, resource limits
  - **Cross-Platform Scripts**:
    - Linux/Mac: `scripts/docker-setup.sh` or `Makefile`
    - Windows: `scripts/docker-setup.bat`
  - **Complete Documentation**: `scripts/DOCKER_QUICK_START.txt`, `scripts/docker-commands.sh`
  - See: Docker configuration files (`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`)

- ✅ **Enterprise-Grade User Authentication & Authorization**
  - **JWT Authentication**: Secure token-based authentication with Access Token and Refresh Token
  - **User Data Isolation**: Each user can only access and manage their own task data
  - **Role-Based Access**: Administrator (admin) and regular user (user) roles
  - **API Key Management**: Users can self-generate and manage API keys for third-party integration
  - **User Management**: Admins can manage all users, reset passwords, enable/disable accounts
  - **SSO Ready**: Support for OIDC and SAML 2.0 single sign-on (optional configuration)
  - **Frontend Integration**: Login/registration pages, user profile, permission route guards
  - **Database Migration**: Automatic default user creation for existing data
  - See: `backend/auth/` directory

### 2025-10-29 🧬 Bioinformatics Format Support

- ✅ **New Plugin-Based Format Engine System**
  - Support for parsing and structuring professional domain document formats
  - Unified engine interface, easy to extend new formats
  - Provide both Markdown and JSON format output for RAG applications

- ✅ **Bioinformatics Format Engines**
  - **FASTA Format**: DNA/RNA/Protein sequence parsing
    - Sequence statistics (count, length, average)
    - Base composition analysis (A/T/G/C ratios)
    - Automatic sequence type detection (DNA/RNA/Protein)
  - **GenBank Format**: NCBI gene sequence annotation format
    - Complete annotation information extraction
    - Feature type statistics (gene/CDS/mRNA, etc.)
    - GC content calculation and organism information
  - Support BioPython or built-in parser (optional dependency)
  - See: `backend/format_engines/README.md`

### 2025-10-27 🎨 Watermark Removal Support (🧪 Experimental)

- ✅ **Intelligent Watermark Detection and Removal**
  - YOLO11x specialized detection model + LaMa high-quality inpainting
  - Support for images (PNG/JPG/JPEG etc.) and PDFs (editable/scanned)
  - Frontend adjustable parameters: detection confidence, removal range
  - Auto-save debug files (detection visualization, masks, etc.)
  - Lightweight models, fast processing, low VRAM usage

> **⚠️ Experimental Feature**: May not work well for certain special watermarks. Test on small scale first.  
> 📖 **Detailed Guide**: [Watermark Removal Optimization Guide](backend/remove_watermark/README_EN.md)

### 2025-10-24 🎬 Video Processing Support

- ✅ **New Video Processing Engine**
  - Support for mainstream video formats: MP4, AVI, MKV, MOV, WebM, etc.
  - **Audio Transcription**: Extract audio from videos and transcribe to text (FFmpeg + SenseVoice)
  - **Keyframe OCR (🧪 Experimental)**: Automatic keyframe extraction and OCR recognition
    - Scene detection: Adaptive scene change detection based on frame difference
    - Quality filtering: Laplacian variance + brightness assessment
    - Image deduplication: Perceptual hashing (pHash) + Hamming distance
    - Text deduplication: Edit distance algorithm to avoid redundant content
    - Support for PaddleOCR-VL engine
  - Multi-language recognition, speaker diarization, emotion recognition
  - Output timestamped transcripts in JSON and Markdown formats
  - Details: `backend/video_engines/README.md`

### 2025-10-23 🎙️ Audio Processing Engine

- ✅ **New SenseVoice Audio Recognition Engine**
  - Multi-language recognition (Chinese/English/Japanese/Korean/Cantonese)
  - Built-in speaker diarization
  - Emotion recognition (Neutral/Happy/Angry/Sad)
  - Event detection (Speech/Applause/BGM/Laugh)
  - Output in JSON and Markdown formats with emoji visualization
  - Details: `backend/audio_engines/README.md`

### 2025-10-23 ✨

**🎯 Structured JSON Format Output Support**

- MinerU (pipeline) and PaddleOCR-VL engines now support structured JSON format output
- JSON output contains complete document structure information (pages, paragraphs, tables, etc.)
- Users can switch between Markdown and JSON formats in the task detail page
- Frontend provides an interactive JSON viewer with expand/collapse, copy, and download features

**🎉 New PaddleOCR-VL Multi-Language OCR Engine**

- Support for 109+ language automatic recognition without manual specification
- Enhanced features: document orientation, text unwarping, layout detection
- Native PDF multi-page support with automatic model download
- Documentation: [backend/paddleocr_vl/README.md](backend/paddleocr_vl/README.md)

### 2025-10-22

```

---

## 🌟 Introduction

MinerU Tianshu is an **Enterprise-grade AI Data Preprocessing Platform** that converts various unstructured data into AI-ready structured formats:

- **📄 Document Processing**: PDF, Word, Excel, PPT → Markdown/JSON
  - MinerU Pipeline (complete parsing), PaddleOCR-VL (109+ languages)
  - **🧪 Watermark Removal (Experimental)**: YOLO11x + LaMa intelligent detection and removal

- **🎬 Video Processing**: MP4, AVI, MKV, MOV → Speech Transcription + Keyframe OCR
  - Video audio extraction (FFmpeg) + speech recognition (SenseVoice)
  - **🧪 Keyframe OCR (Experimental)**: Scene detection + quality filtering + image deduplication + OCR
  - Multi-language support, speaker diarization, emotion recognition

- **🎙️ Audio Processing**: MP3, WAV, M4A → Transcription + Speaker Diarization
  - SenseVoice engine with multi-language support, emotion recognition, event detection

- **🖼️ Image Processing**: JPG, PNG → Text extraction + Structuring
  - Multiple OCR engines available with GPU acceleration
  - **🧪 Watermark Removal Preprocessing (Experimental)**: Intelligent watermark detection and auto-removal

- **🏗️ Enterprise Features**:
  - GPU load balancing, task queue, priority management, automatic retry
  - MCP protocol support for direct integration with AI assistants (Claude Desktop, etc.)
  - Modern web interface for easy management and monitoring

## ✨ Key Features

<table>
  <tr>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Desktop%20Computer.png" width="60"/><br/>
      <strong>Modern UI</strong><br/>
      <sub>Vue 3 + TypeScript + TailwindCSS</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Electric%20Plug.png" width="60"/><br/>
      <strong>GPU Acceleration</strong><br/>
      <sub>LitServe Load Balancing + Multi-GPU Isolation</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Memo.png" width="60"/><br/>
      <strong>Multi-modal Processing</strong><br/>
      <sub>Documents/Images/Audio → Structured Data</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://raw.githubusercontent.com/Tarikul-Islam-Anik/Animated-Fluent-Emojis/master/Emojis/Objects/Link.png" width="60"/><br/>
      <strong>MCP Protocol</strong><br/>
      <sub>Seamless AI Assistant Integration</sub>
    </td>
  </tr>
</table>

## 📸 Screenshots

<div align="center">

### 📊 Dashboard - Real-time Monitoring

<img src="./docs/img/dashboard.png" alt="Dashboard" width="80%"/>

*Real-time queue statistics and recent tasks monitoring*

---

### 📤 Task Submission - Drag & Drop Upload

<img src="./docs/img/submit.png" alt="Task Submission" width="80%"/>

*Supports batch processing and advanced configuration*

---

### ⚙️ Queue Management - System Monitoring

<img src="./docs/img/tasks.png" alt="Queue Management" width="80%"/>

*Reset timeout tasks and clean up old files*

</div>

### Main Features

- ✅ **User Authentication**: JWT-based secure authentication, role-based access control
- ✅ **Dashboard**: Real-time monitoring of queue statistics and recent tasks
- ✅ **Task Submission**: Drag-and-drop file upload, batch processing, and advanced configuration
- ✅ **Task Details**: Real-time status tracking, Markdown/JSON preview, automatic polling updates
- ✅ **Task List**: Filtering, searching, pagination, batch operations
- ✅ **Queue Management**: System monitoring, reset timeout tasks, clean up old files
- ✅ **User Management**: Admin panel for user management, API key generation
- ✅ **MCP Protocol Support**: AI assistant integration via Model Context Protocol
- ✅ **Docker Support**: One-click deployment with complete containerization

### Supported File Formats

- 📄 **PDF and Images** - Multiple GPU-accelerated engines available
  - **MinerU**: Complete document parsing with table and formula recognition
  - **PaddleOCR-VL**: Multi-language OCR (109+ languages), auto orientation and layout analysis
- 📊 **Office Documents** - Word, Excel, PowerPoint (using MarkItDown)
- 🌐 **Web and Text** - HTML, Markdown, TXT, CSV, etc.
- 🎙️ **Audio Files** - MP3, WAV, M4A, FLAC, etc. (using SenseVoice)
  - Multi-language recognition (Chinese/English/Japanese/Korean/Cantonese)
  - Speaker diarization and separation
  - Emotion recognition (Neutral/Happy/Angry/Sad)
  - Output in JSON and Markdown formats
- 🎬 **Video Files** - MP4, AVI, MKV, MOV, WebM, etc.
  - Audio transcription from video (FFmpeg + SenseVoice)
  - Keyframe OCR (🧪 Experimental)
- 🧬 **Bioinformatics Formats** - FASTA, GenBank (using plugin-based format engines)
  - **FASTA**: DNA/RNA/Protein sequence parsing
  - **GenBank**: NCBI gene sequence annotation format
  - Sequence statistics, base composition analysis, GC content calculation

## 🏗️ Project Structure

```
mineru-server/
├── frontend/               # Vue 3 frontend project
│   ├── src/
│   │   ├── api/           # API interface layer
│   │   ├── components/    # Common components
│   │   ├── layouts/       # Layout components
│   │   ├── views/         # Page components
│   │   ├── stores/        # Pinia state management
│   │   ├── router/        # Vue Router
│   │   └── utils/         # Utility functions
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md          # Frontend documentation
│
├── backend/                # Python backend project
│   ├── api_server.py      # FastAPI server
│   ├── task_db.py         # Database management
│   ├── auth/              # Authentication & Authorization
│   │   ├── jwt_handler.py       # JWT token handling
│   │   ├── models.py            # User data models
│   │   ├── routes.py            # Auth routes
│   │   ├── dependencies.py      # Dependency injection
│   │   └── sso.py               # SSO support (optional)
│   ├── audio_engines/     # Audio processing engines
│   │   ├── sensevoice_engine.py  # SenseVoice engine
│   │   └── README.md      # Audio engine documentation
│   ├── format_engines/    # Format engines (professional formats)
│   │   ├── base.py        # Base format engine
│   │   ├── fasta_engine.py      # FASTA format engine
│   │   ├── genbank_engine.py    # GenBank format engine
│   │   └── README.md      # Format engine documentation
│   ├── video_engines/     # Video processing engines
│   │   ├── video_engine.py      # Video processing engine
│   │   ├── keyframe_extractor.py # Keyframe extraction
│   │   └── README.md      # Video engine documentation
│   ├── remove_watermark/  # Watermark removal module
│   │   ├── watermark_remover.py     # Watermark remover
│   │   ├── pdf_watermark_handler.py # PDF watermark handling
│   │   └── README.md      # Watermark removal documentation
│   ├── litserve_worker.py # Worker Pool
│   ├── task_scheduler.py  # Task scheduler
│   └── start_all.py       # Main entry point
│
├── scripts/                # Deployment scripts
│   ├── docker-setup.sh    # Docker setup script
│   ├── docker-setup.bat   # Windows Docker setup script
│   └── docker-commands.sh # Docker management commands
│
├── docker-compose.yml     # Production Docker Compose
├── docker-compose.dev.yml # Development Docker Compose
├── Makefile               # Build and deployment commands
├── .env.example           # Environment variables template
└── pyproject.toml         # Project metadata
```

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** (Recommended)
- **NVIDIA GPU** with **CUDA 12.6+** (for GPU acceleration)
- **8GB+ RAM** (16GB+ recommended)
- **50GB+ Disk Space** (for model downloads and processing)

### One-Click Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/mineru-tianshu.git
cd mineru-tianshu

# One-click setup (builds images and starts services)
make setup

# Or on Windows:
.\scripts\docker-setup.bat
```

This will:
1. Build all Docker images
2. Start all services (API, Workers, Scheduler, Frontend)
3. Initialize the database
4. Download required models

### Manual Setup

1. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start Services**:
   ```bash
   # Terminal 1: Start API Server
   cd backend
   python api_server.py

   # Terminal 2: Start Worker Pool
   cd backend
   python litserve_worker.py

   # Terminal 3: Start Task Scheduler
   cd backend
   python task_scheduler.py

   # Terminal 4: Start Frontend
   cd frontend
   npm install
   npm run dev
   ```

3. **Access the Platform**:
   - **Frontend**: http://localhost:3000
   - **API Docs**: http://localhost:8000/docs
   - **Admin Panel**: http://localhost:3000/admin

## 📖 Usage Guide

### 1. Authentication

All API endpoints require authentication. Get your JWT token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### 2. Submit a Task

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document.pdf" \
  -F "backend=pipeline" \
  -F "lang=ch"
```

### 3. Check Task Status

```bash
curl -X GET http://localhost:8000/api/v1/tasks/YOUR_TASK_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. View Results

Once completed, the task will return the path to the processed files:

- **Markdown**: `output/task_id/filename.md`
- **Images**: `output/task_id/images/`

## 🛠️ Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Copy the template
cp .env.example .env

# Edit the file
nano .env
```

Key variables:
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `MINIO_ENDPOINT`: MinIO endpoint for image storage
- `MINIO_ACCESS_KEY`: MinIO access key
- `MINIO_SECRET_KEY`: MinIO secret key

### Model Download Sources

To speed up model downloads in China:

```bash
# Set environment variable
export MODEL_DOWNLOAD_SOURCE=modelscope

# Or in .env file
MODEL_DOWNLOAD_SOURCE=modelscope
```

## 🧪 Experimental Features

### Watermark Removal

Remove watermarks from PDFs and images:

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@document_with_watermark.pdf" \
  -F "backend=pipeline" \
  -F "remove_watermark=true"
```

### Keyframe OCR

Extract keyframes from videos and perform OCR:

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@video.mp4" \
  -F "backend=video" \
  -F "enable_keyframe_ocr=true" \
  -F "ocr_backend=paddleocr-vl"
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MinerU](https://github.com/opendatalab/MinerU) - Core document parsing engine
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Multi-language OCR engine
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) - Audio processing engine
- [YOLO11](https://github.com/ultralytics/ultralytics) - Object detection for watermark removal
- [LaMa](https://github.com/saic-mdal/lama) - Image inpainting for watermark removal
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Vue 3](https://vuejs.org/) - Frontend framework
- [LitServe](https://github.com/Lightning-AI/litserve) - GPU load balancing

## 📞 Support

For issues, questions, or contributions, please:
- Open an issue on GitHub
- Join our Discord community
- Contact us at support@mineru-tianshu.com

---

<div align="center">

**Made with ❤️ by the MinerU Tianshu Team**

[Documentation](docs/) • [API Reference](backend/README.md) • [Frontend Guide](frontend/README.md)

</div>
