# Schema Contracts（核心数据契约）

## 1. 设计目标

本项目采用 `app/core/schemas` 作为唯一 schema 真源（single source of truth），并由各 agent 的 `schemas` 目录做轻量引用导出，避免出现重复定义、命名漂移和字段不一致。

- 核心定义目录：`app/core/schemas/`
- agent 引用目录：
  - `app/agents/monitor_agent/schemas/`
  - `app/agents/summarizer_agent/schemas/`
  - `app/agents/delivery_agent/schemas/`
  - `app/agents/feedback_agent/schemas/`

## 2. 分层约定

每个关键对象按三类模型分离：

1. **DB persistence model**：`*DB`
   - 表示持久化层记录结构。
2. **service layer input/output model**：`*Create` / `*Upsert` / `*View`
   - 表示服务层输入输出，不直接暴露 DB 内部字段。
3. **external payload model**：`External*Payload`
   - 表示外部集成输入或对外输出载荷，不复用内部 DB 模型。

## 3. 公共基类与 mixin

### 3.1 `SchemaModel`
- 统一 Pydantic 配置（`extra=forbid`、去空格等），保证校验一致性。

### 3.2 `IdentifiedModel`
- 提供统一 `id` 字段（UUID）。

### 3.3 `TimestampedModel`
- 提供统一 `created_at` / `updated_at` 字段。

### 3.4 `AuditFieldsModel`
- 基于 `TimestampedModel` 增加 `created_by` / `updated_by`。

## 4. 统一枚举与受控词表

- `MonitorRunStatus`：监控执行状态。
- `DeliveryStatus`：投递状态。
- `FeedbackLabel`：用户反馈标签。
- `RelevanceLevel`：相关性等级。
- `RecommendedAction`：推荐动作。

> 以上枚举在 `app/core/schemas/enums.py` 统一维护。

## 5. 核心 schema 说明

## 5.1 QueryTask
- **职责**：定义监控任务本身（查询表达式、调度、时区、回看窗口）。
- **真源字段**：`name`、`query_expression`、`schedule`、`timezone`、`lookback_hours`、`is_enabled`。
- **可空字段**：无（除审计字段的 `created_by` / `updated_by`）。
- **派生字段**：无。

## 5.2 MonitorRun
- **职责**：记录每一次任务执行实例及结果计数。
- **真源字段**：`query_task_id`、`triggered_at`、`window_start`、`window_end`、`status`。
- **可空字段**：`error_message`。
- **派生字段**：`new_result_count`（通常由去重流程计算后写入）。

## 5.3 Paper
- **职责**：系统内部的文献主数据实体。
- **真源字段**：`title`（必填），其余标识字段 `pmid` / `doi` 允许为空以兼容来源差异。
- **可空字段**：`pmid`、`doi`、`abstract`、`journal`、`publication_date`、`pubmed_url`、`raw_payload`。
- **派生字段**：无（但可由集成层在入库前归一化）。

## 5.4 PaperQueryHit
- **职责**：表示文献与查询任务、执行批次之间的命中关系。
- **真源字段**：`paper_id`、`query_task_id`、`monitor_run_id`、`matched_at`。
- **可空字段**：`rank_in_run`。
- **派生字段**：`rank_in_run` 可由检索排序产生。

## 5.5 LlmSummary
- **职责**：保存结构化摘要结果及评分。
- **真源字段**：`paper_id`、`model_name`、`prompt_version`、`generated_at`。
- **可空字段**：摘要文本与解释类字段可为空（如 `one_line_takeaway`、`why_it_matters`）。
- **派生字段**：`relevance_score`、`novelty_score`、`actionability_score`、`recommended_action` 通常由 summarizer 输出计算。

## 5.6 DeliveryRecord
- **职责**：记录向外部目标（群、邮箱、Webhook）投递结果。
- **真源字段**：`paper_id`、`target_type`、`target_ref`、`delivery_status`。
- **可空字段**：`card_id`、`delivered_at`、`error_message`。
- **派生字段**：`delivery_status` 由投递流程状态机推进。

## 5.7 UserFeedback
- **职责**：归一化记录用户反馈信号。
- **真源字段**：`paper_id`、`source`、`label`、`created_at`。
- **可空字段**：`note`、`actor`。
- **派生字段**：无。

## 5.8 PreferenceProfile
- **职责**：维护偏好配置（硬规则/软偏好/排除项/期刊偏好）。
- **真源字段**：`profile_name`、`hard_rules`、`soft_preferences`、`excluded_patterns`、`preferred_journals`、`updated_at`。
- **可空字段**：无（列表字段可为空列表）。
- **派生字段**：无。

## 6. 上下游依赖关系

1. `monitor_agent` 依赖：`QueryTask*`、`MonitorRun*`、`Paper*`、`PaperQueryHit*`。
2. `summarizer_agent` 依赖：`PaperView`、`LlmSummary*`、`ExternalSummaryPayload`。
3. `delivery_agent` 依赖：`ExternalSummaryPayload`、`Delivery*`。
4. `feedback_agent` 依赖：`UserFeedback*`、`PreferenceProfile*`。

所有 agent 仅通过 `app/core/schemas` 引用，不在 agent 内重复定义结构。

## 7. 命名与兼容性约束

- 全字段统一 `snake_case`。
- 外部 API 不直接复用 `*DB` 模型。
- 新增字段时，必须先更新 `app/core/schemas`，再由 agent 引用。
- 禁止在 agent 目录新增同名“影子 schema”。
