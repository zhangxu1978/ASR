"""
Qwen3-ASR 0.6B CPU 歌词识别测试
"""
import torch
from qwen_asr import Qwen3ASRModel

print("=" * 50)
print("Qwen3-ASR 0.6B CPU 歌词识别")
print("=" * 50)

# 加载模型 (CPU)
print("\n[1/3] 正在加载模型...")
model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-0.6B",
    dtype=torch.float32,
    device_map="cpu",
    max_new_tokens=1024,  # 歌词较长，增加token
)
print("✅ 模型加载完成！")

# 识别音频
audio_path = r"D:\work\work\git\tools\ASR\sound\回声在草原上.mp3"
print(f"\n[2/3] 正在识别: {audio_path}")

results = model.transcribe(
    audio=audio_path,
    language=None,  # 自动检测语言
)

print("\n" + "=" * 50)
print("识别结果：")
print("=" * 50)
print(f"语言: {results[0].language}")
print(f"歌词:\n{results[0].text}")
print("=" * 50)

# 保存结果
output_path = r"D:\work\work\git\tools\ASR\sound\歌词结果.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(f"语言: {results[0].language}\n\n歌词:\n{results[0].text}")
print(f"\n✅ 结果已保存到: {output_path}")
