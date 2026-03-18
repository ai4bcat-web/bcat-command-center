/**
 * csvParser.ts
 * Parses CSV files with support for quoted fields containing commas/dollar signs.
 * Mirrors the pandas CSV ingestion logic from finance_agent.py.
 */

import fs from "fs";

export type CsvRow = Record<string, string>;

/** Parse a raw CSV string into an array of row objects. Handles quoted fields. */
export function parseCsv(content: string): CsvRow[] {
  const lines = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  if (lines.length === 0) return [];

  const headers = splitCsvLine(lines[0]).map((h) =>
    h.trim().toLowerCase().replace(/\s+/g, "_")
  );

  const rows: CsvRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const values = splitCsvLine(line);
    const row: CsvRow = {};
    headers.forEach((h, idx) => {
      row[h] = (values[idx] ?? "").trim();
    });
    rows.push(row);
  }
  return rows;
}

/** Split a single CSV line respecting double-quoted fields. */
function splitCsvLine(line: string): string[] {
  const fields: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      fields.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  fields.push(current);
  return fields;
}

/** Load and parse a CSV file. Returns empty array if the file does not exist. */
export function loadCsv(filePath: string): CsvRow[] {
  if (!fs.existsSync(filePath)) return [];
  const content = fs.readFileSync(filePath, "utf-8");
  return parseCsv(content);
}

/**
 * Parse a currency/numeric string to a float.
 * Strips $, commas, and whitespace. Returns 0 on failure.
 */
export function toFloat(value: string | undefined | null): number {
  if (value == null) return 0;
  const cleaned = String(value).replace(/[$,\s]/g, "");
  const n = parseFloat(cleaned);
  return isNaN(n) ? 0 : n;
}

/**
 * Convert a date string to a "YYYY-MM" month key.
 * Returns "" if the date cannot be parsed.
 */
export function toMonthKey(dateStr: string | undefined | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}
