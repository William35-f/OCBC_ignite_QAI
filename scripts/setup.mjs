// One-time setup: Python virtualenv + backend packages, frontend packages, .env files.
import { execSync } from "node:child_process";
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const win = process.platform === "win32";
const venvPython = join(backend, ".venv", win ? "Scripts/python.exe" : "bin/python");
const run = (cmd, cwd = root) => {
  console.log(`\n> ${cmd}`);
  execSync(cmd, { cwd, stdio: "inherit" });
};
const has = (cmd) => {
  try {
    execSync(`${cmd} --version`, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
};

// 1. Python virtualenv (uses uv if installed, otherwise plain venv + pip)
const useUv = has("uv");
if (!existsSync(venvPython)) {
  run(useUv ? "uv venv --python 3.13 .venv" : `${win ? "python" : "python3"} -m venv .venv`, backend);
}
run(
  useUv ? `uv pip install --python "${venvPython}" -r requirements.txt` : `"${venvPython}" -m pip install -r requirements.txt`,
  backend,
);

// 2. Frontend packages
run("npm install", join(root, "frontend"));

// 3. .env files from the examples (never overwrites)
for (const dir of [backend, join(root, "frontend")]) {
  if (!existsSync(join(dir, ".env"))) copyFileSync(join(dir, ".env.example"), join(dir, ".env"));
}

console.log("\nSetup done. Start everything with:  npm run dev");
