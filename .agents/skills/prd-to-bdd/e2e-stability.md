# E2E Stability Rules — 写 POM / Steps / 修复 flaky 时必须遵守

> Loaded on demand by `SKILL.md`. **必读** before writing or fixing any Page Object /
> Step Definition in Phase 3 (or when fixing a flaky test).

**原则**：稳定性不是靠等久一点，而是每一步都等"正确的业务状态出现"。

### 禁止 waitForTimeout（CRITICAL）

```typescript
// ❌ 永远不这样写
await page.waitForTimeout(2000);

// ✅ 等具体业务状态
await expect(locator).toBeVisible({ timeout: 30_000 });
await expect(dialog).toBeHidden({ timeout: 15_000 });
await expect(row.getByText('Completed')).toBeVisible({ timeout: TIMEOUTS.document_processing });
```

唯一例外：无 DOM 状态变化可观察时用 `workaroundSleep`（上限 2000ms，必须注释说明原因）。

### 等待网络请求 (Network Waiting) 应对乐观更新

当前端采用乐观更新 (Optimistic UI) 时，UI 会瞬间变化但后台实际仍在处理。此时单纯依靠 UI 断言极易导致后续步骤 Flaky（例如：刚点击创建，UI 列表中立刻出现数据，但马上调用查询接口却查不到，因为数据尚未落库）。此时**必须显式等待核心网络请求响应**。

**注意（防 Race Condition）**：必须在触发动作**之前**建立网络监听。

```typescript
// ✅ 正确写法：先建立监听，再触发动作，最后 await
const responsePromise = this.page.waitForResponse(
  resp => resp.url().includes('/api/v1/resource') && resp.status() === 200
);
await this.page.getByRole('button', { name: 'Save' }).click();
await responsePromise; // 动态等待：接口 50ms 返回就等 50ms，绝不是硬等待
```

### `.waitFor({ state })` 全部替换为 `expect`

```typescript
// ❌ 旧写法 (Anti-pattern)
await locator.waitFor({ state: 'visible', timeout: 10000 });
await this.frame.locator('.result-indicator').waitFor({ state: 'visible', timeout: 20000 });

// ✅ 新写法（报错时含页面快照，推荐）
await expect(locator).toBeVisible({ timeout: 10000 });
await expect(this.frame.locator('.result-indicator')).toBeVisible({ timeout: 20000 });
await expect(locator).toBeHidden({ timeout: 10000 });   // state: 'hidden'
await expect(locator).toBeAttached({ timeout: 10000 }); // state: 'attached'
```

注意：`Promise.race` 链式 `.waitFor().then()` 不能直接替换，需手动改写。

### 统一使用 wait-utils.ts（`core/helpers/wait-utils.ts`）

| 函数 | 用途 |
|------|------|
| `expectVisible(locator, msg?, timeout?)` | 等元素可见 |
| `expectHidden(locator, msg?, timeout?)` | 等元素消失 |
| `waitForStatus(row, statusText, timeout?)` | 等行状态文字 |
| `clickAndWait(button, result, timeout?)` | 点击 + 等结果 |
| `workaroundSleep(page, ms, reason)` | 临时 sleep（≤2000ms）|

timeout 默认值来自 `core/helpers/constants.ts` 的 `TIMEOUTS`，不要硬编码 ms。

### Locator 优先级

| 优先级 | 方法 |
|--------|------|
| 1 | `getByRole` |
| 2 | `getByLabel` / `getByPlaceholder` |
| 3 | `getByText`（精确匹配）|
| 4 | `getByTestId`（推动 FE 加 `data-testid`）|
| 5 | CSS selector（最后手段）|
| ❌ | XPath（禁止）|

### 其他规则

- **Step 只写业务意图**，locator / 等待 / 重试全放 POM
- **Create/Update/Delete 后必须有业务断言**（不能只点按钮）
- **测试数据幂等**：`e2e-` 前缀 + 运行前清理 + 运行后清理
- **异步任务**（文档处理 / AI 生成 / Evaluation）必须等状态字段，不能靠时间估算

### lint 检查

`npm run lint:bdd` 的 **Stability rules** 检测 `steps/*.steps.ts` 里的 `waitForTimeout`。  
`pages/*.ts` 靠人工 review + 渐进迁移（新写禁止，触碰旧代码顺手改）。
