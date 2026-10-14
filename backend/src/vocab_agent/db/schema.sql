-- TigerWord 数据库结构
--
-- 三条设计原则，看代码前先看这三条：
--
--   1. entries 与 raw_entries 分开存
--      entries     = 归一后要背的词
--      raw_entries = 导入时文件里的原貌（含序号、原始音标、原始释义）
--      好处：清洗规则以后改了可以重跑，用户的原始数据不会丢。
--
--   2. 去重主键是 headword，不是导出的序号
--      每次导出都是"当前所有生词"的全量快照，序号会整体重排，
--      只有词条文本本身才是稳定的。
--
--   3. 复习状态和作答流水分开存
--      srs_state   = 每个词当前的状态（该什么时候复习）
--      review_logs = 每次作答的流水
--      好处：以后想换算法、做记忆曲线分析，历史数据都还在。

-- 词条主表：库里要背的词
CREATE TABLE IF NOT EXISTS entries (
    id             INTEGER PRIMARY KEY,
    headword       TEXT NOT NULL UNIQUE,  -- 去重主键：小写 + 去首尾标点 + 压缩空格
    display        TEXT NOT NULL,         -- 展示用：保留原始大小写，如 Iran、March
    kind           TEXT NOT NULL,         -- word（单词）| phrase（短语）
    phonetic_uk    TEXT,                  -- 英式音标，形如 /ˈæpl/；没有就留空
    phonetic_us    TEXT,                  -- 美式音标
    definition     TEXT,                  -- 中文释义，保留词性前缀，如 "n. 苹果"
    source         TEXT NOT NULL DEFAULT 'parse',  -- parse（解析得到）| ai（AI 补的）| user
    confidence     TEXT,                  -- high | medium | low，low 的在导入页高亮
    first_batch_id INTEGER REFERENCES import_batches(id),  -- 第一次由哪批导入进来
    last_seen_at   TEXT NOT NULL,         -- 最近一次在导出文件里出现的时间
    created_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entries_kind ON entries(kind);

-- 复习状态：每个词一个状态机，背和复习的核心
CREATE TABLE IF NOT EXISTS srs_state (
    entry_id       INTEGER PRIMARY KEY REFERENCES entries(id) ON DELETE CASCADE,
    stage          TEXT NOT NULL,         -- new | learning | review | graduated
    step           INTEGER NOT NULL DEFAULT 0,  -- 当前处在复习阶梯的第几级
    due_at         TEXT,                  -- 下次到期的日期，格式 YYYY-MM-DD
    correct_streak INTEGER NOT NULL DEFAULT 0,  -- 连续答对次数
    lapses         INTEGER NOT NULL DEFAULT 0,  -- 累计答错次数
    total_reviews  INTEGER NOT NULL DEFAULT 0,  -- 累计复习次数
    last_review_at TEXT
);

-- 取"今天该复习哪些"时要按 stage + due_at 过滤，所以建联合索引
CREATE INDEX IF NOT EXISTS idx_srs_due ON srs_state(stage, due_at);

-- 学习会话：一次打开网页背书算一场
CREATE TABLE IF NOT EXISTS study_sessions (
    id             INTEGER PRIMARY KEY,
    started_at     TEXT NOT NULL,
    ended_at       TEXT,
    planned_new    INTEGER NOT NULL DEFAULT 0,  -- 本场计划背几个新词
    planned_review INTEGER NOT NULL DEFAULT 0,  -- 本场计划复习几个
    done_new       INTEGER NOT NULL DEFAULT 0,
    done_review    INTEGER NOT NULL DEFAULT 0
);

-- 作答流水：每答一个词记一条，既是审计也是统计看板的数据源
CREATE TABLE IF NOT EXISTS review_logs (
    id          INTEGER PRIMARY KEY,
    entry_id    INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    session_id  INTEGER REFERENCES study_sessions(id),
    rating      TEXT NOT NULL,            -- known（认识）| fuzzy（模糊）| unknown（不认识）
    mode        TEXT NOT NULL,            -- choice（看词选义）| self_report（翻卡自评）
    prev_stage  TEXT,                     -- 作答前的状态，便于回溯状态是怎么变的
    next_stage  TEXT,                     -- 作答后的状态
    prev_step   INTEGER,
    next_step   INTEGER,
    reviewed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_entry ON review_logs(entry_id, reviewed_at);

-- 导入批次：每导入一个文件记一条，出问题时能查到"这批是哪来的"
CREATE TABLE IF NOT EXISTS import_batches (
    id            INTEGER PRIMARY KEY,
    source        TEXT NOT NULL,          -- 原始文件的归档路径
    file_hash     TEXT NOT NULL,          -- 文件指纹，用来识别"同一个文件重复导入"
    input_kind    TEXT NOT NULL,          -- pdf | sheet | image | text
    imported_at   TEXT NOT NULL,
    total         INTEGER NOT NULL DEFAULT 0,
    added         INTEGER NOT NULL DEFAULT 0,
    updated       INTEGER NOT NULL DEFAULT 0,
    unchanged     INTEGER NOT NULL DEFAULT 0,
    needs_review  INTEGER NOT NULL DEFAULT 0  -- 低置信、等人工复核的条数
);

-- 原始导出记录：文件里长什么样就存什么样，用于对账与重建
CREATE TABLE IF NOT EXISTS raw_entries (
    id             INTEGER PRIMARY KEY,
    batch_id       INTEGER NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
    seq_no         INTEGER NOT NULL,      -- 文件里的序号，仅作参考
    raw_word       TEXT NOT NULL,         -- 原样单词，未清洗
    raw_phonetic   TEXT,                  -- 原样音标（可能含"英:/.../ 美:/.../"）
    raw_definition TEXT,                  -- 原样释义
    entry_id       INTEGER REFERENCES entries(id)  -- 对应到哪个词条（可能为空）
);

CREATE INDEX IF NOT EXISTS idx_raw_batch ON raw_entries(batch_id);

-- 设置项：键值对，存放用户可调参数（每日新词量、复习阶梯等）
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
