import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'src/routeTree.gen.ts'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
  // 前端规范里有确定答案的两条交给机器拦（规范来源：.agents/skills/frontend-dev-guidelines）。
  // 绕开共享组件和 token 的写法会被下一个页面照抄，审查靠人记不稳。
  // 改动前已有的违规记在 eslint-suppressions.json，只拦新增；修掉一处后跑 `pnpm exec eslint . --prune-suppressions`。
  {
    files: ['src/**/*.tsx'],
    ignores: ['src/components/ui/**', '**/*.test.tsx', 'src/test/**'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: 'JSXOpeningElement[name.name=/^(button|input|select|textarea)$/]',
          message:
            '用 @/components/ui 里的共享组件；缺的先 `npx shadcn@latest add <组件>` 补进 components/ui，再在业务里用。',
        },
        {
          selector:
            'JSXAttribute[name.name=/^(className|style)$/] :matches(Literal[value=/#[0-9a-fA-F]{3,8}\\b/], TemplateElement[value.raw=/#[0-9a-fA-F]{3,8}\\b/])',
          message:
            '颜色走 token（如 bg-primary、text-destructive），不写裸 hex；新颜色先进 DESIGN.md → index.css。',
        },
      ],
    },
  },
  prettier,
)
