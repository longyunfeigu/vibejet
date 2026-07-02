// input: loginSchema
// output: loginSchema 单元测试(校验必填)
// owner: wanhua.gu
// pos: auth feature - 类型/校验测试；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { describe, expect, it } from 'vitest'

import { loginSchema } from './index'

describe('loginSchema', () => {
  it('拒绝空的用户名或密码', () => {
    expect(loginSchema.safeParse({ username: '', password: '' }).success).toBe(false)
    expect(loginSchema.safeParse({ username: 'alice', password: '' }).success).toBe(false)
  })

  it('接受非空用户名 + 密码', () => {
    expect(loginSchema.safeParse({ username: 'alice', password: 'secret12' }).success).toBe(true)
  })
})
