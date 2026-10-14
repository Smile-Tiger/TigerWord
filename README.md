# TigerWord

把每天在英语听力里摘下来的生词，导进自己的词库，按记忆曲线背掉。

完整的方案说明见 [设计方案.md](设计方案.md)，下面只讲怎么把它跑起来。

## 项目结构

后端和前端完全分开：

| 目录 | 内容 | 技术 |
| --- | --- | --- |
| `backend/` | 导入管线、数据库、AI 补全、复习算法、接口 | Python + FastAPI + SQLite |
| `frontend/` | 背单词的网页界面 | React + Vite + TypeScript |
| `outputs/` | 交付物：真实导出文件的解析结果存档 | - |

## 环境准备

在项目根目录执行（虚拟环境放在根目录，前后端共用）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e backend
```

然后配置 AI 补全用的 Key：

```powershell
Copy-Item backend\.env.example backend\.env
# 打开 backend\.env，把 LLM_API_KEY 填成你自己的 DeepSeek Key
```

不填 Key 也能用：导入照样能跑，只是空缺的音标和释义会留着空白。

## 怎么用（网页版）

需要开**两个**终端（开发时前后端分开跑，改代码能立刻看到效果）。

终端一，起后端：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn vocab_agent.api.main:app --reload
```

终端二，起前端：

```powershell
cd frontend
npm install      # 第一次才需要
npm run dev
```

然后打开 http://localhost:5173 就能背单词了。

前端页面分四处：**背单词**（空格翻面，1/2/3 表示认识/模糊/不认识）、
**导入生词**（传文件、看导入报告）、**统计**（词库分布与正确率）、
**设置**（填自己的 API Key、模型、每日新词量）。

### 打包成一个服务

```powershell
cd frontend
npm run build          # 产物在 frontend/dist
```

之后只起后端一个服务就行，后端会直接把 `frontend/dist` 托管在根路径，
访问 http://127.0.0.1:8000 即可。

## 怎么用（命令行版）

装好之后在**任意目录**都能用 `vocab` 命令，或者在 `backend` 目录下用 `python -m`：

```powershell
vocab import .\你的生词本.pdf     # 导入
vocab today                       # 看今天该背什么
vocab stats                       # 看词库统计
```

导入时会依次做这几件事：

1. 按坐标解析 PDF（音标上下两行也能正确归位）
2. 无损清洗：去首尾标点、合并折行产生的空格
3. 补全：缓存 -> 在线词典 -> DeepSeek，只填空缺，补不到就留空
4. 合并入库：按词去重，重复导入不会产生重复词条
5. 归档原始文件，方便以后改规则重跑

## 跑测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

测试覆盖：PDF 解析（条数、串行、页脚污染）、清洗边界、复习阶梯升降级、
入库合并规则、每日队列组装。

样例文件是 `backend/tests/fixtures/make_fixture.py` 生成的版式复刻件。
想用**你自己的真实导出文件**测，把它放进 `backend/tests/fixtures/`，
相关的测试会自动启用（会校验"解析条数 == 页眉声明的词数"）。

## 数据放在哪

全部在 `backend/data/` 下，不进版本库：

```
backend/data/
├── app.db          # SQLite 主库（词条、复习状态、作答流水）
├── imports/        # 你上传过的原始文件，按名字归档
└── cache/          # 词典和 AI 补全结果的缓存
```

想换位置，在 `backend/.env` 里设置 `DATA_DIR` 即可。

## 当前进度

- [x] PDF 解析（坐标分列，已验证）
- [x] 清洗与入库合并规则
- [x] AI 补全（DeepSeek，带缓存与防幻觉约束）
- [x] 复习算法与每日队列
- [x] 导入流程编排（LangGraph 状态图）
- [x] 命令行工具
- [x] 后端接口（FastAPI：导入 / 今日队列 / 作答 / 统计 / 设置）
- [x] 网页界面（React：背单词 / 导入 / 统计 / 设置）
- [ ] 看词选义题型（目前是翻卡自评）
- [ ] 图片导入（阶段二）
- [ ] 做成一键启动脚本（`scripts/dev.ps1`）
