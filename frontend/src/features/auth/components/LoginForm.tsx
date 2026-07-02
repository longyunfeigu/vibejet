// input: useLogin(), loginSchema (RHF + zodResolver)
// output: LoginForm 组件 —— 编辑排印式表单（下划线输入 + 加宽字距小标签 + 墨绿实心按钮）
// pos: auth feature - 登录表单 UI；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'

import { useLogin } from '../hooks/useLogin'
import { loginSchema, type LoginInput } from '../types'

const labelClass = 'text-ink-faint text-xs tracking-[0.32em]'
const inputClass =
  'border-line placeholder:text-ink-ghost focus-visible:border-ink h-11 rounded-none border-0 border-b bg-transparent px-0 text-base shadow-none focus-visible:ring-0 focus-visible:shadow-[0_1px_0_0_var(--ink)]'

export function LoginForm() {
  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })
  const { mutate, isPending } = useLogin()

  function onSubmit(values: LoginInput) {
    mutate(values)
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-7 text-left">
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem className="gap-1">
              <FormLabel className={labelClass}>用户名或邮箱</FormLabel>
              <FormControl>
                <Input
                  className={inputClass}
                  placeholder="you@example.com"
                  autoComplete="username"
                  aria-required
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem className="gap-1">
              <FormLabel className={labelClass}>密码</FormLabel>
              <FormControl>
                <Input
                  className={inputClass}
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  aria-required
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button
          type="submit"
          disabled={isPending}
          className="bg-pine text-cream hover:bg-pine-deep mt-2 h-12 w-full rounded-[10px] text-[15px] font-medium tracking-[0.1em] shadow-none transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.99]"
        >
          {isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />
              登录中…
            </>
          ) : (
            '登录'
          )}
        </Button>
      </form>
    </Form>
  )
}
