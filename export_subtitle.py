"""
导出 LRC 和 SRT 字幕格式
从时间戳歌词数据生成两种字幕文件
"""
import re

# 读取时间戳数据
INPUT_FILE = r"D:\work\work\git\tools\ASR\sound\歌词时间戳.txt"
LRC_OUTPUT = r"D:\work\work\git\tools\ASR\sound\歌词.lrc"
SRT_OUTPUT = r"D:\work\work\git\tools\ASR\sound\歌词.srt"

print("=" * 60)
print("导出字幕格式")
print("=" * 60)

# 读取时间戳数据
with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 解析时间戳
timestamps = []
pattern = r'\[(\d{2}):(\d{2})\.(\d{2,3}) → (\d{2}):(\d{2})\.(\d{2,3})\] (.+)'

for match in re.finditer(pattern, content):
    start_min = int(match.group(1))
    start_sec = int(match.group(2))
    start_ms_str = match.group(3)
    end_min = int(match.group(4))
    end_sec = int(match.group(5))
    end_ms_str = match.group(6)
    word = match.group(7)
    
    # 处理毫秒精度
    if len(start_ms_str) == 2:
        start_ms = int(start_ms_str) * 10
    else:
        start_ms = int(start_ms_str)
    
    if len(end_ms_str) == 2:
        end_ms = int(end_ms_str) * 10
    else:
        end_ms = int(end_ms_str)
    
    start_time = start_min * 60 + start_sec + start_ms / 1000
    end_time = end_min * 60 + end_sec + end_ms / 1000
    
    timestamps.append({
        'word': word,
        'start': start_time,
        'end': end_time
    })

print(f"\n解析到 {len(timestamps)} 个时间戳")

# ==================== 导出 LRC 格式 ====================
print("\n[1/2] 导出 LRC 格式...")

lrc_lines = []
lrc_lines.append("[ti:回声在草原上]")
lrc_lines.append("[ar:未知]")
lrc_lines.append("[al:未知]")
lrc_lines.append("[by:Auto Generated]")
lrc_lines.append("")

# 将连续的字符合并成词/句
current_line = ""
current_start = 0
lines_for_lrc = []

for i, ts in enumerate(timestamps):
    # 只有当开始新行时才设置开始时间
    if not current_line:
        current_start = ts['start']
    
    current_line += ts['word']
    
    # 当遇到句号、逗号或累积了一定长度时断开
    if ts['word'] in ['。', '，', '！', '？', '、'] or len(current_line) >= 15:
        lines_for_lrc.append({
            'text': current_line,
            'start': current_start,
            'end': ts['end']
        })
        current_line = ""

# 处理最后一行
if current_line:
    lines_for_lrc.append({
        'text': current_line,
        'start': current_start,
        'end': timestamps[-1]['end']
    })

# 生成 LRC
for line in lines_for_lrc:
    start_time = line['start']
    minutes = int(start_time // 60)
    seconds = start_time % 60
    time_str = f"{minutes:02d}:{seconds:05.2f}"
    lrc_lines.append(f"[{time_str}]{line['text']}")

# 保存 LRC
with open(LRC_OUTPUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lrc_lines))

print(f"      LRC 文件已保存: {LRC_OUTPUT}")

# ==================== 导出 SRT 格式 ====================
print("\n[2/2] 导出 SRT 格式...")

srt_lines = []
subtitle_index = 1

for line in lines_for_lrc:
    # SRT 时间格式: 00:00:00,000
    start_h = int(line['start'] // 3600)
    start_m = int((line['start'] % 3600) // 60)
    start_s = int(line['start'] % 60)
    start_ms = int((line['start'] % 1) * 1000)
    
    end_h = int(line['end'] // 3600)
    end_m = int((line['end'] % 3600) // 60)
    end_s = int(line['end'] % 60)
    end_ms = int((line['end'] % 1) * 1000)
    
    start_str = f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d}"
    end_str = f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}"
    
    srt_lines.append(f"{subtitle_index}")
    srt_lines.append(f"{start_str} --> {end_str}")
    srt_lines.append(line['text'])
    srt_lines.append("")
    
    subtitle_index += 1

# 保存 SRT
with open(SRT_OUTPUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(srt_lines))

print(f"      SRT 文件已保存: {SRT_OUTPUT}")

print("\n" + "=" * 60)
print("✅ 导出完成!")
print("=" * 60)
print(f"\n📄 LRC 文件: {LRC_OUTPUT}")
print(f"📄 SRT 文件: {SRT_OUTPUT}")
