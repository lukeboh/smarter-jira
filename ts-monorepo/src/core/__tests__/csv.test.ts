import { describe, it, expect } from "vitest";
import { parseCsv } from "@core/csv";

describe("parseCsv", () => {
  it("parseia CSV com cabeçalho e limpa espaços", () => {
    const csv = "Summary , Assignee\n Task 1 , alice @example.com ";
    const rows = parseCsv(csv);
    expect(rows).toEqual([
      {
        Summary: "Task 1",
        Assignee: "alice @example.com"
      }
    ]);
  });

  it("aplica transform customizado", () => {
    const csv = "a,b\n1,2";
    const rows = parseCsv(csv, {
      transform: (row) => ({ sum: Number(row.a) + Number(row.b) })
    });
    expect(rows).toEqual([{ sum: 3 }]);
  });
});
