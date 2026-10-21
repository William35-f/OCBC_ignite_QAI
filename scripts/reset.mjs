// Reset the demo: delete the SQLite database (questions, reviews, golden set,
// fixes, retests, Trust Challenge results, settings). The knowledge base files
// are untouched and every document is back in OCBC AI's retriever on next start.
// Stop `npm run dev` first.
import { existsSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const db = join(dirname(fileURLToPath(import.meta.url)), "..", "backend", "storage", "qai.db");

if (!existsSync(db)) {
  console.log("Nothing to reset: no database yet.");
  process.exit(0);
}
try {
  rmSync(db);
  console.log("Demo reset. Start again with: npm run dev");
  console.log("Tip: press “Clear chat” in the browser to forget the old conversation.");
} catch (e) {
  console.error(`Could not delete ${db}. Stop the backend (npm run dev) first, then try again.\n${e.message}`);
  process.exit(1);
}
