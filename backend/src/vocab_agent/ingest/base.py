"""解析器的统一返回结构。

为什么要抽这个：
    以后再支持 Excel、图片、Word，只需要再写一个"能返回 ParsedDocument 的函数"，
    导入流程本身一行都不用改。这是 6.3 输入适配器矩阵在代码上的落点。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import RawRecord


@dataclass
class ParsedDocument:
    """一次解析的全部产出。"""

    records: list[RawRecord]
    # 页眉里声明的词数（如"共174词"）。用来做校验：
    # 解析出来的条数应该和它相等，否则说明版式变了、解析漏了。
    declared_count: int | None = None
    # 输入类型：pdf | sheet | image | text
    input_kind: str = "unknown"
    # 解析过程中的异常情况（比如某页没解析出内容），供导入报告展示
    warnings: list[str] = field(default_factory=list)
