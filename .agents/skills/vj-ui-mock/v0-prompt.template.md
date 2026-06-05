<!--
每屏 v0/Lovable 提示词模板，由 vj-ui-mock Phase B 生成。
落盘：docs/reference/research/designs/{epic-id}/{story-id}-{page}.prompt.md
头部 [BASE] 整段拷贝自 design_guidelines.md 的 ## v0 Base Prompt（不改写）。
-->

# UI 提示词：{屏名}（{路由}）

> 来源：Epic {epic-id} / Story {story-ids}　角色：{role}
> 出图后把截图保存为同目录 `{story-id}-{page}.png`，并回填 Story 的「### 设计参考」表。

---

## 提示词（可直接粘贴进 v0 / Lovable）

```
{此处整段拷贝 design_guidelines.md 的 v0 Base Prompt 内容}

页面：{屏名}　路由：{路由}　使用角色：{role}

这个页面要包含：
- {元素 1（来自 Story 前端验收标准）}
- {元素 2}
- ...

必须画出的状态：
- 默认/有数据态：{描述}
- 空态：{无数据时显示什么}
- Loading 态：{若有后端/AI 调用}
- 错误态：{失败时显示什么 + 重试/兜底入口}

交互：
- {交互 1，如"点提交→未作答弹确认对话框"}
```

---

## 对应验收标准（来自 Story，供出图后自查）

- {逐条列出该屏关联的 `#### 前端验收标准` AC 行}
