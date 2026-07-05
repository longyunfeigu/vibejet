// input: authStore(setSession/getSession/clearSession), queryClient
// output: authStore 单元测试(登出清空 query 缓存 + 会话)
// owner: wanhua.gu
// pos: 跨域基础设施 - authStore 测试；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import { afterEach, describe, expect, it } from 'vitest'

import { clearSession, getSession, setSession } from '@/lib/authStore'
import { queryClient } from '@/lib/queryClient'

afterEach(() => {
  clearSession()
})

describe('clearSession', () => {
  it('登出时清空 React Query 缓存，避免换用户重新登录后命中旧用户缓存', () => {
    setSession({ accessToken: 'a', refreshToken: 'r' })
    queryClient.setQueryData(['auth', 'me'], { id: 1, username: 'alice' })
    expect(queryClient.getQueryData(['auth', 'me'])).toBeDefined()

    clearSession()

    expect(queryClient.getQueryCache().getAll()).toHaveLength(0)
    expect(queryClient.getQueryData(['auth', 'me'])).toBeUndefined()
    expect(getSession()).toBeNull()
  })
})
