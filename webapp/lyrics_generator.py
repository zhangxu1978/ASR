"""
歌词生成核心模块
使用 Qwen3-ASR + ForcedAligner 生成带时间戳的歌词
"""
import os
import re
import uuid
import traceback
import gc
import torch
from qwen_asr import Qwen3ASRModel, Qwen3ForcedAligner


class LyricsGenerator:
    """歌词生成器"""
    
    def __init__(self, asr_model_path: str, aligner_model_path: str):
        """
        初始化歌词生成器
        
        Args:
            asr_model_path: ASR模型路径
            aligner_model_path: ForcedAligner模型路径
        """
        self.asr_model_path = asr_model_path
        self.aligner_model_path = aligner_model_path
        self.asr_model = None
        self.aligner = None
        self._models_loaded = False
    
    def _load_models(self):
        """懒加载模型"""
        if not self._models_loaded:
            print("加载 ASR 模型...")
            self.asr_model = Qwen3ASRModel.from_pretrained(self.asr_model_path)
            print("加载 ForcedAligner 模型...")
            self.aligner = Qwen3ForcedAligner.from_pretrained(self.aligner_model_path)
            self._models_loaded = True
            print("模型加载完成!")
    
    def _unload_models(self):
        """卸载模型并释放内存"""
        if self._models_loaded:
            print("卸载模型并释放内存...")
            
            # 清理 ASR 模型
            if self.asr_model is not None:
                del self.asr_model
                self.asr_model = None
            
            # 清理 Aligner 模型
            if self.aligner is not None:
                del self.aligner
                self.aligner = None
            
            # 清理 GPU 缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # 强制垃圾回收
            gc.collect()
            
            self._models_loaded = False
            print("模型已卸载，内存已释放!")
    
    def generate_lyrics(self, audio_path: str, output_dir: str, language: str = "Chinese") -> dict:
        """
        生成歌词文件
        
        Args:
            audio_path: 音频文件路径
            output_dir: 输出目录
            language: 语言 (Chinese, English 等)
        
        Returns:
            dict: 包含生成结果的字典
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成唯一ID
        file_id = uuid.uuid4().hex[:8]
        
        # 输出文件路径
        lrc_path = os.path.join(output_dir, f"{file_id}.lrc")
        srt_path = os.path.join(output_dir, f"{file_id}.srt")
        json_path = os.path.join(output_dir, f"{file_id}.json")
        
        # 加载模型
        self._load_models()
        
        try:
            # 第一步：识别歌词文本
            print("识别歌词文本...")
            asr_result = self.asr_model.transcribe(
                audio=audio_path,
                language=language
            )
            recognized_text = asr_result[0].text
            
            # 第二步：对齐时间戳
            print("对齐时间戳...")
            align_result = self.aligner.align(
                audio=audio_path,
                text=recognized_text,
                language=language
            )[0]
            
            # 第三步：生成歌词文件
            print("生成歌词文件...")
            self._export_lrc(align_result, lrc_path)
            self._export_srt(align_result, srt_path)
            self._export_json(align_result, json_path)
            
            result = {
                'success': True,
                'file_id': file_id,
                'text': recognized_text,
                'lrc_path': lrc_path,
                'srt_path': srt_path,
                'json_path': json_path,
                'lrc_url': f"/download/{file_id}.lrc",
                'srt_url': f"/download/{file_id}.srt",
                'json_url': f"/download/{file_id}.json",
                'timestamps': self._get_timestamps_list(align_result)
            }
            
            # 识别完成后立即释放模型
            self._unload_models()
            
            return result
            
        except Exception as e:
            # 即使出错也要释放内存
            self._unload_models()
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _get_timestamps_list(self, align_result) -> list:
        """获取时间戳列表"""
        timestamps = []
        for item in align_result.items:
            timestamps.append({
                'word': item.text,
                'start': item.start_time,
                'end': item.end_time
            })
        return timestamps
    
    def _export_lrc(self, align_result, output_path: str):
        """导出 LRC 格式"""
        lines = []
        lines.append("[ti:自动生成歌词]")
        lines.append("[ar:未知]")
        lines.append("[al:未知]")
        lines.append("[by:Qwen3-ASR]")
        lines.append("")
        
        # 合并成句子
        current_line = ""
        current_start = 0
        
        for item in align_result.items:
            word = item.text
            # 只有当开始新行时才设置开始时间
            if not current_line:
                current_start = item.start_time
            current_line += word
            
            # 遇到标点或长度足够时断开
            if word in ['。', '，', '！', '？', '、'] or len(current_line) >= 15:
                minutes = int(current_start // 60)
                seconds = current_start % 60
                time_str = f"{minutes:02d}:{seconds:05.2f}"
                lines.append(f"[{time_str}]{current_line}")
                current_line = ""
        
        # 处理最后一行
        if current_line:
            minutes = int(current_start // 60)
            seconds = current_start % 60
            time_str = f"{minutes:02d}:{seconds:05.2f}"
            lines.append(f"[{time_str}]{current_line}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _export_srt(self, align_result, output_path: str):
        """导出 SRT 格式"""
        lines = []
        
        # 合并成句子
        current_line = ""
        current_start = 0
        current_end = 0
        subtitle_index = 1
        
        for item in align_result.items:
            word = item.text
            # 只有当开始新行时才设置开始时间
            if not current_line:
                current_start = item.start_time
            current_line += word
            current_end = item.end_time
            
            # 遇到标点或长度足够时断开
            if word in ['。', '，', '！', '？', '、'] or len(current_line) >= 15:
                start_str = self._format_srt_time(current_start)
                end_str = self._format_srt_time(current_end)
                
                lines.append(str(subtitle_index))
                lines.append(f"{start_str} --> {end_str}")
                lines.append(current_line)
                lines.append("")
                
                subtitle_index += 1
                current_line = ""
        
        # 处理最后一行
        if current_line:
            start_str = self._format_srt_time(current_start)
            end_str = self._format_srt_time(current_end)
            
            lines.append(str(subtitle_index))
            lines.append(f"{start_str} --> {end_str}")
            lines.append(current_line)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _export_json(self, align_result, output_path: str):
        """导出 JSON 格式（逐字时间戳）"""
        import json
        
        data = {
            'lyrics': [],
            'full_text': ''
        }
        
        words = []
        for item in align_result.items:
            words.append(item.text)
            data['lyrics'].append({
                'word': item.text,
                'start': round(item.start_time, 2),
                'end': round(item.end_time, 2)
            })
        
        data['full_text'] = ''.join(words)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """格式化 SRT 时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# 全局实例
_generator = None

def get_generator() -> LyricsGenerator:
    """获取歌词生成器实例"""
    global _generator
    if _generator is None:
        asr_path = r"D:\work\work\git\tools\ASR\Qwen3-ASR-0.6B"
        aligner_path = r"D:\work\work\git\tools\ASR\Qwen3-ForcedAligner-0.6B"
        _generator = LyricsGenerator(asr_path, aligner_path)
    return _generator
