---
paths:
  - "frontend/**/*.tsx"
  - "frontend/**/*.ts"
---

# 前端铁律（碰前端代码必守）

> 这些是**非协商**的硬规则，按路径自动注入，不依赖 skill 是否加载。
> 详细 how-to（剧本 A/B、富度 checklist、参考技法）见 `.agents/skills/frontend-dev-guidelines/SKILL.md`。

## 富度（避免"像 demo"）

1. **按「页面体验地图」建整屏**：实现一屏时，照 epic 里该屏的 `职责/主操作/次操作/关键状态/信息优先级/体验护栏` 把**整屏建出来**。`#### 前端验收标准`（FE AC）只是其中**可机检的子集**，不是实现上限——**不许只做到刚好过 AC 的最薄版本**。
2. **评审不许空屏**：屏上必须有逼真且有代表性的数据再算完成。
   - 后端先行 → 接真接口（确保 dev 库有 seed 数据）。
   - 后端没好 / 前后端并行 → 用前端 mock（`features/<x>/mock*.ts`）占位，**接口落地即删**。
3. **富度走参考**：按**屏类型**参考一个贴切的外部高级作品的「组成 / 密度 / 交互范式」，用 `docs/project/DESIGN.md` 的 token **重新皮肤化**——**抄骨架与密度，不抄品牌皮**（配色/logo/招牌字）。无外部参考 → 按屏**范式**（列表/控制台、仪表盘、详情、表单/向导、设置）+ 调用 `design-taste-frontend` / `high-end-visual-design` skill 的启发式。
4. **不许孤零零的卡片堆**：有数据就上表格/统计/筛选；补齐三态（加载/空/错误）与次操作。

## 样式与栈（与 frontend-dev-guidelines 一致）

5. 样式 token 唯一来源 = `docs/project/DESIGN.md` → 编译进 `src/index.css`。**不写裸 hex，不用 MUI/emotion/`sx`**；用 Tailwind class + shadcn 组件 + `cn()`。
6. 数据用 `useSuspenseQuery` + `<SuspenseLoader>`，不写 early-return loading。
