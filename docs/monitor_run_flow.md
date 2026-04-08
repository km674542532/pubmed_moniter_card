# Monitor Run Flow（V1）

## 范围

当前仅支持：
- 单 `query_task` 手动执行
- 单用户视角
- 飞书单卡推送

暂不覆盖：
- 多用户隔离
- 反馈回写与偏好学习闭环
- digest 聚合
- Notes 同步

## 主流程步骤

入口：`MonitorRunService.run_query_task(query_task_id)`

1. 读取 `query_task`，校验启用状态。
2. 基于 `lookback_hours` 计算 `window_start/window_end`。
3. 创建 `monitor_run`，初始状态 `running`。
4. 调用 PubMed integration (`search_and_fetch`) 完成检索与拉取。
5. 将外部记录映射为内部 `Paper` 输入并归一化。
6. 基于 PMID 做全局去重。
7. 对本轮新增 paper 建立 `paper_query_hit`。
8. 逐篇调用 LLM integration 生成结构化 summary。
9. 构建飞书卡片并发送。
10. 写入并更新 `delivery_record`。
11. 汇总结果并更新 `monitor_run` 为 `success/partial_success/failed`。

## 步骤输入输出

- 输入：`query_task_id`
- 关键中间输出：
  - `PubMedSearchAndFetchResult`
  - 去重后的 `PaperDB` 列表
  - 每篇论文 `PaperProcessResult`（LLM 与 delivery 是否成功）
- 最终输出：`MonitorRunResult`

## 状态机定义

运行态（编排层）：
- `running`
- `success`
- `partial_success`
- `failed`

落库态（`MonitorRunStatus`）：
- `running` -> `RUNNING`
- `success` -> `SUCCEEDED`
- `partial_success` -> `PARTIAL`
- `failed` -> `FAILED`

判定规则：
- PubMed 查询整体失败：`failed`
- PubMed 成功但部分 paper 在 LLM 或 delivery 失败：`partial_success`
- 全部流程成功：`success`

## 失败恢复策略

- 单篇 LLM 失败：
  - 记录论文级错误并继续处理下一篇。
  - run 最终可能为 `partial_success`。
- 单篇飞书发送失败：
  - 保留 `delivery_record` 失败记录并继续。
  - run 最终可能为 `partial_success`。
- PubMed 全局失败：
  - 立即结束本次 run，状态 `failed`，携带错误原因。

## 哪些步骤允许 Partial Failure

允许部分失败：
- LLM summary
- Feishu delivery

不允许部分失败（失败即 run failed）：
- 读取 `query_task`
- PubMed 查询与拉取阶段（全局入口数据源失败）

## 结构化事件日志

关键事件：
- `monitor_run_started`
- `pubmed_search_started`
- `pubmed_search_completed`
- `papers_normalized`
- `papers_deduplicated`
- `llm_summary_started`
- `llm_summary_completed`
- `delivery_started`
- `delivery_completed`
- `monitor_run_completed`
- `monitor_run_failed`

统一字段：
- `run_id`
- `query_task_id`
- `step`
- `status`
- `payload_ref`
- `error`
