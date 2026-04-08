import Papa from "papaparse";

export interface CsvParseOptions<T> {
  header?: boolean;
  transform?: (row: Record<string, string>) => T;
}

export function parseCsv<T = Record<string, string>>(
  content: string,
  options: CsvParseOptions<T> = {}
): T[] {
  const { header = true, transform } = options;
  const result = Papa.parse<Record<string, string>>(content, {
    header,
    skipEmptyLines: true,
    transformHeader: (headerName: string): string => headerName.trim(),
    transform: (value: string): string => value.trim()
  });

  if (result.errors.length) {
    const messages = result.errors.map((err) => err.message).join("; ");
    throw new Error(`Falha ao processar CSV: ${messages}`);
  }

  if (!transform) {
    return result.data as unknown as T[];
  }

  return result.data.map((row) => transform(row));
}
