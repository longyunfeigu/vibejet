/**
 * Voice Agent 环境配置读取模块
 *
 * 读取优先级：
 *   1. 全量个人 env 变量（VOICE_AGENT_BASE_URL + VOICE_AGENT_USERNAME + VOICE_AGENT_PASSWORD）→ 直接使用（CI 兼容）
 *   2. VOICE_AGENT_ENV → 从 environments.json 查找对应环境
 *   3. environments.json 中的 default 环境
 *   4. 旧版 .env 文件（向后兼容）
 *   5. 抛出错误
 */

import * as fs from 'fs';
import * as path from 'path';

export interface EnvConfig {
  name: string;
  base_url: string;
  username: string;
  password: string;
  org: string;
  understand_language?: string;
  speak_language?: string;
  voice?: string;
  share_code?: string;
  // Extended fields for latency / voice-call runner tests
  livekit_url?: string;
  livekit_api_key?: string;
  livekit_api_secret?: string;
  openai_api_key?: string;
  openai_base_url?: string;
  wiz_tts_base_url?: string;
  backend_api_url?: string;
  sip_bridge_host?: string;
  sip_bridge_port?: number;
  // Pre-configured agent IDs for tests that require a real LLM dialog flow.
  // These agents must exist in the target environment with a published dialog flow
  // that generates Server Response Latency on browser voice calls.
  audio_e2e_agent_id?: string;
  [key: string]: unknown;
}

const ENVIRONMENTS_PATH = path.resolve(__dirname, 'environments.json');
const ENV_PATH = path.resolve(__dirname, '../.env');

function loadEnvironmentsFile(): { default: string; environments: Record<string, Omit<EnvConfig, 'name'>> } | null {
  if (!fs.existsSync(ENVIRONMENTS_PATH)) return null;
  try {
    return JSON.parse(fs.readFileSync(ENVIRONMENTS_PATH, 'utf-8'));
  } catch {
    return null;
  }
}

function loadDotEnv(): Record<string, string> {
  if (!fs.existsSync(ENV_PATH)) return {};
  const vars: Record<string, string> = {};
  for (const line of fs.readFileSync(ENV_PATH, 'utf-8').split('\n')) {
    const match = line.match(/^([^#=]+)=(.*)$/);
    if (match) vars[match[1].trim()] = match[2].trim();
  }
  return vars;
}

export function getVoiceAgentConfig(): EnvConfig {
  // 1. 全量 env 变量（CI 兼容）
  // Merge environments.json extra fields (sip_bridge_host, livekit_url, etc.) so that
  // workers spawned after globalSetup — which inherit BASE_URL/USERNAME/PASSWORD — still
  // receive the full environment config, not just the minimal three-field subset.
  if (
    process.env.VOICE_AGENT_BASE_URL &&
    process.env.VOICE_AGENT_USERNAME &&
    process.env.VOICE_AGENT_PASSWORD
  ) {
    const envName = process.env.VOICE_AGENT_ENV ?? 'custom';
    const envFile = loadEnvironmentsFile();
    const extraData = (envFile?.environments?.[envName] ?? {}) as Record<string, unknown>;
    return {
      ...extraData,
      name: envName,
      base_url: process.env.VOICE_AGENT_BASE_URL,
      username: process.env.VOICE_AGENT_USERNAME,
      password: process.env.VOICE_AGENT_PASSWORD,
      org: process.env.VOICE_AGENT_ORG ?? (extraData['org'] as string | undefined) ?? 'Wiz',
    } as EnvConfig;
  }

  // 2 & 3. environments.json（VOICE_AGENT_ENV 指定 或 default）
  const envFile = loadEnvironmentsFile();
  if (envFile) {
    const envName = process.env.VOICE_AGENT_ENV ?? envFile.default;
    const envData = envFile.environments[envName];
    if (envData) {
      return { name: envName, ...envData } as EnvConfig;
    }
    throw new Error(
      `[voice-agent] environments.json 中未找到环境 "${envName}"。\n` +
      `可用环境: ${Object.keys(envFile.environments).join(', ')}`
    );
  }

  // 4. 旧版 .env 文件（向后兼容）
  const dotEnv = loadDotEnv();
  if (dotEnv.VOICE_AGENT_USERNAME && dotEnv.VOICE_AGENT_PASSWORD) {
    return {
      name: 'legacy',
      base_url: dotEnv.VOICE_AGENT_BASE_URL ?? 'https://wizlynn-thai.wiz.ai/',
      username: dotEnv.VOICE_AGENT_USERNAME,
      password: dotEnv.VOICE_AGENT_PASSWORD,
      org: dotEnv.VOICE_AGENT_ORG ?? 'Wiz',
    };
  }

  // 5. 报错
  throw new Error(
    '[voice-agent] 未找到环境配置。\n' +
    '请创建 config/environments.json（参考 config/environments.example.json），\n' +
    '或设置环境变量 VOICE_AGENT_USERNAME / VOICE_AGENT_PASSWORD / VOICE_AGENT_BASE_URL。'
  );
}

/** 返回当前环境对应的 auth-state 文件路径，每个环境独立缓存 */
export function getAuthStatePath(envName: string): string {
  return path.resolve(__dirname, `auth-state-${envName}.json`);
}
