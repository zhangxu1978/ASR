"""
Qwen3-ASR 0.6B CPU 歌词识别测试
使用方法：python test_asr.py <音频文件路径>
"""
import torch
from qwen_asr import Qwen3ASRModel

def main():
    print("=" * 50)
    print("Qwen3-ASR 0.6B CPU 歌词识别")
    print("=" * 50)

    # 加载模型 (CPU)
    print("\n[1/3] 正在加载模型...")
    model = Qwen3ASRModel.from_pretrained(
        "Qwen/Qwen3-ASR-0.6B",
        dtype=torch.float32,  # CPU 用 float32
        device_map="cpu",
        max_new_tokens=256,
    )
    print("✅ 模型加载完成！")

    # 识别音频
    print("\n[2/3] 请输入音频文件路径：")
    audio_path = input("> ").strip().strip('"').strip("'")

    if not audio_path:
        print("❌ 未提供音频文件路径")
        return

    print(f"\n[3/3] 正在识别: {audio_path}")
    results = model.transcribe(
        audio=audio_path,
        language=None,  # 自动检测语言
    )

    print("\n" + "=" * 50)
    print("识别结果：")
    print("=" * 50)
    print(f"语言: {results[0].language}")
    print(f"歌词: {results[0].text}")
    print("=" * 50)

if __name__ == "__main__":
    main()
