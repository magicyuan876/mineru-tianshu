# Audio Processing Engines

## SenseVoice 语音识别引擎

基于阿里达摩院的 SenseVoiceSmall 模型，支持多语言识别和说话人识别。

**核心特性**：

- ✅ 多语言识别（中文/英文/日文/韩文/粤语）
- ✅ 说话人识别（自动区分不同说话人）
- ✅ 情感识别（中性 😐/开心 😊/生气 😠/悲伤 😢）
- ✅ 事件检测（语音 💬/掌声 👏/音乐 🎵/笑声 😄）
- ✅ 智能语言检测（基于文本内容而非标签）
- ✅ Emoji 可视化（标签自动转换为 emoji）
- ✅ 时间戳对齐
- ✅ GPU 加速

---

## 安装依赖

音频处理依赖已添加到 `backend/requirements.txt`，运行项目的安装脚本即可：

```bash
cd backend
./install.sh  # Linux/WSL
```

额外需要的系统依赖：

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

**环境检查**：

```bash
python backend/audio_engines/check_environment.py
```

---

## 使用方法

```python
from audio_engines import SenseVoiceEngine

# 初始化引擎
engine = SenseVoiceEngine()

# 处理音频
result = engine.parse(
    audio_path="meeting.mp3",
    output_path="./output",
    language="auto"  # 自动检测语言
)

# 获取结果
json_data = result['json_data']
print(f"说话人: {json_data['metadata']['speakers']}")
print(f"文本: {json_data['content']['text']}")
```

---

## 输出格式

### JSON 格式（包含说话人信息）

```json
{
  "version": "1.0",
  "type": "audio",
  "metadata": {
    "language": "zh",
    "speakers": ["SPEAKER_00", "SPEAKER_01"],
    "speaker_count": 2
  },
  "content": {
    "text": "完整文本",
    "segments": [
      {
        "id": 0,
        "text": "大家好",
        "start": 0.0,
        "end": 2.5,
        "speaker": "SPEAKER_00",
        "emotion": "NEUTRAL",
        "language": "zh"
      }
    ]
  }
}
```

---

## API 参考

### `parse(audio_path, output_path, language, use_itn)`

**参数**：

- `audio_path` (str): 音频文件路径
- `output_path` (str): 输出目录
- `language` (str): 语言代码 (auto/zh/en/ja/ko/yue)，默认 "auto"
- `use_itn` (bool): 使用逆文本归一化，默认 True

**返回**：包含 JSON 和 Markdown 格式结果的字典

---

## 参考资源

- [SenseVoice 模型](https://www.modelscope.cn/models/iic/SenseVoiceSmall)
- [FunASR 框架](https://github.com/alibaba-damo-academy/FunASR)
