"""TigerWord 后端：把用户摘录的生词导入词库，并按记忆曲线安排背诵。

包结构（每一层职责单一，方便单独测试）：

    config.py    全局配置与路径（数据目录、数据库位置、LLM 参数）
    db/          数据层：建表、连接、增删改查
    ingest/      导入层：解析文件 -> 清洗 -> 补全
    srs/         学习算法层：复习间隔阶梯、每日队列组装（纯函数，不用 LLM）
    llm/         LLM 客户端：DeepSeek 等 OpenAI 兼容接口
    agent/       导入流程编排：LangGraph 状态图
    api/         接口层：FastAPI，前端通过它读写
    cli.py       命令行入口，方便不开前端时先用起来
"""

__version__ = "0.1.0"
