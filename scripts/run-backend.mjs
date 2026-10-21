// Run the backend's virtualenv Python (inside backend/) with the given arguments.
// Works on Windows, macOS and Linux:  node scripts/run-backend.mjs -m pytest -q
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const backend = join(dirname(fileURLToPath(import.meta.url)), "..", "backend");
const python =
  process.platform === "win32"
    ? join(backend, ".venv", "Scripts", "python.exe")
    : join(backend, ".venv", "bin", "python");

if (!existsSync(python)) {
  console.error("Backend virtualenv not found. Run `npm run setup` first.");
  process.exit(1);
}

const child = spawn(python, process.argv.slice(2), { cwd: backend, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 0));
