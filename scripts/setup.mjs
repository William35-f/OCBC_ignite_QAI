// One-time setup on a new computer: Python virtualenv + backend packages (exact
// tested versions from requirements.lock.txt), frontend packages, .env files.
// Needs: Node 18+, and either uv (recommended: it downloads Python by itself)
// or Python 3.12 / 3.13 on the PATH.
import { execSync } from "node:child_process";
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const win = process.platform === "win32";
const venvPython = join(backend, ".venv", win ? "Scripts/python.exe" : "bin/python");
const requirements = existsSync(join(backend, "requirements.lock.txt")) ? "requirements.lock.txt" : "requirements.txt";
const SUPPORTED = ["3.12", "3.13"];

const run = (cmd, cwd = root) => {
  console.log(`\n> ${cmd}`);
  execSync(cmd, { cwd, stdio: "inherit" });
};
const output = (cmd) => {
  try {
    return execSync(cmd, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return null;
  }
};
const fail = (msg) => {
  console.error(`\nSetup stopped: ${msg}`);
  process.exit(1);
};

// 1. Python virtualenv: uv if installed, otherwise a supported system Python
const useUv = output("uv --version") !== null;
if (!existsSync(venvPython)) {
  if (useUv) {
    run("uv venv --python 3.13 .venv", backend); // uv downloads Python 3.13 if needed
  } else {
    // Try the usual names, keep the first one that is Python 3.12 or 3.13
    const candidates = win ? ["py -3.13", "py -3.12", "python"] : ["python3.13", "python3.12", "python3"];
    const python = candidates.find((c) => {
      const v = output(`${c} -c "import sys; print('%d.%d' % sys.version_info[:2])"`);
      return v !== null && SUPPORTED.includes(v);
    });
    if (!python) {
      fail(
        "Python 3.12 or 3.13 was not found.\n" +
          "  Easiest fix: install uv (https://docs.astral.sh/uv/) and run `npm run setup` again,\n" +
          "  or install Python 3.13 from https://www.python.org/downloads/ (tick 'Add python.exe to PATH').",
      );
    }
    run(`${python} -m venv .venv`, backend);
  }
}
run(
  useUv
    ? `uv pip install --python "${venvPython}" -r ${requirements}`
    : `"${venvPython}" -m pip install -r ${requirements}`,
  backend,
);

// 2. Node packages: the root helper (concurrently) and the frontend
run("npm install", root);
run("npm install", join(root, "frontend"));

// 3. .env files from the examples (never overwrites)
for (const dir of [backend, join(root, "frontend")]) {
  if (!existsSync(join(dir, ".env"))) copyFileSync(join(dir, ".env.example"), join(dir, ".env"));
}

console.log("\nSetup done. Start everything with:  npm run dev");
console.log("The first start downloads the embedding model (~90 MB) and can take 1-2 minutes.");
