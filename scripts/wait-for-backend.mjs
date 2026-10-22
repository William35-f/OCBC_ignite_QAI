// Wait until the backend answers before starting the website, so the browser
// never shows "Cannot reach the Q AI backend" while it is still loading.
// The first start after a reboot can take a minute or two (loading the
// machine-learning libraries and the embedding model).
const url = process.env.QAI_HEALTH_URL || "http://127.0.0.1:8000/api/health";
const timeoutSec = Number(process.env.QAI_WAIT_SECONDS || 300);
const started = Date.now();
let lastNote = 0;

async function up() {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

console.log("Waiting for the Q AI backend to load (first start can take 1-2 minutes)...");
while (!(await up())) {
  const secs = Math.round((Date.now() - started) / 1000);
  if (secs >= timeoutSec) {
    console.error(`The backend did not start within ${timeoutSec}s. Check the [api] lines above for an error.`);
    process.exit(1);
  }
  if (secs - lastNote >= 15) {
    console.log(`  still loading... ${secs}s`);
    lastNote = secs;
  }
  await new Promise((r) => setTimeout(r, 1000));
}
console.log(`Backend ready after ${Math.round((Date.now() - started) / 1000)}s. Starting the website...`);
