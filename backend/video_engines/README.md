# 视频处理引擎

基于 FFmpeg + SenseVoice 的视频处理引擎，支持从视频中提取音频并进行语音识别。

## 功能特性

### 支持的视频格式

- MP4 (最常用)
- AVI
- MKV
- MOV
- FLV
- WebM
- M4V
- WMV
- MPEG/MPG

### 核心功能

1. **音频提取**：使用 FFmpeg 从视频中提取音频
2. **语音识别**：复用 SenseVoice 引擎进行多语言语音识别
3. **说话人识别**：支持多说话人场景
4. **情感识别**：识别语音情感（中性、开心、愤怒、悲伤）
5. **时间戳对齐**：精确的时间轴信息

## 环境要求

### 1. FFmpeg（必需）

**Windows:**

```bash
# 使用 Chocolatey
choco install ffmpeg

# 或手动安装
# 1. 下载 FFmpeg: https://ffmpeg.org/download.html
# 2. 解压并添加到 PATH
```

**Linux:**

```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**

```bash
brew install ffmpeg
```

### 2. Python 依赖

```bash
# 音频处理依赖（如果尚未安装）
pip install funasr ffmpeg-python

# 检查环境
python backend/video_engines/check_environment.py
```

## 快速开始

### 1. 环境检查

```python
from backend.video_engines import get_engine

# 获取引擎实例
engine = get_engine()

# 检查 FFmpeg 是否可用
if engine.check_ffmpeg():
    print("✅ FFmpeg 已就绪")
else:
    print("❌ 请先安装 FFmpeg")
```

### 2. 处理视频

```python
from backend.video_engines import get_engine

# 初始化引擎
engine = get_engine()

# 处理视频
result = engine.parse(
    video_path='path/to/video.mp4',
    output_path='output_dir',
    language='auto',  # 自动检测语言
    use_itn=True,     # 启用数字归一化
    keep_audio=False  # 不保留临时音频文件
)

# 获取结果
print(f"Markdown: {result['markdown_file']}")
print(f"JSON: {result['json_file']}")
print(f"内容: {result['markdown']}")
```

### 3. 仅提取音频

```python
# 如果只需要提取音频
audio_path = engine.extract_audio(
    video_path='video.mp4',
    output_path='audio.wav',  # 可选
    audio_format='wav'        # wav/mp3/aac
)

print(f"音频已保存: {audio_path}")
```

### 4. 获取视频信息

```python
# 获取视频元信息
info = engine.get_video_info('video.mp4')
print(f"时长: {info['format']['duration']} 秒")
print(f"大小: {info['format']['size']} 字节")
```

## API 接口

### `VideoProcessingEngine.parse()`

主处理方法，完成视频 → 音频 → 文字的转换。

**参数：**

- `video_path` (str): 视频文件路径
- `output_path` (str): 输出目录
- `language` (str): 语言代码，默认 "auto"
  - `auto`: 自动检测
  - `zh`: 中文
  - `en`: 英文
  - `ja`: 日文
  - `ko`: 韩文
  - `yue`: 粤语
- `use_itn` (bool): 是否启用数字归一化，默认 True
- `keep_audio` (bool): 是否保留提取的音频文件，默认 False

**返回：**

```python
{
    'success': True,
    'output_path': 'output_dir',
    'markdown': '# 转写内容...',
    'markdown_file': 'output_dir/video.md',
    'json_file': 'output_dir/video.json',
    'json_data': {...},  # 结构化数据
    'result': {...}      # 原始 SenseVoice 结果
}
```

### `VideoProcessingEngine.extract_audio()`

从视频中提取音频。

**参数：**

- `video_path` (str): 视频文件路径
- `output_path` (str): 输出音频路径（可选）
- `audio_format` (str): 音频格式（wav/mp3/aac），默认 'wav'

**返回：**

- `str`: 提取的音频文件路径

### `VideoProcessingEngine.check_ffmpeg()`

检查 FFmpeg 是否可用。

**返回：**

- `bool`: True 表示 FFmpeg 可用

### `VideoProcessingEngine.get_video_info()`

获取视频详细信息（使用 ffprobe）。

**参数：**

- `video_path` (str): 视频文件路径

**返回：**

- `dict`: 视频元信息（格式、流、时长等）

## 输出格式

### 1. Markdown 格式

```markdown
# 语音转写：video.mp4

**原始文件**: video.mp4 (视频)
**视频格式**: MP4
**语言**: 🇨🇳 中文
**说话人数**: 2
**说话人**: SPEAKER_00, SPEAKER_01

## 完整文本

这里是完整的转写文本内容...

## 分段转写

**SPEAKER_00**:

[00:05] 大家好，欢迎来到今天的讲座...
[00:12] 😊 今天我们要讨论的主题是...

**SPEAKER_01**:

[01:23] 非常感谢，我有一个问题...
```

### 2. JSON 格式

```json
{
  "version": "1.0",
  "type": "video",
  "source": {
    "filename": "video.mp4",
    "file_type": "video",
    "video_format": "mp4",
    "original_filename": "video.mp4",
    "duration": 120.5
  },
  "metadata": {
    "language": "zh",
    "speakers": ["SPEAKER_00", "SPEAKER_01"],
    "speaker_count": 2,
    "segment_count": 15
  },
  "content": {
    "text": "完整转写文本...",
    "segments": [
      {
        "id": 0,
        "text": "大家好，欢迎来到今天的讲座",
        "start": 5.2,
        "end": 8.1,
        "speaker": "SPEAKER_00",
        "emotion": "NEUTRAL",
        "language": "zh"
      }
    ]
  }
}
```

## 工作流程

```
视频文件 (MP4/AVI/MKV...)
    ↓
[FFmpeg 提取音频]
    ↓
音频文件 (WAV, 16kHz, 单声道)
    ↓
[SenseVoice 语音识别]
    ↓
转写结果 (Markdown + JSON)
```

## 技术细节

### 音频提取参数

FFmpeg 使用以下参数优化语音识别效果：

- **编码**: PCM 16位 (`-acodec pcm_s16le`)
- **采样率**: 16kHz (`-ar 16000`) - 适合语音识别
- **声道**: 单声道 (`-ac 1`) - 减小文件体积
- **格式**: WAV - 无损压缩

### 性能优化

1. **临时文件管理**：默认自动清理临时音频文件
2. **流式处理**：大视频文件分段处理
3. **单例模式**：引擎复用，避免重复加载

## 故障排查

### 1. FFmpeg 未找到

```
❌ FFmpeg 未安装或未在 PATH 中
```

**解决方法**：

1. 确认 FFmpeg 已安装：`ffmpeg -version`
2. 将 FFmpeg 添加到系统 PATH
3. 重启终端/IDE

### 2. 音频提取失败

```
❌ FFmpeg failed with return code 1
```

**可能原因**：

- 视频文件损坏
- 视频格式不支持
- 磁盘空间不足

**解决方法**：

1. 使用 VLC 等播放器验证视频是否正常
2. 检查视频格式是否在支持列表中
3. 确保有足够的磁盘空间

### 3. 音频引擎加载失败

```
❌ 音频引擎加载失败
```

**解决方法**：

1. 确认已安装 FunASR：`pip install funasr`
2. 检查 SenseVoice 引擎是否正常
3. 运行环境检查：`python backend/video_engines/check_environment.py`

## 示例代码

### 完整示例

```python
from backend.video_engines import get_engine
from pathlib import Path

def process_video(video_path: str):
    """处理视频文件"""
    # 初始化引擎
    engine = get_engine()

    # 检查 FFmpeg
    if not engine.check_ffmpeg():
        raise RuntimeError("FFmpeg 未安装")

    # 创建输出目录
    output_dir = Path('output') / Path(video_path).stem
    output_dir.mkdir(parents=True, exist_ok=True)

    # 处理视频
    result = engine.parse(
        video_path=video_path,
        output_path=str(output_dir),
        language='auto',
        use_itn=True
    )

    # 打印结果
    print(f"✅ 处理完成!")
    print(f"📄 Markdown: {result['markdown_file']}")
    print(f"📄 JSON: {result['json_file']}")

    return result

# 使用示例
if __name__ == '__main__':
    result = process_video('example.mp4')
    print(result['markdown'])
```

### 批量处理

```python
from backend.video_engines import get_engine
from pathlib import Path

def batch_process_videos(video_dir: str):
    """批量处理视频文件"""
    engine = get_engine()
    video_dir = Path(video_dir)

    # 查找所有视频文件
    video_files = []
    for ext in engine.SUPPORTED_FORMATS:
        video_files.extend(video_dir.glob(f'*{ext}'))

    print(f"找到 {len(video_files)} 个视频文件")

    # 逐个处理
    results = []
    for video_file in video_files:
        print(f"处理: {video_file.name}")
        try:
            result = engine.parse(
                video_path=str(video_file),
                output_path=f'output/{video_file.stem}'
            )
            results.append(result)
            print(f"✅ {video_file.name} 完成")
        except Exception as e:
            print(f"❌ {video_file.name} 失败: {e}")

    return results

# 使用示例
batch_process_videos('videos/')
```

## 集成到 API Server

视频处理引擎已集成到主 API Server，可以通过以下方式使用：

### 提交视频处理任务

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -F "file=@video.mp4" \
  -F "backend=video" \
  -F "lang=auto"
```

### 查询任务状态

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

## 参考资料

- [FFmpeg 官方文档](https://ffmpeg.org/documentation.html)
- [SenseVoice 引擎](../audio_engines/README.md)
- [FunASR 文档](https://github.com/alibaba-damo-academy/FunASR)
