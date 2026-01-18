# ASCII to PNG Converter

高质量 ASCII 字符画转 PNG 图片工具，专为此区块链课程设计。

## 功能特点

- 🎨 **Retina 高清输出**: 4x 超采样渲染，2x 输出，超清晰
- 🇨🇳 **完美 CJK 支持**: 中英文混排严格网格对齐
- 🖥️ **macOS 风格**: 带红黄绿灯的窗口装饰
- 🎯 **智能右对齐**: 自动吸附右边框字符到正确位置
- 🌙 **多主题**: dark (默认), light, dracula

## 安装

```bash
cd scripts
python3 -m venv .venv
source .venv/bin/activate
pip install Pillow
```

## 使用方法

### 基本用法

```bash
# 从文件转换
python ascii2png.py input.txt -o output.png

# 从 stdin 读取
cat diagram.txt | python ascii2png.py -o output.png
```

### 指定主题

```bash
python ascii2png.py input.txt -o output.png --theme dracula
```

### 可用主题

| 主题    | 背景色  | 文字色  | 边框色  |
| ------- | ------- | ------- | ------- |
| dark    | #1E1E1E | #CCCCCC | #569CD6 |
| light   | #FFFFFF | #24292E | #0366D6 |
| dracula | #282A36 | #F8F8F2 | #8BE9FD |

## 示例

输入 (`test.txt`):
```
┌────────────────────────┐
│    Hello 你好世界      │
└────────────────────────┘
```

输出: 高清 PNG 图片，带 macOS 风格窗口装饰。

## 技术细节

- 英文字体: Monaco / Menlo (macOS), Consolas (Windows)
- 中文字体: PingFang (macOS), 微软雅黑 (Windows)
- 网格系统: 中文占 2 个单元格宽度，英文占 1 个
- 智能右对齐: 每行末尾的 `│` 字符自动吸附到最右侧列
