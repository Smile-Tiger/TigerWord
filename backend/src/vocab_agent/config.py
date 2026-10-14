"""全局配置：路径、数据库位置、LLM 参数。

为什么单独抽一个模块：
    所有路径和可调参数集中在这里，其它模块只从这里取。
    以后要改数据目录、换 LLM 供应商、调每日新词量，只动这一个文件。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 目录定位。本文件路径是：
#     <项目根>/backend/src/vocab_agent/config.py
# 所以倒推：
#     parents[0] = vocab_agent 包目录
#     parents[1] = src
#     parents[2] = backend      <- 后端的根，数据目录建在这里
#     parents[3] = 项目根       <- backend 和 frontend 的上一级
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """可调参数。默认值写在类里，真实值可以被 backend/.env 覆盖。"""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- 数据目录 ----------
    # 数据库、导入的原始文件、词典缓存都放在这里，全部不进版本库
    data_dir: Path = BACKEND_DIR / "data"

    # ---------- LLM（AI 补全用，走 OpenAI 兼容的接口）----------
    llm_provider: str = "deepseek"
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 60.0

    # ---------- 补全开关 ----------
    # 关掉之后导入照样能跑，只是空缺的音标和释义会一直空着
    enrich_enabled: bool = True
    # 是否先用在线词典查。词典能查到就不花 LLM 的钱
    enrich_use_dictionary_api: bool = True

    # ---------- 学习节奏 ----------
    # 每日新词配额，界面上也可以改（改了会覆盖这里的默认值）
    daily_new_limit: int = 20

    # ---------- 由 data_dir 派生出来的路径 ----------

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def imports_dir(self) -> Path:
        """用户上传的原始文件按日期归档在这里，用于回溯和对账。"""
        return self.data_dir / "imports"

    @property
    def cache_dir(self) -> Path:
        """词典 / LLM 补全结果的本地缓存，保证同一个词只查一次。"""
        return self.data_dir / "cache"

    @property
    def dictionary_cache_path(self) -> Path:
        return self.cache_dir / "dictionary.json"

    def ensure_dirs(self) -> None:
        """确保运行需要的目录都存在（不存在就建，已存在不报错）。"""
        for path in (self.data_dir, self.imports_dir, self.cache_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """进程内复用同一个配置对象（读 .env 只读一次）。"""
    settings = Settings()
    settings.ensure_dirs()
    return settings
