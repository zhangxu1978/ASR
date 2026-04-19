"""
Qwen3-ASR + ForcedAligner 歌词时间戳识别
两步法：1. 先识别歌词文本  2. 再对齐时间戳
"""
from qwen_asr import Qwen3ASRModel, Qwen3ForcedAligner
import os

# 配置路径
AUDIO_FILE = r"D:\work\work\git\tools\ASR\sound\回声在草原上.mp3"
ASR_MODEL_PATH = r"D:\work\work\git\tools\ASR\Qwen3-ASR-0.6B"
ALIGNER_MODEL_PATH = r"D:\work\work\git\tools\ASR\Qwen3-ForcedAligner-0.6B"
OUTPUT_FILE = r"D:\work\work\git\tools\ASR\sound\歌词时间戳.txt"

print("=" * 60)
print("歌词时间戳识别 (两步法)")
print("=" * 60)

# 第一步：加载 ASR 模型识别文本
print("\n[1/4] 加载 ASR 模型...")
asr_model = Qwen3ASRModel.from_pretrained(ASR_MODEL_PATH)
print("      ASR 模型加载完成!")

print("\n[2/4] 识别歌词文本...")
asr_result = asr_model.transcribe(
    audio=AUDIO_FILE,
    language="Chinese"
)
recognized_text = asr_result[0].text
print(f"      识别文本: {recognized_text}")
print("      文本识别完成!")

# 第二步：加载 ForcedAligner 对齐时间戳
print("\n[3/4] 加载 ForcedAligner 模型...")
aligner = Qwen3ForcedAligner.from_pretrained(ALIGNER_MODEL_PATH)
print("      ForcedAligner 模型加载完成!")

print("\n[4/4] 进行时间戳对齐...")
align_result = aligner.align(
    audio=AUDIO_FILE,
    text=recognized_text,
    language="Chinese"
)[0]  # 取第一个结果

# 输出结果
print("\n" + "=" * 60)
print("识别结果")
print("=" * 60)

lines = []
lines.append("=" * 60)
lines.append("歌词时间戳结果")
lines.append("=" * 60)
lines.append(f"音频文件: {AUDIO_FILE}")
lines.append(f"模型: Qwen3-ASR-0.6B + Qwen3-ForcedAligner-0.6B")
lines.append("-" * 60)

# 原始识别文本
lines.append("")
lines.append("【完整歌词】")
lines.append(recognized_text)
lines.append("")

# 逐字时间戳
lines.append("")
lines.append("【逐字时间戳】")
lines.append("")

print("\n逐字时间戳:")
# 遍历 align_result.items
for item in align_result.items:
    word = item.text if hasattr(item, 'text') else str(item)
    start = item.start_time if hasattr(item, 'start_time') else 0
    end = item.end_time if hasattr(item, 'end_time') else 0
    
    start_time = f"{int(start // 60):02d}:{start % 60:05.2f}"
    end_time = f"{int(end // 60):02d}:{end % 60:05.2f}"
    
    line = f"[{start_time} → {end_time}] {word}"
    lines.append(line)
    print(f"  {line}")

# 计算总时长
total_duration = max([item.end_time for item in align_result.items]) if align_result.items else 0

# 保存
lines.append("")
lines.append("-" * 60)
lines.append(f"总时长: {total_duration:.2f} 秒")

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("-" * 60)
print(f"\n✅ 结果已保存到: {OUTPUT_FILE}")
