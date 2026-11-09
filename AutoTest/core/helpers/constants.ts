// Global test constants — import from here, never hardcode in test files

export const TEST_PREFIX = 'e2e';

export const TIMEOUTS = {
  page_load: 30_000,
  api_response: 10_000,
  document_processing: 180_000,   // 3 min: KB file indexing
  llm_generation: 300_000,         // 5 min: AI Simulation test generation
  ai_execution: 480_000,           // 8 min: AI Simulation test execution
  eval_run: 300_000,               // 5 min: KB evaluation task
} as const;

export const POLL_INTERVALS = {
  fast: 3_000,
  normal: 5_000,
  slow: 10_000,
  very_slow: 15_000,
} as const;

// KB is now a module within the voice-agent platform; baseURL is set in playwright.config.ts

export const VOICE_AGENT_ENVS = {
  thai: 'https://wizlynn-thai.wiz.ai/',
  sg: 'https://wizlynn-sg.wiz.ai/',
  br: 'https://wizlynn-br.wiz.ai/',
  dev: 'https://wizlynn-dev.wiz.ai/',
  uat: 'https://wizlynn-uat.wiz.ai/',
} as const;

export const AI_SIM_BACKEND = {
  thai: 'https://wizlynn-thai.wiz.ai',
  sg: 'https://wizlynn-sg.wiz.ai',
} as const;
