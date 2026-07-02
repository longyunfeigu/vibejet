// input: useLogin(), loginSchema (RHF + zodResolver)
// output: LoginForm 组件 —— 用户名/邮箱 + 密码表单(填充式输入 + 药丸按钮)，提交触发登录
// owner: wanhua.gu
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

const inputClass =
  'h-12 rounded-2xl border-0 bg-muted px-4 text-base shadow-none placeholder:text-muted-foreground/70 focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-ring/40'

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
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4 text-left">
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem className="gap-1.5">
              <FormLabel className="text-sm font-medium">
                用户名或邮箱 <span className="text-destructive">*</span>
              </FormLabel>
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
            <FormItem className="gap-1.5">
              <FormLabel className="text-sm font-medium">
                密码 <span className="text-destructive">*</span>
              </FormLabel>
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
          className="mt-2 h-12 w-full rounded-full bg-foreground text-base font-semibold text-background transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] hover:bg-foreground/90 active:scale-[0.985]"
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
