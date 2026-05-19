# Security Checklist (Python / FastAPI)

当改动涉及认证、授权、用户输入、外部集成、数据存储时，在 Pass 1 中额外检查以下项。

## A.1 Secrets & 配置

- [ ] 代码中无硬编码的密码、API key、token（`grep -i "password\|secret\|api_key\|token"` 过 diff）
- [ ] `.env` / `.env.local` / `*.pem` / `*.key` 在 `.gitignore` 中
- [ ] 敏感配置走 `pydantic-settings` + 环境变量，不走代码常量
- [ ] DEBUG 模式在生产环境关闭，不泄露 traceback / 内部信息

## A.2 认证

- [ ] 密码使用 bcrypt (≥12 rounds) / scrypt / argon2 哈希，不存明文
- [ ] Session / JWT token 有过期时间，合理的 max-age
- [ ] 登录端点有频率限制（≤10 次 / 15 分钟）
- [ ] 密码重置 token 一次性使用，≤1 小时过期
- [ ] Token 校验包含签名、过期时间、issuer 验证

## A.3 授权（OWASP #1: Broken Access Control）

- [ ] 每个受保护端点检查认证状态
- [ ] 每个资源访问检查归属 / 角色（防止 IDOR）
- [ ] 管理端点要求 admin 角色验证
- [ ] 列表接口默认按 owner / tenant 过滤，不返回全量
- [ ] 不能通过 ID 枚举访问他人资源

## A.4 输入校验（OWASP #3: Injection）

- [ ] 所有用户输入在系统边界（API route / DTO）校验
- [ ] 校验使用白名单而非黑名单
- [ ] 字符串长度约束（min/max）、数值范围约束
- [ ] SQL 查询参数化（SQLAlchemy bindparam），无字符串拼接
- [ ] 文件上传：类型限制、大小限制、内容校验
- [ ] URL / email / path 使用 Pydantic 校验器，不直接透传
- [ ] 重定向 URL 校验，防止 Open Redirect

## A.5 数据保护

- [ ] API 响应排除敏感字段（`password_hash`、`reset_token`、`secret_key`）
- [ ] 日志不记录密码、token、完整卡号等敏感数据
- [ ] 所有外部通信使用 HTTPS
- [ ] PII 按合规要求加密存储

## A.6 CORS 与 Headers

- [ ] CORS origin 白名单，不使用 `allow_origins=["*"]`（开发环境除外）
- [ ] 生产环境设置安全 headers：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`
- [ ] Cookie 设置 `httponly`、`secure`、`samesite`

## A.7 依赖安全

- [ ] `pip audit` 或 `safety check` 无 critical / high 漏洞
- [ ] 不引入无维护或 star 极低的第三方包
- [ ] 升级依赖时检查 changelog 中的安全修复

## A.8 错误处理

- [ ] 生产环境返回通用错误信息，不暴露内部细节（SQL、堆栈、文件路径）
- [ ] 安全事件有结构化日志（登录失败、越权尝试、token 过期）
- [ ] 异常不被静默吞掉（`except: pass` 需要有明确理由）

## A.9 OWASP Top 10 速查

| # | 漏洞类型 | 防护措施 |
|---|---------|---------|
| 1 | Broken Access Control | 每端点 auth + ownership 校验 |
| 2 | Cryptographic Failures | HTTPS + 强哈希 + 不在代码中存 secret |
| 3 | Injection | 参数化查询 + Pydantic 校验 |
| 4 | Insecure Design | 威胁建模 + spec 驱动开发 |
| 5 | Security Misconfiguration | 安全 headers + 最小权限 + 依赖审计 |
| 6 | Vulnerable Components | `pip audit` + 保持依赖更新 |
| 7 | Auth Failures | 强密码 + 频率限制 + session 管理 |
| 8 | Data Integrity Failures | 校验更新来源 + 签名制品 |
| 9 | Logging Failures | 记录安全事件 + 不记录 secret |
| 10 | SSRF | 校验/白名单 URL + 限制出站请求 |
