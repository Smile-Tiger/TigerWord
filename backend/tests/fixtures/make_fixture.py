"""生成一份"版式逼真"的样例 PDF，供解析器测试使用。

【为什么需要它】
    原始的导出文件放在微信临时目录里，会被系统自动清理（我们的那份已经没了）。
    所以这里用代码复刻同样的版式，把解析器最容易出错的几种情况都造出来，
    让测试随时能跑。

【复刻的关键特征】——这些都是从真实文件里量出来的
    1. 四列的 x 位置：序号 56、单词 76、音标 207、解释 338
    2. 英式音标画在序号行的**上方**（约 -5pt），美式音标在**下方**（约 +5pt）
    3. 释义太长会折行，折行的第一行常常跟音标同一水平线，第二行在序号行下方
    4. 有的词条完全没有音标和释义（真实文件里是 militaries）
    5. 页脚 "1 of 1" 在页面最底部

运行方式（在 backend 目录下）：
    .venv\\Scripts\\python.exe tests\\fixtures\\make_fixture.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# 字体分两种，为什么：
#   Windows 的中文字体（雅黑/宋体等）**不含 IPA 音标符号**，
#   直接画会把 ˌ ɒ ɪ ʃ ː 这些字符丢掉；
#   而 Arial 这类西文字体又不含汉字。
#   所以按字符类型切换字体，见下面的 draw_mixed()。
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
CJK_FONT = "STSong-Light"

# 西文字体用于音标。找不到就退回中文字体（此时音标会丢字符，但布局测试照常）。
LATIN_FONT = CJK_FONT
for _candidate in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
    if Path(_candidate).exists():
        pdfmetrics.registerFont(TTFont("LatinIPA", _candidate))
        LATIN_FONT = "LatinIPA"
        break

FONT_SIZE = 9

PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.27 x 841.89，和真实文件基本一致

# 四列的文字起始 x 坐标（量自真实文件）
X_SEQ = 56
X_WORD = 76
X_PHONETIC = 207
X_DEFINITION = 338

# 每一行数据在页面上的顶部位置（top，从上往下算）
ROW_TOPS = [92, 109, 126, 143, 160, 177]

# 每个词条的绘制指令：(相对序号行的纵向偏移, 列, 文字)
# 列取值：seq / word / phonetic / definition
RECORDS: list[list[tuple[float, str, str]]] = [
    [
        # 英美音标都有，释义单行
        (-5.2, "phonetic", "英:/ˌkɒnsl'teɪʃn/"),
        (0.0, "seq", "1"),
        (0.0, "word", "consultation"),
        (0.0, "definition", "n. 磋商(会议),咨询,专家会诊"),
        (5.2, "phonetic", "美:/ˌkɑːnsl'teɪʃn/"),
    ],
    [
        # 释义折成两行，第一行压在序号行上方，第二行落到下方
        (-5.2, "phonetic", "英:/'kraɪsɪs/"),
        (-5.3, "definition", "n. 危机；决定性时刻；危险期 adj. 危机的；用于处理危"),
        (0.0, "seq", "2"),
        (0.0, "word", "crisis"),
        (5.2, "phonetic", "美:/'kraɪsɪs/"),
        (5.5, "definition", "机的"),
    ],
    [
        # 音标和释义都没有 —— 最容易把上下两行串错的一条
        (0.0, "seq", "3"),
        (0.0, "word", "militaries"),
    ],
    [
        # 只有一个音标（没有英美前缀），释义折行且第二行带数字
        (-5.5, "definition", "adj. 租用的 n. [计]专线；[计]一线路（指一电话线路每"),
        (0.0, "seq", "4"),
        (0.0, "word", "leased"),
        (0.0, "phonetic", "/li:st/"),
        (6.5, "definition", "天 24 小时地连通两地）"),
    ],
    [
        # 短语：没有音标，只有简短释义
        (0.0, "seq", "5"),
        (0.0, "word", "dozens of"),
        (0.0, "definition", "几十"),
    ],
    [
        (0.0, "seq", "6"),
        (0.0, "word", "facilities"),
        (0.0, "phonetic", "/fə'sɪləti/"),
        (0.0, "definition", "n. 工具, 设施, 设备"),
    ],
]

X_BY_COLUMN = {
    "seq": X_SEQ,
    "word": X_WORD,
    "phonetic": X_PHONETIC,
    "definition": X_DEFINITION,
}


def build(path: Path) -> None:
    """按上面的指令画出一页 PDF。"""
    pdf = canvas.Canvas(str(path), pagesize=A4)

    def draw(top: float, column: str, text: str) -> None:
        # PDF 坐标原点在左下角，所以要把"从上往下算的 top"换算成 y
        _draw_mixed(pdf, X_BY_COLUMN[column], PAGE_HEIGHT - top, text)

    # 页眉：标题 + 列表头。词数写成 6，和下面实际条数一致，
    # 这样解析器的"自校验"逻辑能验证通过。
    draw(44, "word", "#所有生词本 (共6词)")
    draw(44, "definition", "日期：")
    draw(71, "word", "单词")
    draw(71, "phonetic", "音标")
    draw(71, "definition", "解释")
    draw(73, "seq", "No.")

    # 数据行
    for row_top, instructions in zip(ROW_TOPS, RECORDS):
        for offset, column, text in instructions:
            draw(row_top + offset, column, text)

    # 页脚。故意画得和真实文件一样，用来验证它不会被粘到最后一个词条上。
    draw(817, "definition", "1 of 1")

    pdf.showPage()
    pdf.save()


def _needs_latin(ch: str) -> bool:
    """判断这个字符要不要用西文字体画。

    IPA 音标落在 Unicode 的 0250-02FF 区间（如 ɒ ɪ ʃ ː ˌ ），
    中文字体没有这些字形，必须换字体。
    """
    return 0x0250 <= ord(ch) <= 0x02FF


def _draw_mixed(pdf: canvas.Canvas, x: float, y: float, text: str) -> None:
    """把一段文字按字符类型切成若干段，分别用中文字体/西文字体画出来。

    reportlab 的 drawString 一次只能用一个字体，
    所以这里手动累加每段的宽度，把下一段接着画在正确的位置上。
    """
    runs: list[tuple[str, str]] = []  # (字体, 文字片段)
    for ch in text:
        font = LATIN_FONT if _needs_latin(ch) else CJK_FONT
        if runs and runs[-1][0] == font:
            runs[-1] = (font, runs[-1][1] + ch)
        else:
            runs.append((font, ch))

    cursor = x
    for font, chunk in runs:
        pdf.setFont(font, FONT_SIZE)
        pdf.drawString(cursor, y, chunk)
        cursor += pdfmetrics.stringWidth(chunk, font, FONT_SIZE)


if __name__ == "__main__":
    target = Path(__file__).parent / "sample_wordbook.pdf"
    build(target)
    print(f"已生成 {target}")
