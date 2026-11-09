/**
 * Generalized per-worker cleanup registry.
 *
 * Replaces the agent-only cleanup-registry. Each Playwright worker runs tests
 * sequentially, so a module-level instance is worker-local and safe from
 * cross-worker pollution. Entities are keyed by type so the global After hook
 * can dispatch each id to the matching xxxApi.delete().
 */

export type EntityType = string;

export interface CleanupRegistry {
  register(type: EntityType, id: string | number | undefined | null): void;
  peek(type: EntityType): string[];
  flushAll(): Record<EntityType, string[]>;
}

export function createCleanupRegistry(): CleanupRegistry {
  const store = new Map<EntityType, string[]>();

  return {
    register(type, id) {
      const value = (id ?? '').toString().trim();
      if (!value) return;
      const list = store.get(type) ?? [];
      if (!list.includes(value)) {
        list.push(value);
        store.set(type, list);
      }
    },
    peek(type) {
      return [...(store.get(type) ?? [])];
    },
    flushAll() {
      const out: Record<EntityType, string[]> = {};
      for (const [type, ids] of store.entries()) {
        if (ids.length) out[type] = [...ids];
      }
      store.clear();
      return out;
    },
  };
}

/** Shared worker-local singleton used by entity factories and the global After hook. */
export const registry = createCleanupRegistry();
