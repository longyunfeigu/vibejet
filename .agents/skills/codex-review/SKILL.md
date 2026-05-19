---
name: codex-review
description: 文档/设计审查闭环。将 Claude 生成的文档（PRD、架构设计、API 设计、数据模型、技术方案）发送给 Codex 进行独立审查，Claude Code 自主判断采纳建议并修改文档。在 prd-generator-ears、api-design、architecture、data-model 等 skill 生成文档后自动执行，用户可说"跳过审查"来跳过。也可手动调用 /codex-review。
---

# codex-review

让 Codex 作为独立审查者，对 Claude 生成的文档/设计进行结构化审查。Claude Code 对审查建议自主判断采纳，无需用户逐条确认。

## 适用场景

- 任何文档生成 skill（prd-generator-ears、api-design、architecture、data-model）完成后的**自动后置步骤**
- 用户手动输入 `/codex-review` 审查指定文档
- 用户想对技术方案、设计文档做独立交叉验证

## 不适用场景

- 代码审查 → 使用 `review` skill
- 用户明确说"跳过审查"或"不需要审查"
- 文档尚未生成完毕（半成品状态）

## 自动触发机制

当以下 skill 生成文档完毕后，**直接执行审查，不询问用户**：
- `prd-generator-ears`
- `api-design`
- `architecture`
- `data-model`

用户可随时说"跳过审查"中断。

## Workflow

### Phase 1: 准备

1. **确定审查目标**：
   - 如果是自动触发：使用刚生成的文档内容
   - 如果是手动调用：用户需指定文件路径或文档内容
   - 如果用户未指定且工作区有最近生成的文档，询问确认

2. **检测文档类型**（自动，基于内容特征和来源 skill）：
   - PRD / 需求文档
   - 架构设计文档
   - API 设计文档
   - 数据模型文档
   - 技术方案文档
   - 通用文档（兜底）

3. **写入临时文件**：
   ```bash
   # 将文档内容写入临时文件供 Codex 读取
   /tmp/codex-review-{timestamp}.md
   ```

### Phase 2: Codex 审查

根据文档类型选择审查维度，调用 Codex 执行独立审查。

#### 审查维度（按文档类型）

**PRD / 需求文档：**
- 场景完整性：是否覆盖了核心用户场景和边缘场景
- 边界条件：异常流、极端输入、并发场景是否考虑
- 用户旅程遗漏：关键步骤是否有跳跃或断裂
- 验收标准明确度：AC 是否可测试、无歧义
- 需求冲突：不同需求之间是否存在矛盾

**架构设计文档：**
- 组件职责清晰度：每个组件是否单一职责、边界明确
- 依赖合理性：依赖方向是否正确、是否有循环依赖
- 扩展性：关键决策点是否预留了扩展空间
- 故障点：单点故障、级联失败、降级策略
- 一致性：与已有架构的兼容性

**API 设计文档：**
- 接口一致性：命名、参数风格、响应格式是否统一
- 错误码覆盖：异常场景是否都有对应错误码和描述
- 幂等性：写操作是否考虑了幂等设计
- 版本兼容：是否考虑了向后兼容和版本演进
- 安全性：认证、授权、输入验证是否到位

**数据模型文档：**
- 范式合理性：是否有不必要的冗余或过度范式化
- 索引策略：查询模式是否有对应索引支持
- 数据一致性：跨表关联是否有完整性约束
- 扩展性：字段设计是否支持未来变更
- 性能影响：大表、热点数据、分区策略

**技术方案文档：**
- 方案可行性：技术选型是否成熟、团队是否有能力落地
- 风险评估：已识别风险是否有对应缓解措施
- 替代方案对比：是否评估了其他方案及其 trade-off
- 实施步骤完整性：步骤是否可执行、是否有遗漏
- 回滚方案：出问题时如何回退

#### 执行 Codex 审查命令

```bash
codex exec -m gpt-5.4 \
  -c model_reasoning_effort="xhigh" \
  -s read-only \
  --skip-git-repo-check \
  --full-auto \
  "You are a senior technical reviewer with deep expertise in software architecture and system design.

Review the following [DOC_TYPE] document.

Focus on these dimensions:
[REVIEW_DIMENSIONS]

Output format — numbered suggestions, each with severity:
[N] [Blocking] concrete issue description → specific fix suggestion
[N] [Non-blocking] concrete issue description → specific fix suggestion

Rules:
- Only report real issues. Do not pad with style suggestions.
- Blocking = will cause production incidents, data loss, security holes, or makes the design unimplementable.
- Non-blocking = improvement opportunities, missing edge cases, clarity issues.
- Each suggestion must be actionable with a concrete fix.
- If no issues found, output: No issues found.

Document to review:
$(cat /tmp/codex-review-{timestamp}.md)" 2>/dev/null
```

**变量替换：**
- `[DOC_TYPE]`：PRD / Architecture Design / API Design / Data Model / Technical Proposal
- `[REVIEW_DIMENSIONS]`：根据上面的审查维度列表填充
- `{timestamp}`：实际时间戳

**超时处理：**
- 设置 `timeout 180` 秒
- 超时后提示用户可重试或降低 reasoning effort

### Phase 3: Claude Code 自主采纳

Claude Code 独立判断每条建议是否采纳，**不询问用户**。

#### 判断标准

| 建议级别 | 判断规则 |
|---------|---------|
| **Blocking** | 默认采纳。仅当建议明显基于错误理解（Codex 未看到完整上下文导致误判）时跳过，并记录跳过原因 |
| **Non-blocking** | 逐条评估：(1) 是否确实提升文档质量或防止后续歧义 → 采纳；(2) 是否纯风格偏好或与项目约定冲突 → 跳过 |

#### 执行流程

1. **解析 Codex 输出**：提取编号建议，分类为 Blocking / Non-blocking

2. **逐条判断**：对每条建议，Claude Code 基于自身对项目上下文的理解决定采纳或跳过

3. **执行修改**：
   - 将采纳的建议应用到原文档
   - 每条修改标注来源：`<!-- codex-review: applied suggestion [N] -->`

4. **输出审查摘要**（告知用户最终结果，不需要用户确认）：

```
Codex 审查完成（N 条建议，X blocking，Y non-blocking）

✅ 已采纳（M 条）：
[1] [Blocking] 问题描述 → 已修复
[3] [Non-blocking] 问题描述 → 已修复

⏭️ 已跳过（K 条）：
[2] [Non-blocking] 问题描述 → 跳过原因：纯风格偏好，与项目现有约定一致
```

5. **清理临时文件**：
   ```bash
   rm -f /tmp/codex-review-{timestamp}.md
   ```

## 错误处理

### Codex 不可用
- 检查 `codex --version`
- 如果未安装或不可用，提示用户安装并跳过审查

### 审查输出为空或格式异常
- 重试一次，降低 reasoning effort 到 `high`
- 仍然失败则输出原始 Codex 响应供用户判断

### 文档过长
- 如果文档超过 50KB，分段审查
- 每段独立调用 Codex，最后合并结果

## 与其他 skill 的关系

- `prd-generator-ears` → 生成 PRD 后自动触发本 skill
- `api-design` → 生成 API 设计后自动触发本 skill
- `architecture` → 生成架构设计后自动触发本 skill
- `data-model` → 生成数据模型后自动触发本 skill
- `review` → 审查代码，本 skill 审查文档，互不冲突
- `codex` → 本 skill 复用 codex skill 的命令格式和配置

## 示例

### 手动审查 PRD

```text
/codex-review docs/prd/user-management.md
```

### 审查最近生成的文档

```text
/codex-review
```
（自动检测最近生成的文档）

### 跳过自动触发的审查

```text
跳过审查
```
