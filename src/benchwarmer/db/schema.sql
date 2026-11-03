PRAGMA page_size = 4096;

CREATE TABLE IF NOT EXISTS meta_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    org TEXT NOT NULL,
    model_name TEXT NOT NULL,
    base_model TEXT,
    params_b REAL,                      -- Parameter count in billions (e.g., 7.0, 32.5, 70.6)
    context_length INTEGER,
    architecture TEXT,
    license TEXT,
    precision TEXT,                     -- e.g., 'BF16', 'FP16', 'GPTQ', 'AWQ'
    is_moe INTEGER DEFAULT 0,           -- 0 or 1
    active_params_b REAL,               -- Active parameters for MoE models (defaults to params_b)
    sha TEXT,
    last_modified TEXT,
    raw_metadata TEXT                   -- JSON string
);

CREATE TABLE IF NOT EXISTS benchmark_scores (
    model_id TEXT NOT NULL,
    suite TEXT NOT NULL,                -- 'hf_v2', 'hf_v1', 'lmsys_arena'
    benchmark TEXT NOT NULL,            -- 'ifeval', 'bbh', 'math_hard', 'gpqa', 'musr', 'mmlu_pro', 'arena_elo'
    metric TEXT NOT NULL,               -- Normalized primary metric name (e.g., 'norm_score')
    score REAL NOT NULL,                -- Uniform 0.0 - 100.0 scale for cross-benchmark math
    raw_score REAL NOT NULL,            -- Original unscaled score (e.g., 1285.4 for Elo, 0.742 for acc_norm)
    PRIMARY KEY (model_id, suite, benchmark, metric),
    FOREIGN KEY (model_id) REFERENCES models(model_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scores_bench_desc ON benchmark_scores(benchmark, score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_model_bench ON benchmark_scores(model_id, benchmark);
CREATE INDEX IF NOT EXISTS idx_models_params ON models(params_b);

CREATE VIRTUAL TABLE IF NOT EXISTS models_fts USING fts5(
    model_id,
    org,
    model_name,
    architecture,
    content='models',
    content_rowid='rowid',
    tokenize='porter unicode61 remove_diacritics 1'
);

CREATE VIEW IF NOT EXISTS v_leaderboard_summary AS
SELECT
    m.model_id,
    m.org,
    m.params_b,
    m.active_params_b,
    m.context_length,
    m.architecture,
    m.precision,
    MAX(CASE WHEN b.benchmark = 'ifeval' THEN b.score END) AS ifeval,
    MAX(CASE WHEN b.benchmark = 'bbh' THEN b.score END) AS bbh,
    MAX(CASE WHEN b.benchmark = 'math_hard' THEN b.score END) AS math_hard,
    MAX(CASE WHEN b.benchmark = 'gpqa' THEN b.score END) AS gpqa,
    MAX(CASE WHEN b.benchmark = 'musr' THEN b.score END) AS musr,
    MAX(CASE WHEN b.benchmark = 'mmlu_pro' THEN b.score END) AS mmlu_pro,
    MAX(CASE WHEN b.benchmark = 'arena_elo' THEN b.raw_score END) AS arena_elo_raw,
    MAX(CASE WHEN b.benchmark = 'arena_elo' THEN b.score END) AS arena_elo_norm,
    AVG(CASE WHEN b.suite = 'hf_v2' THEN b.score END) AS hf_v2_avg
FROM models m
LEFT JOIN benchmark_scores b ON m.model_id = b.model_id
GROUP BY m.model_id;
