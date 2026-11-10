/**
 * E2E 环境配置读取模块
 *
 * 读取优先级：
 *   1. 全量 env 变量（E2E_BASE_URL + E2E_USERNAME + E2E_PASSWORD）→ 直接使用（CI 兼容）
 *   2. E2E_ENV → 从 environments.json 查找对应环境
 *   3. environments.json 中的 default 环境
 *   4. 抛出错误
 */

import * as fs from 'fs';
import * as path from 'path';

export interface EnvConfig {
  name: string;
  base_url: string;
  username: string;
  password: string;
  email?: string;
  [key: string]: unknown;
}

const ENVIRONMENTS_PATH = path.resolve(__dirname, 'environments.json');

function loadEnvironmentsFile(): { default: string; environments: Record<string, Omit<EnvConfig, 'name'>> } | null {
  if (!fs.existsSync(ENVIRONMENTS_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(ENVIRONMENTS_PATH, 'utf-8'));
  } catch {
    return null;
  }
}

export function getE2EConfig(): EnvConfig {
  // 1. 全量 env 变量（CI 兼容）。合并 environments.json 里同名环境的其余字段，
  //    这样 globalSetup 之后派生的 worker 拿到的也是完整配置。
  if (process.env.E2E_BASE_URL && process.env.E2E_USERNAME && process.env.E2E_PASSWORD) {
    const envName = process.env.E2E_ENV ?? 'custom';
    const extraData = (loadEnvironmentsFile()?.environments?.[envName] ?? {}) as Record<string, unknown>;
    return {
      ...extraData,
      name: envName,
      base_url: process.env.E2E_BASE_URL,
      username: process.env.E2E_USERNAME,
      password: process.env.E2E_PASSWORD,
      email: process.env.E2E_EMAIL ?? (extraData['email'] as string | undefined),
    } as EnvConfig;
  }

  // 2 & 3. environments.json（E2E_ENV 指定 或 default）
  const envFile = loadEnvironmentsFile();
  if (envFile) {
    const envName = process.env.E2E_ENV ?? envFile.default;
    const envData = envFile.environments[envName];
    if (envData) {
      return { name: envName, ...envData } as EnvConfig;
    }
    throw new Error(
      `[e2e] environments.json 中未找到环境 "${envName}"。\n` +
      `可用环境: ${Object.keys(envFile.environments).join(', ')}`
    );
  }

  // 4. 报错
  throw new Error(
    '[e2e] 未找到环境配置。\n' +
    '请创建 config/environments.json（参考 config/environments.example.json），\n' +
    '或设置环境变量 E2E_BASE_URL / E2E_USERNAME / E2E_PASSWORD。'
  );
}

/** 返回当前环境对应的 auth-state 文件路径，每个环境独立缓存 */
export function getAuthStatePath(envName: string): string {
  return path.resolve(__dirname, `auth-state-${envName}.json`);
}
