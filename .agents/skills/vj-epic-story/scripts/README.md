# vj-epic-story/scripts/

| 文件 | 用途 |
|------|------|
| `validate_story.py` | Story 结构机检：R1 行为 AC ≤7、R2 `验证:` 三要素、R3 Assumptions 三要素、R4 Feature Bundling（`<!-- bundling-ok -->` 可豁免）、R5 无前向依赖。exit 0=过 / 1=有 ERROR 禁止写盘 / 2=用法错误 |

调用方：`vj-epic-story` Phase 5.5（写盘前必跑）、`vj-feature` Phase 2 机检步骤。

```bash
python3 .agents/skills/vj-epic-story/scripts/validate_story.py docs/tasks/epics/epic-1-user.md
python3 .agents/skills/vj-epic-story/scripts/validate_story.py docs/tasks/epics/epic-2-catalog/   # 目录形式
```
