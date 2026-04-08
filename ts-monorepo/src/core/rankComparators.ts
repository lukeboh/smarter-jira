import type { RankOptions } from "./ranking";

export interface IssueLike {
  key: string;
  fields: Record<string, unknown>;
}

export function buildComparator(options: RankOptions, statusOrder?: string[], issuetypeOrder?: string[], epicOrder?: string[]) {
  const order = normalizeOrder(options.rankBy, options.order);
  const statusMap = mapOrder(statusOrder);
  const issuetypeMap = mapOrder(issuetypeOrder);
  const epicMap = mapOrder(epicOrder);

  return (a: IssueLike, b: IssueLike): number => {
    for (let i = 0; i < options.rankBy.length; i++) {
      const criterion = options.rankBy[i];
      const direction = order[i];
      const valueA = getCriterionValue(a, criterion, statusMap, issuetypeMap, epicMap);
      const valueB = getCriterionValue(b, criterion, statusMap, issuetypeMap, epicMap);

      const comparison = compareValues(valueA, valueB);
      if (comparison !== 0) {
        return direction === "asc" ? comparison : -comparison;
      }
    }
    return 0;
  };
}

function normalizeOrder(rankBy: string[], order?: string[]): string[] {
  if (!order || order.length === 0) {
    return rankBy.map(() => "asc");
  }
  if (order.length === 1) {
    return rankBy.map(() => order[0] ?? "asc");
  }
  if (order.length !== rankBy.length) {
    throw new Error("Número de direções de ordenação diferente do número de critérios");
  }
  return order;
}

function mapOrder(values?: string[]): Map<string, number> | undefined {
  if (!values) return undefined;
  const map = new Map<string, number>();
  values.forEach((value, index) => map.set(value.toLowerCase(), index));
  return map;
}

function getCriterionValue(
  issue: IssueLike,
  criterion: string,
  statusMap?: Map<string, number>,
  issuetypeMap?: Map<string, number>,
  epicMap?: Map<string, number>
) {
  switch (criterion) {
    case "key":
      return parseIssueKey(issue.key);
    case "priority":
      return Number((issue.fields.priority as { id?: string })?.id ?? Number.MAX_SAFE_INTEGER);
    case "status": {
      const statusName = (issue.fields.status as { name?: string; statusCategory?: { id?: number } })?.name;
      if (statusName && statusMap) {
        const normalized = statusMap.get(statusName.toLowerCase());
        if (normalized !== undefined) return normalized;
      }
      const categoryId = (issue.fields.status as { statusCategory?: { id?: number } })?.statusCategory?.id;
      if (categoryId) {
        const categoryMap: Record<number, number> = { 2: 0, 4: 1, 3: 2 };
        return categoryMap[categoryId] ?? 99;
      }
      return Number.MAX_SAFE_INTEGER;
    }
    case "issuetype": {
      const name = (issue.fields.issuetype as { name?: string })?.name;
      if (name && issuetypeMap) {
        const normalized = issuetypeMap.get(name.toLowerCase());
        if (normalized !== undefined) return normalized;
      }
      return name ?? "";
    }
    case "epic": {
      const epic = (issue.fields as Record<string, unknown>)["epic"] ?? (issue.fields as Record<string, unknown>)["Epic"];
      if (typeof epic === "string" && epicMap) {
        const normalized = epicMap.get(epic.toLowerCase());
        if (normalized !== undefined) return normalized;
      }
      return epic ?? "";
    }
    default:
      return (issue.fields as Record<string, unknown>)[criterion] ?? (issue as unknown as Record<string, unknown>)[criterion];
  }
}

function compareValues(a: unknown, b: unknown): number {
  if (a === b) return 0;
  if (a === undefined || a === null) return 1;
  if (b === undefined || b === null) return -1;

  if (typeof a === "number" && typeof b === "number") {
    return a - b;
  }

  if (Array.isArray(a) && Array.isArray(b)) {
    const length = Math.max(a.length, b.length);
    for (let i = 0; i < length; i++) {
      const result = compareValues(a[i], b[i]);
      if (result !== 0) return result;
    }
    return 0;
  }

  return String(a).localeCompare(String(b));
}

function parseIssueKey(key: string): [string, number] {
  const [prefix, number] = key.split("-");
  const parsed = Number(number);
  if (Number.isNaN(parsed)) {
    return [key, Number.MAX_SAFE_INTEGER];
  }
  return [prefix, parsed];
}
