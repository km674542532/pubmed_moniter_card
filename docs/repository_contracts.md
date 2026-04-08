# Repository Contracts

## 1) 持久化访问边界

允许直接调用 repository 的模块：
- workflow/service 编排层
- integration 的业务服务层（通过 service 间接使用）
- agent handler 的应用服务层（通过 use-case/service 间接使用）

禁止直接访问数据库的模块：
- workflow
- integration adapter
- agent handler
- LLM 提示词与解析逻辑模块

规则：上述模块 **不得拼 SQL**、不得直接持有 sqlite3/ORM session。

## 2) Create 与 Upsert 边界

- `create`：用于“明确新增一条记录”，如果自然唯一键冲突应报错。
- `upsert`：用于“按自然键幂等写入”。

当前约定：
- `PaperRepository.upsert_paper` 以 `pmid` 作为自然唯一键。若 `pmid` 为空，直接抛出异常。
- `PreferenceRepository.upsert_profile` 以 `profile_name` 作为自然唯一键。

## 3) 数据真源策略

- `paper.pmid` 是主自然唯一键。
- `paper_query_hit` 不做 `(paper_id, query_task_id)` 唯一限制，允许同一 paper 在不同 run 多次命中。
- `llm_summary` 允许多版本并行保留；读取“最新版本”使用 `summary_version DESC, generated_at DESC`。
- `delivery_record` 必须保留失败记录，失败后只更新状态，不可删除旧失败数据。

## 4) 适配层要求

- repository 仅依赖 `DatabaseAdapter` 协议（`session()` 上下文）。
- 当前默认实现 `SQLiteAdapter`，后续替换 PostgreSQL 时仅需新增 adapter 并保持 repository 接口不变。

## 5) 非职责声明

repository 内禁止包含：
- LLM 生成与提示词编排逻辑
- 飞书/邮件 payload 组装逻辑
- PubMed 原始数据清洗逻辑

repository 只负责：
- 持久化写入
- 查询读取
- 基础约束校验（例如 upsert 关键字段缺失）
