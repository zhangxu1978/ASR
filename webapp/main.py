"""
歌词识别API服务
基于 Qwen3-ASR 的歌曲歌词识别后端
"""
import os
import json
import uuid
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lyrics_generator import get_generator

# 创建 FastAPI 应用
app = FastAPI(
    title="歌词识别API",
    description="基于 Qwen3-ASR 的歌曲歌词识别服务",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路径配置
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
DATA_FILE = BASE_DIR / "data.json"

# 确保目录存在
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 请求模型
class LyricsRequest(BaseModel):
    language: Optional[str] = "Chinese"

# 数据管理
class DataManager:
    def __init__(self, data_file):
        self.data_file = data_file
        self.data = self.load_data()
    
    def load_data(self):
        """加载数据"""
        if not self.data_file.exists():
            return []
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def save_data(self):
        """保存数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_file(self, file_info):
        """添加文件信息"""
        self.data.append(file_info)
        self.save_data()
        return file_info
    
    def get_file(self, file_id):
        """获取文件信息"""
        for file in self.data:
            if file['id'] == file_id:
                return file
        return None
    
    def update_file(self, file_id, updates):
        """更新文件信息"""
        for i, file in enumerate(self.data):
            if file['id'] == file_id:
                self.data[i].update(updates)
                self.save_data()
                return self.data[i]
        return None
    
    def delete_file(self, file_id):
        """删除文件信息"""
        for i, file in enumerate(self.data):
            if file['id'] == file_id:
                deleted_file = self.data.pop(i)
                self.save_data()
                return deleted_file
        return None
    
    def get_all_files(self):
        """获取所有文件信息"""
        return self.data

# 初始化数据管理器
data_manager = DataManager(DATA_FILE)

@app.get("/")
async def index():
    """返回主页"""
    return FileResponse(str(BASE_DIR / "templates" / "index.html"))

@app.get("/library")
async def library():
    """返回音频文件管理页面"""
    return FileResponse(str(BASE_DIR / "templates" / "library.html"))

@app.post("/api/lyrics")
async def generate_lyrics(
    file: UploadFile = File(...),
    language: str = "Chinese"
):
    """
    上传歌曲文件，生成歌词（完整版，生成LRC、SRT、JSON）

    Args:
        file: 音频文件 (mp3, wav, m4a, flac 等)
        language: 语言 (Chinese, English 等)

    Returns:
        JSON: 包含歌词信息和下载链接
    """
    allowed_extensions = {'mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac', 'wma'}
    file_ext = file.filename.split('.')[-1].lower() if file.filename else ''

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}。支持的格式: {', '.join(allowed_extensions)}"
        )

    file_id = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{file_id}.{file_ext}"

    try:
        contents = await file.read()
        with open(upload_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    generator = get_generator()
    result = generator.generate_lyrics(
        audio_path=str(upload_path),
        output_dir=str(OUTPUT_DIR),
        language=language
    )

    try:
        os.remove(upload_path)
    except:
        pass

    if result['success']:
        return JSONResponse({
            'success': True,
            'file_id': result['file_id'],
            'text': result['text'],
            'urls': {
                'lrc': result['lrc_url'],
                'srt': result['srt_url'],
                'json': result['json_url']
            },
            'timestamps': result['timestamps']
        })
    else:
        raise HTTPException(
            status_code=500,
            detail=f"歌词生成失败: {result.get('error', '未知错误')}"
        )

@app.post("/api/lyrics-json/{file_id}")
async def recognize_for_edit(
    file_id: str
):
    """
    识别歌词用于校对（只生成JSON，不生成LRC/SRT）

    Args:
        file_id: 文件ID

    Returns:
        JSON: 包含歌词JSON数据和句子分组
    """
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = BASE_DIR / file_info['file_path']
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    generator = get_generator()
    result = generator.generate_lyrics_json(
        audio_path=str(file_path),
        output_dir=str(OUTPUT_DIR),
        language="Chinese"
    )

    if result['success']:
        updates = {
            'recognized': True,
            'timestamps_lyrics': result['json_url'].replace('/download/', ''),
            'lrc_lyrics': None,
            'srt_lyrics': None
        }
        data_manager.update_file(file_id, updates)

        return JSONResponse({
            'success': True,
            'file_id': result['file_id'],
            'text': result['text'],
            'sentences': result['sentences'],
            'timestamps': result['timestamps'],
            'json_url': result['json_url']
        })
    else:
        raise HTTPException(
            status_code=500,
            detail=f"歌词识别失败: {result.get('error', '未知错误')}"
        )

@app.post("/api/export-lyrics/{file_id}")
async def export_lyrics(
    file_id: str,
    request: Request
):
    """
    从JSON歌词导出LRC/SRT格式

    Args:
        file_id: 文件ID
        request: 请求对象，包含格式类型

    Returns:
        JSON: 导出结果
    """
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        body = await request.json()
        export_format = body.get('format', 'lrc')
    except:
        export_format = 'lrc'

    json_path = OUTPUT_DIR / file_info['timestamps_lyrics']
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="歌词JSON文件不存在")

    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    sentences = json_data.get('lyrics', [])

    if export_format == 'lrc':
        content = _generate_lrc_from_json(sentences)
        filename = f"{file_id}.lrc"
    else:
        content = _generate_srt_from_json(sentences)
        filename = f"{file_id}.srt"

    output_path = OUTPUT_DIR / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    updates = {}
    if export_format == 'lrc':
        updates['lrc_lyrics'] = filename
    else:
        updates['srt_lyrics'] = filename
    data_manager.update_file(file_id, updates)

    return JSONResponse({
        'success': True,
        'message': f'{export_format.upper()}导出成功',
        'url': f"/download/{filename}"
    })

def _generate_lrc_from_json(sentences: list) -> str:
    """从JSON数据生成LRC格式"""
    lines = []
    lines.append("[ti:自动生成歌词]")
    lines.append("[ar:未知]")
    lines.append("[al:未知]")
    lines.append("[by:Qwen3-ASR]")
    lines.append("")

    for item in sentences:
        start = item['start']
        text = item.get('text', item.get('word', ''))
        if not text:
            continue
        minutes = int(start // 60)
        seconds = start % 60
        time_str = f"{minutes:02d}:{seconds:05.2f}"
        lines.append(f"[{time_str}]{text}")

    return '\n'.join(lines)

def _generate_srt_from_json(sentences: list) -> str:
    """从JSON数据生成SRT格式"""
    lines = []
    index = 1

    for item in sentences:
        start = item['start']
        end = item.get('end', start + 3)
        text = item.get('text', item.get('word', ''))
        if not text:
            continue

        start_str = _format_srt_time(start)
        end_str = _format_srt_time(end)
        lines.append(str(index))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(text)
        lines.append("")
        index += 1

    return '\n'.join(lines)

def _format_srt_time(seconds: float) -> str:
    """格式化SRT时间"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

@app.post("/api/save-lyrics/{file_id}")
async def save_lyrics(file_id: str, request: Request):
    """
    保存修改后的歌词JSON

    Args:
        file_id: 文件ID
        request: 请求对象，包含歌词内容

    Returns:
        JSON: 保存结果
    """
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        body = await request.json()
        lyrics_content = body.get('lyrics')
    except:
        raise HTTPException(status_code=400, detail="请求参数错误")

    if not lyrics_content:
        raise HTTPException(status_code=400, detail="歌词内容不能为空")

    filename = file_info.get('timestamps_lyrics', f"{file_id}.json")
    output_path = OUTPUT_DIR / filename

    json_data = {
        'lyrics': lyrics_content,
        'full_text': ''.join(item.get('text', item.get('word', '')) for item in lyrics_content)
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        return JSONResponse({
            'success': True,
            'message': '歌词保存成功',
            'json_url': f"/download/{filename}"
        })
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"歌词保存失败: {str(e)}"
        )

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...)
):
    """
    上传音频文件到库
    
    Args:
        file: 音频文件
    
    Returns:
        JSON: 上传结果
    """
    # 验证文件类型
    allowed_extensions = {'mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac', 'wma'}
    file_ext = file.filename.split('.')[-1].lower() if file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}。支持的格式: {', '.join(allowed_extensions)}"
        )
    
    # 生成唯一文件名
    file_id = uuid.uuid4().hex
    file_name = file.filename
    file_size = 0
    
    # 保存上传的文件
    upload_path = UPLOAD_DIR / f"{file_id}.{file_ext}"
    try:
        contents = await file.read()
        file_size = len(contents)
        with open(upload_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 添加文件信息到数据
    file_info = {
        'id': file_id,
        'name': file_name,
        'duration': 0,  # 稍后计算
        'size': file_size,
        'recognized': False,
        'original_lyrics': None,
        'timestamps_lyrics': None,
        'lrc_lyrics': None,
        'srt_lyrics': None,
        'ai_corrected_srt': None,
        'ai_corrected_lrc': None,
        'upload_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'file_path': str(upload_path.relative_to(BASE_DIR))
    }
    
    # 保存到数据管理
    data_manager.add_file(file_info)
    
    return JSONResponse({
        'success': True,
        'file_id': file_id,
        'message': '文件上传成功'
    })

@app.get("/api/files")
async def get_files():
    """
    获取所有文件列表

    Returns:
        JSON: 文件列表
    """
    files = data_manager.get_all_files()
    for file in files:
        if file.get('file_path'):
            file['file_path_exists'] = (BASE_DIR / file['file_path']).exists()
        else:
            file['file_path_exists'] = False
    return JSONResponse({
        'success': True,
        'files': files
    })

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """
    删除文件

    Args:
        file_id: 文件ID

    Returns:
        JSON: 删除结果
    """
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        if 'file_path' in file_info and file_info['file_path']:
            file_path = BASE_DIR / file_info['file_path']
            if file_path.exists():
                os.remove(file_path)

        for key in ['original_lyrics', 'timestamps_lyrics', 'lrc_lyrics', 'srt_lyrics', 'ai_corrected_srt', 'ai_corrected_lrc']:
            if key in file_info and file_info[key]:
                file_path = OUTPUT_DIR / file_info[key]
                if file_path.exists():
                    os.remove(file_path)

        data_manager.delete_file(file_id)

        return JSONResponse({
            'success': True,
            'message': '文件删除成功'
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")

@app.get("/api/audio/{file_id}")
async def get_audio(file_id: str):
    """
    获取音频文件
    
    Args:
        file_id: 文件ID
    
    Returns:
        FileResponse: 音频文件
    """
    # 获取文件信息
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 构建文件路径
    file_path = BASE_DIR / file_info['file_path']
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=file_info['name']
    )

@app.post("/api/recognize/{file_id}")
async def recognize_lyrics(file_id: str):
    """
    识别音频文件的歌词
    
    Args:
        file_id: 文件ID
    
    Returns:
        JSON: 识别结果
    """
    # 获取文件信息
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 构建文件路径
    file_path = BASE_DIR / file_info['file_path']
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 生成歌词
    generator = get_generator()
    result = generator.generate_lyrics(
        audio_path=str(file_path),
        output_dir=str(OUTPUT_DIR),
        language="Chinese"
    )
    
    if result['success']:
        # 更新文件信息
        updates = {
            'recognized': True,
            'lrc_lyrics': result['lrc_url'].replace('/download/', ''),
            'srt_lyrics': result['srt_url'].replace('/download/', ''),
            'timestamps_lyrics': result['json_url'].replace('/download/', '')
        }
        data_manager.update_file(file_id, updates)
        
        return JSONResponse({
            'success': True,
            'message': '歌词识别成功'
        })
    else:
        raise HTTPException(
            status_code=500,
            detail=f"歌词生成失败: {result.get('error', '未知错误')}"
        )

@app.post("/api/upload-lyrics/{file_id}")
async def upload_original_lyrics(
    file_id: str,
    file: UploadFile = File(...)
):
    """
    上传原始歌词文件
    
    Args:
        file_id: 文件ID
        file: 歌词文件
    
    Returns:
        JSON: 上传结果
    """
    # 获取文件信息
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 保存歌词文件
    file_ext = file.filename.split('.')[-1].lower() if file.filename else ''
    lyrics_path = OUTPUT_DIR / f"{file_id}_original.{file_ext}"
    
    try:
        contents = await file.read()
        with open(lyrics_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 更新文件信息 - 只保存文件名，不包含路径
    updates = {
        'original_lyrics': f"{file_id}_original.{file_ext}"
    }
    data_manager.update_file(file_id, updates)
    
    return JSONResponse({
        'success': True,
        'message': '歌词上传成功'
    })

@app.post("/api/ai-correct/{file_id}")
async def ai_correct_lyrics(file_id: str, request: Request):
    """
    AI校对歌词
    
    Args:
        file_id: 文件ID
        request: 请求对象，包含校对类型
    
    Returns:
        JSON: 校对结果
    """
    # 获取文件信息
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查是否有原始歌词
    if not file_info.get('original_lyrics'):
        raise HTTPException(status_code=400, detail="请先上传原始歌词")
    
    # 解析请求参数
    try:
        body = await request.json()
        correct_type = body.get('type', 'srt')
    except:
        correct_type = 'srt'
    
    # 检查是否有对应的识别歌词
    if correct_type == 'srt' and not file_info.get('srt_lyrics'):
        raise HTTPException(status_code=400, detail="请先识别SRT歌词")
    if correct_type == 'lrc' and not file_info.get('lrc_lyrics'):
        raise HTTPException(status_code=400, detail="请先识别LRC歌词")
    
    # 读取原始歌词
    original_lyrics_path = OUTPUT_DIR / file_info['original_lyrics']
    if not original_lyrics_path.exists():
        raise HTTPException(status_code=404, detail="原始歌词文件不存在")
    
    with open(original_lyrics_path, 'r', encoding='utf-8') as f:
        original_lyrics = f.read()
    
    # 读取识别的歌词
    if correct_type == 'srt':
        recognized_lyrics_path = OUTPUT_DIR / file_info['srt_lyrics']
        output_suffix = '_ai.srt'
    else:
        recognized_lyrics_path = OUTPUT_DIR / file_info['lrc_lyrics']
        output_suffix = '_ai.lrc'
    
    if not recognized_lyrics_path.exists():
        raise HTTPException(status_code=404, detail="识别歌词文件不存在")
    
    with open(recognized_lyrics_path, 'r', encoding='utf-8') as f:
        recognized_lyrics = f.read()
    
    # 构建提示词
    prompt = f"""我有一份原始歌词和一份通过ASR识别出来的歌词，我希望你能根据识别歌词让原始歌词成为带着时间戳的歌词。

原始歌词：
{original_lyrics}

ASR识别的{correct_type.upper()}歌词：
{recognized_lyrics}

请根据ASR识别的时间戳，将原始歌词重新组织成{correct_type.upper()}格式的歌词。保持识别歌词中的时间戳信息，智能的根据原始歌词的内容和顺序，猜出时间轴上原始歌词的位置。

只返回{correct_type.upper()}格式的歌词内容，不要包含其他解释或说明。"""
    
    # 调用本地大模型
    try:
        ai_response = await call_local_llm(prompt)
        
        # 保存优化后的歌词
        output_filename = f"{file_id}{output_suffix}"
        output_path = OUTPUT_DIR / output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ai_response)
        
        # 更新文件信息
        updates = {}
        if correct_type == 'srt':
            updates['ai_corrected_srt'] = output_filename
        else:
            updates['ai_corrected_lrc'] = output_filename
        
        data_manager.update_file(file_id, updates)
        
        return JSONResponse({
            'success': True,
            'message': f'AI校对完成！已生成优化后的{correct_type.upper()}歌词'
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI校对失败: {str(e)}"
        )


async def call_local_llm(prompt: str) -> str:
    """
    调用本地大模型
    
    Args:
        prompt: 提示词
    
    Returns:
        str: 模型响应
    """
    import httpx
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://localhost:3100/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "X-Model-ID": "bendi"
            },
            json={
                 "model":"bendi",
                "stream": False,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 8000,
                "temperature": 0.7
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"大模型调用失败: {response.status_code} - {response.text}")

@app.get("/compare/{file_id}")
async def compare_lyrics_page(file_id: str):
    """
    歌词对比页面
    
    Args:
        file_id: 文件ID
    
    Returns:
        FileResponse: 对比页面
    """
    # 检查文件是否存在
    file_info = data_manager.get_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(str(BASE_DIR / "templates" / "compare.html"))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """下载歌词文件"""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        # 检查是否在uploads目录
        upload_path = UPLOAD_DIR / filename
        if upload_path.exists():
            file_path = upload_path
        else:
            raise HTTPException(status_code=404, detail="文件不存在")
    
    # 确定文件类型
    if filename.endswith('.lrc'):
        media_type = "text/plain"
    elif filename.endswith('.srt'):
        media_type = "text/plain"
    elif filename.endswith('.json'):
        media_type = "application/json"
    elif any(filename.endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma']):
        media_type = "audio/mpeg"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )

@app.get("/api/status")
async def status():
    """检查服务状态"""
    return {
        'status': 'running',
        'model_loaded': True
    }

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
