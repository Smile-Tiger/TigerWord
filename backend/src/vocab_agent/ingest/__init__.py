"""导入层：把用户给的文件还原成词条，清洗，再补齐缺的字段。

处理顺序：
    base.py        解析器的统一返回结构
    pdf_parser.py  解析 PDF（坐标分列）
    text_parser.py 解析纯文本 / 粘贴的单词列表
    normalize.py   无损清洗：去首尾标点、合空格、拆音标
    enrich.py      补全：缓存 -> 词典 API -> LLM
"""
