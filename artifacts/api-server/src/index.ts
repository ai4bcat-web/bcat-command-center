/**
 * index.ts — BCAT API Server entry point
 * Starts Express on PORT (Replit injects this) or 3000 for local dev.
 */

import app from "./app";

const PORT = parseInt(process.env.PORT ?? "3000", 10);

app.listen(PORT, "0.0.0.0", () => {
  console.log(`[bcat-api] Server running on port ${PORT}`);
  console.log(`[bcat-api] NODE_ENV=${process.env.NODE_ENV ?? "development"}`);
  console.log(`[bcat-api] CSV_DATA_DIR=${process.env.CSV_DATA_DIR ?? process.cwd()}`);
});
