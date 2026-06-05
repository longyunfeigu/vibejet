# Story 5.3 (US012): 主观题人工复核改终分

**用户故事**: 作为出题管理员，我可以复核主观题 AI 给分并采纳/改分/人工给分以定终分，以便整卷成绩在保留 AI 原始依据的前提下由人把关确定

#### 验收标准

**Happy Path**
- [ ] confirm 采纳 AI 分 → final_score=ai_score，status=final `验证: API PUT /api/v1/exam/question-scores/{id}/review {action:"confirm"} → 200 + data.final_score==ai_score + data.status="final"`
- [ ] adjust 改分覆盖 → manual_score=final_score=score，保留 ai_score/ai_rationale `验证: API PUT .../review {action:"adjust",score:8} → 200 + final_score=8; DB question_scores → manual_score=8 AND ai_score 未变`
- [ ] manual 对 pending_manual/needs_manual 题人工给分 → final_score=score，status=final `验证: API PUT .../review {action:"manual",score:6} → 200 + final_score=6 + status="final"`

**Error Paths**
- [ ] score 超出 [0, max_score] → 422 `验证: API PUT .../review {action:"adjust",score:999} → 422 + error 指向 score_out_of_range`
- [ ] action 非法 / adjust·manual 缺 score / question_score 不存在 → 422 或 404 `验证: API PUT .../review {action:"adjust"} (缺score) → 422 invalid_review_action; PUT /question-scores/999999/review → 404 question_score_not_found`

**Integration**
- [ ] 某 submission 全部 question_scores 转 final → 同步算 total_score=Σfinal_score 并条件更新 grading_status='graded'（并发只翻转一次） `验证: pytest test_all_final_triggers_graded_total_score_once → PASSED; DB submissions → total_score=Σfinal_score, grading_status="graded"`

#### 前端验收标准
- [ ] 复核页展示每道主观题的 AI 给分与评分依据，提供采纳/改分/人工给分入口 `验证: Browser 复核页 → 每主观题显示 ai_score + rationale + 采纳/改分/人工给分控件`
- [ ] 全部题定终分后展示整卷总分与 graded 状态 `验证: Browser 全部复核完 → 总分文案出现 + 状态显示已评分(graded)`

#### Assumptions
- 无

**覆盖度自检**: 派生 ✓（决策表: action ∈ {confirm,adjust,manual} × 状态；BVA: score 0/max/越界）/ Happy ✓ / Edge N/A — 边界并入 Error 的越界校验 / Error ✓ / Integration ✓ / FE ✓ / AC 总数 7 ≤7 ✓ / Assumptions "无"
**参考**: docs/project/api/grading.md（PUT review confirm/adjust/manual, ACD1 触发）, docs/project/data/grading.md（保留 AI 原始 R5.3, 终分触发总分 ACD1）
**依赖**: Story 5.1, Story 5.2
