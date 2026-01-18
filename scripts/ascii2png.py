#!/usr/bin/env python3
"""
High-Quality ASCII to PNG Converter
优化版: 支持 Retina 高清、macOS 窗口风格、精确的 CJK 字符对齐、智能右对齐
"""

import argparse
import sys
import os
import unicodedata
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("❌ 请先安装 Pillow: pip install Pillow")
    sys.exit(1)

# ============ 配置常量 ============
SCALE_FACTOR = 4  # 渲染倍数 (4x 超采样，然后缩放到 2x 保存)
OUTPUT_SCALE = 2  # 输出图片的缩放倍数 (Retina)

THEMES = {
    "dark": {
        "bg": "#1E1E1E",
        "text": "#CCCCCC",
        "punc": "#569CD6",  # 标点符号/边框
        "keyword": "#C586C0",  # 关键字
        "header_bg": "#252526",
        "nav_points": ["#FF5F56", "#FFBD2E", "#27C93F"],  # 红黄绿灯
    },
    "dracula": {
        "bg": "#282A36",
        "text": "#F8F8F2",
        "punc": "#8BE9FD",
        "keyword": "#FF79C6",
        "header_bg": "#21222C",
        "nav_points": ["#FF5555", "#F1FA8C", "#50FA7B"],
    },
    "light": {
        "bg": "#FFFFFF",
        "text": "#24292E",
        "punc": "#0366D6",
        "keyword": "#D73A49",
        "header_bg": "#F6F8FA",
        "nav_points": ["#FF5F56", "#FFBD2E", "#27C93F"],
    },
}

# 字体回退列表
FONTS_EN = [
    "/System/Library/Fonts/Monaco.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/Library/Fonts/SF-Mono-Regular.otf",
    "C:/Windows/Fonts/consola.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]

FONTS_CN = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]


def load_font(size):
    """加载英文字体和中文字体"""
    font_en = ImageFont.load_default()
    font_cn = ImageFont.load_default()

    for f in FONTS_EN:
        if os.path.exists(f):
            try:
                index = 0
                if f.endswith(".ttc") and "Menlo" in f:
                    index = 0
                font_en = ImageFont.truetype(f, size, index=index)
                break
            except:
                continue

    for f in FONTS_CN:
        if os.path.exists(f):
            try:
                font_cn = ImageFont.truetype(f, size)
                break
            except:
                continue

    return font_en, font_cn


def get_char_width_type(char):
    """判断字符宽度: 1 (半角), 2 (全角)"""
    # 显式处理特定的制表符或全角符号
    if char in ["│", "─", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴"]:
        return 1  # 强制这些框线符号为单宽，防止某些字体下变为全宽
    if unicodedata.east_asian_width(char) in ("F", "W", "A"):
        return 2
    return 1


def hex2rgb(hex_str):
    return tuple(int(hex_str.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))


def render_image(content, output_path, theme_name="dark", font_size=40, padding=40):
    theme = THEMES.get(theme_name, THEMES["dark"])

    # 1. 准备字体
    render_size = font_size * SCALE_FACTOR
    font_en, font_cn = load_font(render_size)

    # 2. 计算网格尺寸
    # 强制 cell_width 为 'M' 宽度的 1.0 倍，保证 grid 紧凑
    # 注意：某些字体下 M 的宽度可能不是准确的 half-width，这里取整
    char_w_metric = font_en.getlength("M")
    cell_width = int(char_w_metric)
    cell_height = int(render_size * 1.6)  # 增加行高

    lines = content.strip().split("\n")

    # 3. 计算每一行的逻辑宽度 (grid units)
    line_grid_widths = []
    max_grid_width = 0

    parsed_lines = []  # 存储 (char, grid_width)

    for line in lines:
        grid_w = 0
        chars_data = []
        for char in line:
            w = get_char_width_type(char)
            chars_data.append((char, w))
            grid_w += w

        parsed_lines.append(chars_data)
        line_grid_widths.append(grid_w)
        max_grid_width = max(max_grid_width, grid_w)

    # 窗口标题栏高度
    header_height = int(cell_height * 1.5)

    # 画布总尺寸
    img_width = max_grid_width * cell_width + padding * 2 * SCALE_FACTOR
    img_height = len(lines) * cell_height + padding * 2 * SCALE_FACTOR + header_height

    image = Image.new("RGB", (img_width, img_height), hex2rgb(theme["bg"]))
    draw = ImageDraw.Draw(image)

    # 4. 绘制窗口装饰
    draw.rectangle(
        [(0, 0), (img_width, header_height)], fill=hex2rgb(theme["header_bg"])
    )

    dot_radius = int(header_height * 0.2)
    dot_spacing = int(header_height * 0.6)
    start_x = padding * SCALE_FACTOR
    center_y = header_height // 2

    for i, color in enumerate(theme["nav_points"]):
        x = start_x + i * dot_spacing
        draw.ellipse(
            [(x, center_y - dot_radius), (x + dot_radius * 2, center_y + dot_radius)],
            fill=hex2rgb(color),
        )

    # 5. 绘制文字 (Smart Grid Alignment)
    start_y = header_height + padding * SCALE_FACTOR

    for row, chars_data in enumerate(parsed_lines):
        col_idx = 0
        y = start_y + row * cell_height  # 基准Y

        # 垂直居中修正
        text_offset_y = (cell_height - render_size) / 2  # 简单居中

        for i, (char, w) in enumerate(chars_data):

            # --- 智能右对齐逻辑 ---
            # 如果是该行的最后一个字符，且是右边框符号 '│' 或 '┐' 或 '┘'
            # 强制将其 x 坐标对齐到 max_grid_width - 1
            is_last_char = i == len(chars_data) - 1
            is_right_border = char in ["│", "┐", "┘", "┤"]

            if is_last_char and is_right_border:
                # 强制 snap 到最右侧一格
                target_col = max_grid_width - 1
                # 如果当前计算的 col_idx 还没到那里，直接跳过去
                if col_idx < target_col:
                    col_idx = target_col
            # --------------------

            # 确定颜色
            color = hex2rgb(theme["text"])
            if char in ["─", "│", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼"]:
                color = hex2rgb(theme["punc"])
            elif char in ["•", "-", ">", "<", "→", "←", "↑", "↓"]:
                color = hex2rgb(theme["punc"])

            # 计算绘制坐标
            x = padding * SCALE_FACTOR + col_idx * cell_width

            # 绘制
            if w == 2:
                # 中文: 绘制在 2 个单元格宽度的中心
                # 实际字符宽度可能不等于 2 * cell_width
                char_pixel_w = font_cn.getlength(char)
                # 计算居中偏移
                center_x_offset = (2 * cell_width - char_pixel_w) / 2
                draw.text((x + center_x_offset, y), char, font=font_cn, fill=color)
                col_idx += 2
            else:
                # 英文: 绘制在 1 个单元格宽度的中心
                char_pixel_w = font_en.getlength(char)
                center_x_offset = (cell_width - char_pixel_w) / 2
                draw.text((x + center_x_offset, y), char, font=font_en, fill=color)
                col_idx += 1

    # 6. 缩放输出
    target_width = img_width // (SCALE_FACTOR // OUTPUT_SCALE)
    target_height = img_height // (SCALE_FACTOR // OUTPUT_SCALE)

    final_image = image.resize(
        (target_width, target_height), resample=Image.Resampling.LANCZOS
    )
    final_image.save(output_path)
    print(f"✅ 生成高清图: {output_path} ({target_width}x{target_height})")


def main():
    parser = argparse.ArgumentParser(description="Generate High-Quality PNG from ASCII")
    parser.add_argument("input", nargs="?", help="Input file")
    parser.add_argument("-o", "--output", required=True, help="Output path")
    parser.add_argument("--theme", default="dark", choices=["dark", "light", "dracula"])

    args = parser.parse_args()

    content = ""
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        if sys.stdin.isatty():
            print("Usage: python ascii2png.py input.txt -o output.png")
            sys.exit(1)
        content = sys.stdin.read()

    if not content:
        print("Empty content")
        sys.exit(1)

    render_image(content, args.output, args.theme)


if __name__ == "__main__":
    main()
