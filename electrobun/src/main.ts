/**
 * Electrobun main process for FaireL3s.
 *
 * Spawns the PyInstaller-built Python backend as a child process,
 * waits for it to signal readiness, then loads the Flask UI
 * in a native WKWebView window.
 */
import { BrowserWindow } from "electrobun/bun";
import { spawn, type Subprocess } from "bun";
import { join, dirname } from "path";

const BACKEND_PORT = 5150;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const POLL_INTERVAL_MS = 200;
const STARTUP_TIMEOUT_MS = 15_000;

// ---------------------------------------------------------------------------
// Locate the bundled Python backend executable
// ---------------------------------------------------------------------------
function backendPath(): string {
  // In a built app, resources are alongside the executable.
  // During dev, they live in the project's resources/ directory.
  const base = dirname(Bun.main);
  const candidates = [
    join(base, "..", "resources", "python-backend", "FaireL3s"),   // built app
    join(base, "..", "resources", "python-backend", "FaireL3s", "FaireL3s"), // nested
    join(base, "resources", "python-backend", "FaireL3s"),          // dev
  ];
  for (const p of candidates) {
    if (Bun.file(p).size > 0) return p;
  }
  // Fallback: assume it's in the standard location
  return candidates[0];
}

// ---------------------------------------------------------------------------
// Wait for Flask to be reachable
// ---------------------------------------------------------------------------
async function waitForBackend(timeoutMs: number): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(BACKEND_URL, { signal: AbortSignal.timeout(1000) });
      if (res.ok) return true;
    } catch {
      // not ready yet
    }
    await Bun.sleep(POLL_INTERVAL_MS);
  }
  return false;
}

// ---------------------------------------------------------------------------
// Graceful shutdown
// ---------------------------------------------------------------------------
async function shutdownBackend(proc: Subprocess): Promise<void> {
  // Ask Flask to quit via its /quit endpoint
  try {
    await fetch(`${BACKEND_URL}/quit`, {
      method: "POST",
      signal: AbortSignal.timeout(2000),
    });
  } catch {
    // Flask may already be gone
  }

  // Give it a moment to exit cleanly
  await Bun.sleep(1500);

  // Force-kill if still running
  try {
    proc.kill();
  } catch {
    // already exited
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  const exe = backendPath();
  console.log(`[FaireL3s] Starting backend: ${exe}`);

  const backendProc = spawn({
    cmd: [exe, "--no-browser"],
    stdout: "pipe",
    stderr: "pipe",
  });

  // Log stderr from the backend
  (async () => {
    if (!backendProc.stderr) return;
    const reader = backendProc.stderr.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      process.stderr.write(`[backend] ${decoder.decode(value)}`);
    }
  })();

  // Watch for the ready signal on stdout or fall back to polling
  let ready = false;

  // Race: listen for JSON ready signal vs. polling
  const readyPromise = new Promise<boolean>((resolve) => {
    if (!backendProc.stdout) {
      resolve(false);
      return;
    }
    const reader = backendProc.stdout.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    (async () => {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          try {
            const msg = JSON.parse(line.trim());
            if (msg.ready) {
              resolve(true);
              return;
            }
          } catch {
            // not JSON, ignore
          }
        }
      }
      resolve(false);
    })();
  });

  const pollPromise = waitForBackend(STARTUP_TIMEOUT_MS);

  ready = await Promise.race([readyPromise, pollPromise]);

  if (!ready) {
    console.error("[FaireL3s] Backend failed to start within timeout");
    backendProc.kill();
    process.exit(1);
  }

  console.log("[FaireL3s] Backend ready, opening window");

  // Create the native window
  const win = new BrowserWindow({
    title: "Faire Lower 3rds",
    url: BACKEND_URL,
    frame: {
      width: 620,
      height: 920,
      x: 200,
      y: 100,
    },
  });

  // Handle window close -> shut down backend
  win.on("closed", async () => {
    await shutdownBackend(backendProc);
    process.exit(0);
  });

  // Handle backend crash
  backendProc.exited.then((code) => {
    if (code !== 0 && code !== null) {
      console.error(`[FaireL3s] Backend exited with code ${code}`);
      process.exit(1);
    }
  });
}

main().catch((err) => {
  console.error("[FaireL3s] Fatal error:", err);
  process.exit(1);
});
