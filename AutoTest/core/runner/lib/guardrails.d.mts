export function findApiCallViolations(relPath: string, content: string): string[];
export function countControlledWaits(content: string): number;
export const EXEC_TYPES_CN: string[];
export const BACKEND_UNIT_CN: string;
export function collectFeatureCaseIds(content: string): Set<string>;
export function findBackendUnitViolations(
  row: { where: string; caseId: string; exec: string; notes: string },
  featureCaseIds: Set<string>,
): string[];
