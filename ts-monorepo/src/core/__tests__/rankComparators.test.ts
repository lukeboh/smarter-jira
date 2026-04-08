import { describe, it, expect } from "vitest";
import { buildComparator } from "@core/rankComparators";

const issues = [
  { key: "PROJ-3", fields: { status: { name: "In Progress" }, issuetype: { name: "Story" } } },
  { key: "PROJ-2", fields: { status: { name: "To Do" }, issuetype: { name: "Bug" } } },
  { key: "PROJ-1", fields: { status: { name: "Done" }, issuetype: { name: "Task" } } }
];

describe("buildComparator", () => {
  it("ordena por status customizado", () => {
    const comparator = buildComparator({ rankBy: ["status"], order: ["asc"] }, ["To Do", "In Progress", "Done"], undefined, undefined);
    const sorted = [...issues].sort(comparator);
    expect(sorted.map((issue) => issue.key)).toEqual(["PROJ-2", "PROJ-3", "PROJ-1"]);
  });

  it("ordena por chave numérica", () => {
    const comparator = buildComparator({ rankBy: ["key"], order: ["asc"] }, undefined, undefined, undefined);
    const sorted = [...issues].sort(comparator);
    expect(sorted.map((issue) => issue.key)).toEqual(["PROJ-1", "PROJ-2", "PROJ-3"]);
  });
});
