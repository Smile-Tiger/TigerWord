r"""FastAPI 应用装配。

启动方式（在 backend 目录下）：
    ..\.venv\Scripts\python.exe -m uvicorn vocab_agent.api.main:app --reload

开发时前端单独跑在 5173 端口（Vite），所以这里开了跨域；
打包后前端产物放在 frontend/dist，由本文件直接托管，只跑一个服务。
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import PROJECT_DIR
from .routes import imports, settings as settings_route, stats, study

# 开发时前端的地址，允许它跨域访问接口
DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app() -> FastAPI:
    """装配应用。拆成函数是为了测试时能造一个干净的实例。"""
    app = FastAPI(
        title="TigerWord",
        version=__version__,
        description="把摘录的生词导入词库，并按记忆曲线安排背诵",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(settings_route.router)
    app.include_router(imports.router)
    app.include_router(study.router)
    app.include_router(stats.router)

    @app.get("/api/health")
    def health() -> dict:
        """探活接口，前端启动时可以先用它确认后端在不在。"""
        return {"status": "ok", "version": __version__}

    # 前端构建产物存在时直接托管。放在最后注册，
    # 这样 /api/... 的请求会先被上面的路由接住，不会被打到静态文件里。
    dist_dir = PROJECT_DIR / "frontend" / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")

    return app


app = create_app()
