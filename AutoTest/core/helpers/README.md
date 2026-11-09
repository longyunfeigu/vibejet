# helpers

## 职责
共享测试夹具库，提供工厂类、常量配置和工具函数，被 `cases/` 和 `bdd/steps/` 统一导入，避免重复代码。

## 内容

| 文件 | 说明 |
|------|------|
| `kb-factory.ts` | KbFactory — Knowledge Hub 测试数据工厂，负责知识库、文档等测试对象的创建和清理 |
| `agent-factory.ts` | AgentFactory — Voice Agent 测试数据工厂，负责座席配置、会话等测试对象的创建和清理 |
| `constants.ts` | 全局常量，包含超时配置、默认等待时间、环境标识等 |

## 使用

在测试文件中直接导入所需工厂类或常量：

```typescript
import { KbFactory } from '../helpers/kb-factory';
import { AgentFactory } from '../helpers/agent-factory';
import { TIMEOUT, BASE_URL } from '../helpers/constants';
```

注意事项：
- 工厂类应负责测试数据的完整生命周期（创建 + 清理），确保测试间互不干扰
- 新增共享逻辑时优先放入 helpers/，避免在 cases/ 或 steps/ 中出现重复实现
- 常量值不得硬编码在用例中，统一在 `constants.ts` 中定义后引用
