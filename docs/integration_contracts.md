# Integration Contracts

## 1. 总体原则

integration 层只做外部系统适配：
- 请求构造
- 响应解析
- 错误归一化

integration 层不负责：
- repository 落盘
- monitor run 编排
- 项目级业务状态机

## 2. PubMed Integration 边界

输入：
- `query_expression`
- `start_date`
- `end_date`
- `retmax`

输出：
- PMID 列表
- 原始 ESearch/ESummary 响应
- 映射后的 `PaperCreate` 列表

模块职责：
- `search_client.py`: 调 ESearch，处理超时和基础错误。
- `fetch_client.py`: 调 ESummary（可后续替换 EFetch）。
- `mapper.py`: 外部 payload -> 内部 `PaperCreate`，保留 `raw_payload`。
- `service.py`: 串联 search/fetch/map，返回统一结果对象。

## 3. LLM Integration 边界

输入：
- 论文对象（`PaperDB | PaperView`）
- 可选偏好上下文（`preference_context`）

输出：
- 结构化 `LlmSummaryOutput`
- 健康检查结果 `LlmHealthcheckResult`

模块职责：
- `client.py`: `chat_json` 与 `healthcheck`，provider/model/timeout 可配置。
- `prompt_builder.py`: 通用总结 prompt + 偏好映射 prompt。
- `schemas.py`: 非持久化输出结构定义。
- `service.py`: Stage A 总结 + Stage B 偏好映射（预留），统一输出结构化对象。

## 4. Feishu Integration 边界

输入：
- 论文对象
- LLM 结构化总结
- metadata
- webhook 配置

输出：
- 卡片 payload（构造阶段）
- `FeishuDeliveryResult`（发送阶段）

模块职责：
- `card_builder.py`: 仅构造 payload，不发请求。
- `client.py`: webhook 发送/更新接口，统一错误处理 + 重试参数。
- `schemas.py`: 投递结果对象。

## 5. 分层依赖约束

可以依赖 integration 的层：
- workflow/service 编排层
- application use-case 层

不可以直接越层调用 integration 的层：
- repository 层
- schema persistence 层
- 纯 domain model 层

并且：任何上层若要持久化 integration 结果，必须通过 repository 完成。
