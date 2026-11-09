/**
 * schema.ts — single source of truth for Release-Check guide values.
 * Later phases import from here; do not duplicate these enums elsewhere.
 */

// Service keys: the deployable parts of vibejet (FastAPI backend, React frontend, gRPC server).
export const SERVICES = ['backend', 'frontend', 'grpc'] as const;

export const GUIDE_TYPES = ['feature', 'bugfix'] as const;
export const SAFETY_LEVELS = ['readonly', 'writes-test-data', 'costly'] as const;
export const RISK_LEVELS = ['high', 'medium', 'low'] as const;
// Per check item, see priority.ts. P0 = basic function, P1 = main scenarios, P2 = minor, non-blocking.
export const PRIORITIES = ['P0', 'P1', 'P2'] as const;

export type Priority = typeof PRIORITIES[number];

// Environment dependencies a guide may declare in `requires` (STANDARD.md 1.15):
// gray:<key>, model:<name fragment>[|<name fragment>...], service:<workload>, or the bare word outbound.
export const REQUIRES_ENTRY = /^(?:(?:gray|service):[A-Za-z0-9][\w.\-/]*|model:[A-Za-z0-9][\w.\-/]*(?:\|[A-Za-z0-9][\w.\-/]*)*|outbound)$/;

export type GuideType = typeof GUIDE_TYPES[number];

export type SectionId =
  | 'background' | 'entry' | 'verify' | 'invariants' | 'data' | 'pitfalls'
  | 'depth' | 'repro' | 'old-behavior' | 'expected-after-fix' | 'root-cause'
  | 'change';

export const SECTION_HEADINGS: Record<SectionId, string[]> = {
  'background': ['Background and goal', '背景与目标'],
  'entry': ['Entry points', '入口'],
  'verify': ['How to verify', '怎么算对'],
  'invariants': ['Must not break', '绝不能坏的底线'],
  'data': ['Test data and cleanup', '前置数据与清理'],
  'pitfalls': ['Easy to misjudge', '容易误判的地方'],
  'depth': ['Depth hints', '深度提示'],
  'repro': ['Reproduction conditions', '复现条件'],
  'old-behavior': ['Behavior on old version', '旧版本的错误现象'],
  'expected-after-fix': ['Expected after fix', '修复后应有的现象'],
  'root-cause': ['Root cause', '根因'],
  'change': ['This change', '本次改动'],
};

const FEATURE_SECTIONS: SectionId[] = [
  'background', 'entry', 'verify', 'invariants', 'data', 'pitfalls', 'change',
];

export const REQUIRED_SECTIONS: Record<GuideType, SectionId[]> = {
  feature: FEATURE_SECTIONS,
  // 'repro' is no longer required (bugs are verified on the new version only); the heading is still recognised in older guides
  bugfix: [...FEATURE_SECTIONS, 'old-behavior', 'expected-after-fix', 'root-cause'],
};
