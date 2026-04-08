# PubMed → LLM → 飞书卡片 文献监控系统架构指导文件

## 1. 项目目标

构建一个面向科研场景的文献监控系统：

- 定时检索 PubMed 指定检索式
- 自动识别新增文献
- 使用 LLM 生成结构化中文总结
- 将每篇文献推送为一张可交互消息卡
- 支持用户对文献进行“相关 / 不相关 / 待看 / 精读”等标记
- 将用户反馈沉淀为偏好信号，持续优化后续总结与排序

该系统的核心不是“论文推送”，而是“可学习的文献筛选与理解工作台”。

---

## 2. 设计原则

### 2.1 先稳定，再智能

第一阶段优先保证：

- 检索稳定
- 去重稳定
- 推送稳定
- 状态可追踪
- 失败可恢复

LLM 总结、个性化排序、反馈学习都建立在稳定的数据流之上。

### 2.2 一篇文献一个对象

系统内所有流程统一以 `Paper` 作为核心对象，不允许下游直接依赖“原始 API 响应”。

### 2.3 事件驱动 + 状态落盘

每个关键步骤都必须：

- 输入可追踪
- 输出可落盘
- 状态可恢复
- 错误可审计

### 2.4 检索与理解解耦

- PubMed 模块只负责“找文献、取元数据”
- LLM 模块只负责“总结、打分、标签化”
- 推送模块只负责“投递卡片”
- 反馈模块只负责“记录人工判断”

### 2.5 用户反馈优先于模型猜测

系统最终应以用户显式反馈作为偏好学习的最高优先级来源。

---

## 3. 总体架构

```text
Scheduler
  ↓
Query Runner
  ↓
PubMed Retriever
  ↓
Dedup / Incremental Filter
  ↓
Paper Repository
  ↓
LLM Summarizer & Relevance Scorer
  ↓
Card Builder
  ↓
Feishu Push Gateway
  ↓
User Feedback Receiver
  ↓
Preference Store
  ↓
Prompt / Ranking Adapter
```

系统分为 8 个核心层：

1. 调度层
2. 检索层
3. 数据标准化层
4. 持久化层
5. LLM 理解层
6. 推送展示层
7. 用户反馈层
8. 偏好学习层

---

## 4. 模块划分

## 4.1 Scheduler（调度层）

职责：

- 按固定周期触发检索任务
- 支持多个检索任务并行管理
- 控制单任务并发与重试
- 记录任务执行历史

建议能力：

- 支持 cron 表达式
- 支持立即试跑
- 支持暂停 / 恢复 / 失效任务
- 支持按 query 维度独立调度

产出：

- `MonitorRun` 运行记录
- 本次运行的时间窗口
- 触发的 query_task_id

---

## 4.2 Query Runner（检索任务执行层）

职责：

- 加载用户配置的 PubMed 检索式
- 计算本次增量时间窗口
- 调用 PubMed 检索接口获取 PMID 列表
- 将原始结果交给标准化层

建议支持：

- 一个用户可配置多个监控主题
- 每个主题拥有独立的：
  - query_name
  - query_expression
  - schedule
  - lookback_window
  - priority_policy

关键点：

- 采用“固定时间窗 + overlap buffer”策略，而不是单纯依赖 reldate
- 每次查询都记录原始参数与返回数量

---

## 4.3 PubMed Retriever（PubMed 获取层）

职责：

- 调用 PubMed API 获取 PMID 列表
- 拉取标题、摘要、作者、期刊、发表日期、PMID、链接等元数据
- 保留原始 API 响应以便审计

建议拆分为：

- `PubMedSearchClient`：负责搜索 PMID
- `PubMedFetchClient`：负责抓取详细元数据
- `PubMedMapper`：负责标准化为内部模型

不要在这个层做：

- LLM 总结
- 业务排序
- 用户偏好推断

---

## 4.4 Incremental Filter / Dedup（增量与去重层）

职责：

- 判断论文是否已存在
- 判断是否是本轮新增
- 对重复抓取结果进行过滤
- 支持 query 级和 paper 级双层去重

建议去重规则：

### paper 全局去重

以 PMID 作为主键；若无 PMID，则退化到 DOI / 标题哈希。

### query 命中去重

同一篇 paper 可以命中多个 query，应保留：

- paper 实体唯一
- paper_query_hit 多条关联记录

这样后续可以知道：

- 这篇论文被哪些检索式命中
- 它是通过哪个主题进入系统的

---

## 4.5 Paper Repository（持久化层）

职责：

- 保存 paper 标准对象
- 保存 query 配置
- 保存 run 历史
- 保存消息推送状态
- 保存用户反馈
- 保存 LLM 结果版本

建议数据库：

- MVP：SQLite
- 后续升级：PostgreSQL

核心表建议：

### 1. query_task
- id
- name
- query_expression
- schedule
- timezone
- lookback_hours
- is_enabled
- created_at
- updated_at

### 2. monitor_run
- id
- query_task_id
- triggered_at
- window_start
- window_end
- status
- raw_result_count
- new_result_count
- error_message

### 3. paper
- id
- pmid
- doi
- title
- abstract
- journal
- publication_date
- authors_json
- pubmed_url
- raw_payload_json
- created_at
- updated_at

### 4. paper_query_hit
- id
- paper_id
- query_task_id
- monitor_run_id
- matched_at
- rank_in_run

### 5. llm_summary
- id
- paper_id
- summary_version
- prompt_version
- model_name
- language
- structured_output_json
- relevance_score
- novelty_score
- actionability_score
- generated_at

### 6. delivery_record
- id
- paper_id
- target_type
- target_ref
- card_id
- delivery_status
- delivered_at
- error_message

### 7. user_feedback
- id
- paper_id
- source
- label
- note
- actor
- created_at

### 8. user_preference_profile
- id
- profile_name
- hard_rules_json
- soft_preferences_json
- updated_at

---

## 4.6 LLM Summarizer & Relevance Scorer（理解层）

职责：

- 对 paper 生成结构化中文总结
- 输出与用户研究方向的相关性判断
- 生成后续卡片展示所需字段
- 为排序提供打分

输出不应是自由文本，而应是结构化对象。

建议输出 schema：

```json
{
  "one_line_takeaway": "",
  "plain_chinese_summary": [
    "",
    "",
    ""
  ],
  "study_type": "",
  "core_methods": [""],
  "main_findings": [""],
  "why_it_matters": [""],
  "relevance_level": "high",
  "relevance_score": 0,
  "novelty_score": 0,
  "actionability_score": 0,
  "reason_for_relevance": [""],
  "tags": [""],
  "recommended_action": "read_now"
}
```

建议把 LLM 的任务拆成两段：

### Stage A：通用文献理解
输出论文本身的研究内容，不掺杂用户偏好。

### Stage B：用户偏好映射
结合用户偏好画像，输出：

- 相关性
- 排序理由
- 推荐动作

这样更利于后续重算与模型替换。

---

## 4.7 Card Builder（卡片构建层）

职责：

- 将 paper + llm_summary 组装为前端展示卡片
- 保证消息卡结构稳定
- 不在这里做模型推理

一张卡建议包含：

- 标题
- 期刊 + 日期
- PMID / 链接
- 一句话结论
- 中文摘要 3 条
- 相关性等级
- 推荐动作
- 操作按钮：相关 / 不相关 / 待看 / 精读

建议为卡片保留内部 metadata：

- paper_id
- llm_summary_id
- query_task_id
- current_prompt_version
- dispatch_batch_id

---

## 4.8 Feishu Push Gateway（推送层）

职责：

- 将卡片推送到飞书目标位置
- 管理 webhook 或 app-bot 发送方式
- 记录推送成功/失败状态
- 支持重试

建议抽象接口：

- `send_card(card_payload)`
- `update_card(card_id, card_payload)`
- `send_digest(cards)`

后续如果要接：

- 邮件
- Slack
- 企业微信
- Notion
- Apple Notes / Shortcuts

都通过同一套 Delivery 接口适配。

---

## 4.9 User Feedback Receiver（反馈层）

职责：

- 接收用户对卡片的交互反馈
- 标记 paper 的人工状态
- 可选追加用户备注
- 触发偏好更新

支持的反馈标签建议：

- relevant
- irrelevant
- pending
- deep_read
- methods_reference
- background_only

反馈必须保留原始来源：

- 来源平台
- 操作时间
- 操作用户
- 对应卡片版本

---

## 4.10 Preference Store / Ranking Adapter（偏好学习层）

职责：

- 聚合用户反馈
- 更新用户偏好画像
- 调整下轮总结语气、相关性理由和排序策略

建议分成两类偏好：

### 硬偏好（Hard Rules）
例如：

- 优先 ASD / neurodevelopment
- 优先 WGS / long-read / SV / noncoding
- 优先可转化 biomarker 研究
- 降低纯病例报告权重

### 软偏好（Soft Preferences）
例如：

- 更偏好有 cohort 的研究
- 更偏好方法学创新
- 更偏好能启发自身项目设计的文章

硬偏好用于过滤和加权，软偏好用于 prompt 调整和解释生成。

---

## 5. 核心数据模型

## 5.1 Paper

```text
Paper
├─ paper_id
├─ pmid
├─ doi
├─ title
├─ abstract
├─ journal
├─ publication_date
├─ authors
├─ keywords
├─ pubmed_url
├─ raw_payload
└─ created_at
```

## 5.2 LlmSummary

```text
LlmSummary
├─ llm_summary_id
├─ paper_id
├─ model_name
├─ prompt_version
├─ one_line_takeaway
├─ plain_chinese_summary
├─ main_findings
├─ relevance_level
├─ relevance_score
├─ novelty_score
├─ actionability_score
├─ reason_for_relevance
├─ tags
└─ generated_at
```

## 5.3 Feedback

```text
Feedback
├─ feedback_id
├─ paper_id
├─ label
├─ note
├─ source
├─ actor
└─ created_at
```

## 5.4 PreferenceProfile

```text
PreferenceProfile
├─ profile_id
├─ user_id
├─ hard_rules
├─ soft_preferences
├─ excluded_patterns
├─ preferred_journals
└─ updated_at
```

---

## 6. 关键流程

## 6.1 主流程：每日监控

```text
Scheduler trigger
  → load query_task
  → compute search window
  → PubMed search
  → fetch metadata
  → normalize to Paper
  → dedup
  → persist new paper / hits
  → call LLM summarizer
  → build card
  → send to Feishu
  → write delivery record
```

## 6.2 用户反馈流程

```text
User clicks card action
  → feedback received
  → persist feedback
  → update paper review state
  → update preference profile
  → mark candidate features for future ranking
```

## 6.3 重新总结流程

```text
Preference updated
  → select affected papers
  → rerun Stage B preference mapping
  → update ranking / explanation
```

---

## 7. 项目目录建议

```text
literature_monitor/
├─ app/
│  ├─ core/
│  │  ├─ config/
│  │  ├─ logging/
│  │  ├─ events/
│  │  └─ scheduler/
│  ├─ agents/
│  │  ├─ monitor_agent/
│  │  │  ├─ handler/
│  │  │  ├─ schemas/
│  │  │  └─ services/
│  │  ├─ summarizer_agent/
│  │  │  ├─ handler/
│  │  │  ├─ schemas/
│  │  │  └─ services/
│  │  ├─ delivery_agent/
│  │  │  ├─ handler/
│  │  │  ├─ schemas/
│  │  │  └─ services/
│  │  └─ feedback_agent/
│  │     ├─ handler/
│  │     ├─ schemas/
│  │     └─ services/
│  ├─ integrations/
│  │  ├─ pubmed/
│  │  ├─ llm/
│  │  ├─ feishu/
│  │  └─ apple_shortcuts/
│  ├─ repositories/
│  ├─ db/
│  └─ utils/
├─ scripts/
├─ docs/
└─ tests/
```

说明：

- `agents` 放业务流程
- `integrations` 放外部系统接入
- `repositories` 统一数据库访问
- `core` 放配置、调度、日志、事件协议
- `utils` 仅放通用无业务语义工具

---

## 8. 日志与审计设计

每一步都要有结构化日志，至少包含：

- event_id
- run_id
- query_task_id
- step
- status
- payload_ref
- error
- created_at

建议关键事件：

- query_triggered
- pubmed_search_completed
- pubmed_fetch_completed
- papers_deduplicated
- llm_summary_started
- llm_summary_completed
- card_built
- delivery_succeeded
- delivery_failed
- feedback_received
- preference_updated

要求：

- LLM 调用失败必须落盘
- 推送失败必须落盘
- 原始 PubMed 返回摘要缺失也应记录
- 所有重试动作必须有 retry_count

---

## 9. 配置设计

建议配置分层：

### 系统级配置
- 数据库路径
- 日志目录
- 默认时区
- 默认模型
- 重试策略

### 集成级配置
- PubMed base_url
- NCBI api_key
- Feishu webhook / app config
- LLM provider / model / timeout

### 任务级配置
- query_expression
- schedule
- language
- relevance_prompt_profile
- delivery_target

---

## 10. 失败恢复策略

### PubMed 查询失败
- 重试有限次数
- 若仍失败，标记 run 失败
- 下轮继续按时间窗口补偿

### LLM 失败
- paper 保留为 `summary_pending`
- 不阻塞整体抓取
- 后台重跑或下一轮补跑

### 飞书推送失败
- 写入 `delivery_failed`
- 支持重试队列

### 用户反馈写入失败
- 原始 webhook payload 落盘
- 支持补偿回放

---

## 11. 推荐的迭代顺序

## Phase 1：可运行 MVP

目标：先跑通完整闭环。

包含：

- 单 query 定时检索
- PubMed 增量抓取
- SQLite 存储
- LLM 结构化总结
- 飞书单卡推送
- 手工反馈写入

不包含：

- 多用户
- 高级个性化排序
- 多端同步
- 复杂权限系统

## Phase 2：反馈驱动优化

包含：

- 反馈标签完善
- 偏好画像更新
- 二阶段总结
- 更智能排序

## Phase 3：多端扩展

包含：

- Apple Notes / Shortcuts 归档
- Digest 日报
- Obsidian / Notion 同步
- Web 审核台

---

## 12. 关键接口边界

建议先把以下接口定义稳定下来，再开始写实现：

### QueryTaskService
- create_query_task
- update_query_task
- disable_query_task
- list_active_query_tasks

### PubMedService
- search_pmids
- fetch_papers

### PaperService
- upsert_paper
- attach_query_hit
- list_new_papers_for_run

### LlmSummaryService
- summarize_paper
- rerank_for_user_profile

### DeliveryService
- send_paper_card
- retry_failed_delivery

### FeedbackService
- record_feedback
- update_review_state

### PreferenceService
- rebuild_preference_profile
- get_prompt_context

---

## 13. 对 Apple Notes / Mac 端的定位

Apple Notes 更适合作为归档或日报容器，不建议作为主交互台。

建议定位：

- 飞书：主交互入口
- Notes：每日汇总归档
- SQLite / PostgreSQL：状态真源

原因：

- 飞书更适合消息卡与按钮交互
- Notes 更适合沉淀精读摘要和人工笔记
- 数据真源必须在数据库，而不是消息平台或笔记软件中

---

## 14. 项目最终形态

该系统最终应具备三种能力：

### 1. 增量发现
自动发现与你研究方向相关的新文献。

### 2. 结构化理解
自动把论文转成适合快速判断的研究卡片。

### 3. 偏好学习
根据你的标注持续调整筛选和总结倾向。

因此，这不是一个简单的“PubMed 抓取器”，而是一个：

**面向科研工作流的个性化文献监控与反馈学习系统。**

---

## 15. 当前建议的技术基线

- 语言：Python
- 调度：APScheduler / cron
- 存储：SQLite（MVP）→ PostgreSQL（升级）
- PubMed 接入：E-utilities
- LLM：可切换 provider 的统一封装
- 推送：飞书自定义机器人 / app bot
- 配置：yaml + env
- 日志：jsonl 结构化事件日志

---

## 16. 下一步执行方式

后续开发建议严格按下面顺序推进：

1. 先固化 schemas
2. 再固化 repositories
3. 再写 PubMed integration
4. 再写 monitor run 主流程
5. 再写 LLM summary pipeline
6. 再写 飞书 card delivery
7. 最后接 feedback 与 preference learning

先不要一开始就把所有“智能化”做进去。
先把“稳定的数据流 + 清晰的边界 + 可恢复的状态机”搭好。

