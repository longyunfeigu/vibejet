# Activation Pipeline — 代码上线后激活 Pending 用例

> Loaded on demand by `SKILL.md`. Follow this file (NOT the main Pipeline) when the
> trigger below matches. Same module structure, validation commands, and stability
> rules as the main skill apply.

**触发条件**：用户说 "激活 pending 用例" / "activate pending" / "代码上线了，激活用例"，并指定模块或 delivery doc。

### Step A — 确认激活目标

询问或从上下文中获取：
- 哪个模块（`modules/{module}/`）？
- 激活哪些场景（全部 pending / 指定 delivery doc 关联的场景）？

列出 `{module}-{feature}.pending.feature` 中所有待激活的场景标题，让用户确认范围。

### Step B — 运行实现门检查（同 Phase 2.0）

对每个待激活场景，确认其后端路由和前端组件已在代码库中存在：

```bash
# 后端：路由已注册
grep -n "{api-keyword}" RD/voice-agent/backend/app/main.py

# 后端：实现文件存在 (排除 tests)
find RD/voice-agent/backend/app -name "*.py" -not -path "*/tests/*" | xargs grep -l "{api-keyword}" 2>/dev/null

# 前端：组件文件存在 (关注 src，排除 tests)
find RD/voice-agent/frontend/src -name "{ComponentName}.tsx" 2>/dev/null
find RD/voice-agent/frontend/src -type f \( -name "*.tsx" -o -name "*.ts" \) -not -path "*/__tests__/*" | xargs grep -l "{feature-keyword}" 2>/dev/null | head -5
```

- 检查通过 → 继续 Step C
- 检查未通过 → 停止，告知用户哪些场景对应的代码还未实现，不激活

### Step C — 将场景从 pending 移入主 feature

从 `{module}-{feature}.pending.feature` 中剪切目标场景，追加到 `{module}-{feature}.feature` 末尾：
- **Assign TC tags**: pending scenarios may lack TC tags — assign `@{CASE_ID}` before moving. The Case ID must come from csv rows in `manual-test-cases-en.csv`; do not invent a second numbering scheme in feature files.
- 保留场景原有的其他标签和步骤文本，不修改
- feature 文件仅英文，无 `.cn.feature` 中文副本——不需要同步任何中文 feature。
- 若 pending 文件移空，删除该文件；若仍有未激活场景，保留文件

### Step D — 实现 Page Object 方法

在 `modules/{module}/{feature}/pages/{FeatureName}Page.ts` 中，为 Step C 移入的每个场景补充缺失的 POM 方法：

```bash
# 先检查当前 POM 已有哪些方法
grep -n "async " modules/{module}/{feature}/pages/{FeatureName}Page.ts
```

- 只补充场景中用到的新方法，不改动已有方法
- 根据 Step B 发现的实际组件 selector 来定位元素（不凭 delivery docs 推测）
- 读取真实源码（`.tsx` 文件）确认 `placeholder`、`aria-label`、`role`、`data-testid` 等属性

### Step E — 实现 Step Definitions

在 `modules/{module}/{feature}/steps/{module}-{feature}.steps.ts` 中补充新步骤：

```bash
# 先查已有步骤，避免重复定义
grep -n "Given\|When\|Then" modules/{module}/{feature}/steps/{module}-{feature}.steps.ts
grep -n "Given\|When\|Then" modules/common/steps/common.steps.ts
```

- 已有句式直接复用，不重新定义
- 每个步骤只调用一个 POM 方法

### Step F — 验证

```bash
npm run bdd:gen      # 0 missing step definitions
npm run typecheck    # 0 TypeScript errors
npm run lint:bdd     # all checks PASS
```

逐一修复报错后再进入下一步。

### Step G — 更新 csv

用 Python 打开 `manual-test-cases-en.csv` 和 `manual-test-cases-cn.csv`，
将激活场景对应行的 Notes 列中 `Implementation pending — feature not yet in codebase` 字样删除。

```python
import csv, re, tempfile, shutil

# The case IDs of the scenarios you just moved from pending to active
activated_case_ids = {"VA-FBR-001", "VA-FBR-002"} # Update this dynamically

for filepath in ['...en.csv', '...cn.csv']:
    rows = []
    with open(filepath, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if row[0] in activated_case_ids:
            note = row[15] if len(row) > 15 else ''
            row[15] = re.sub(r'\s*\|?\s*Implementation pending[^|]*', '', note).strip(' |')
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(rows)
```

### Activation Output Report

```
=== Pending → Active Pipeline Complete ===

Module: {module}
Activated from: {module}-{feature}.pending.feature

Step B — Implementation Gate
  ✓ {n} backend route(s) verified in main.py
  ✓ {n} frontend component(s) found in src/

Step C — Scenarios moved
  ✓ {n} scenario(s) moved to {module}-{feature}.feature
  ({n} scenario(s) remain in pending — not yet implemented)

Step D/E — Implementation
  ✓ {n} method(s) added to {FeatureName}Page.ts
  ✓ {n} step(s) added to {module}-{feature}.steps.ts

Step F — Validation
  ✓ bdd:gen: 0 missing steps
  ✓ typecheck: 0 errors
  ✓ lint:bdd: all checks PASS

Step G — csv updated
  ✓ {n} rows cleared of "Implementation pending" note

Run: npm run test:{module-alias}:uat
```
