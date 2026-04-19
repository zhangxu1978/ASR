# Qwen3-ASR 歌词识别应用

基于 Qwen3-ASR 的智能歌词识别 Web 应用，支持上传歌曲自动识别歌词，并生成 LRC、SRT 格式字幕文件。

## 功能特点

- 🎵 **音频上传** - 支持 MP3, WAV, M4A, FLAC, OGG 等常见音频格式
- 🎤 **歌词识别** - 使用 Qwen3-ASR 0.6B 模型，CPU 即可运行
- ⏱️ **时间戳对齐** - 精确到毫秒级的时间戳
- 📄 **多格式导出** - 支持 LRC（卡拉OK）和 SRT（视频字幕）格式
- ▶️ **同步播放** - 带歌词的音频播放器，歌词自动滚动高亮
- 🌍 **多语言支持** - 中文、英文、日语、韩语等

## 项目结构

```
webapp/
├── main.py              # FastAPI 后端服务
├── lyrics_generator.py  # 歌词生成核心模块
├── requirements.txt     # Python 依赖
├── start.bat          # Windows 启动脚本
├── templates/
│   └── index.html     # 前端页面
├── static/            # 静态资源目录
├── uploads/           # 上传文件临时目录
└── output/            # 生成的歌词文件目录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# Windows
start.bat

# 或手动启动
python main.py
```

### 3. 访问应用

打开浏览器访问: http://localhost:8000

## API 接口

### POST /api/lyrics

上传音频文件并生成歌词

**参数:**
- `file`: 音频文件 (multipart/form-data)
- `language`: 语言，默认 "Chinese"

**返回:**
```json
{
  "success": true,
  "file_id": "abc123",
  "text": "完整歌词文本",
  "urls": {
    "lrc": "/download/abc123.lrc",
    "srt": "/download/abc123.srt",
    "json": "/download/abc123.json"
  },
  "timestamps": [
    {"word": "清", "start": 44.0, "end": 44.24},
    ...
  ]
}
```

### GET /download/{filename}

下载生成的歌词文件

## 使用说明

1. **上传音频**: 点击上传区域，选择歌曲文件
2. **选择语言**: 根据歌曲语言选择对应选项
3. **开始识别**: 点击"识别歌词"按钮
4. **等待结果**: 首次运行需要加载模型（约3-5分钟）
5. **查看和下载**: 识别完成后可查看歌词、播放歌曲、下载字幕文件

## 技术栈

- **后端**: FastAPI + Python
- **前端**: HTML5 + CSS3 + Vanilla JavaScript
- **模型**: Qwen3-ASR-0.6B + Qwen3-ForcedAligner-0.6B
- **推理**: PyTorch CPU 推理

## 注意事项

- 首次运行需要下载模型（约 3GB）
- CPU 推理较慢，一首 4 分钟歌曲约需 5-10 分钟
- 建议使用耳机收听，避免背景音乐干扰识别
- 识别结果可能受歌曲类型、音质影响

## License

MIT
