// #12's remaining half: the Node SDK's `on_progress` on the same release build.
//
//   LAYERFS_NATIVE=<addon.node> node sdk-progress.mjs <home> <store> <machine> <small-store>
//
// Prints one JSON object on stdout: the events of a push and a pull of the big
// Store, each with the time it arrived and whether the call had already
// settled, and the same for a Store whose handler throws at every event.
import { client } from "layerfs";

const [home, store, machine, small] = process.argv.slice(2);
const lfs = client({ home });

async function collect(argv, call) {
  const events = [];
  let settled = false;
  const started = performance.now();
  let answer = null;
  let error = null;
  try {
    answer = await call((p) => {
      events.push({
        at: Math.round((performance.now() - started) * 1000) / 1000,
        phase: p.phase,
        done: p.done ?? null,
        total: p.total ?? null,
        settled,
      });
    });
  } catch (thrown) {
    error = { name: thrown?.name, code: thrown?.code, message: String(thrown?.message ?? thrown) };
  }
  settled = true;
  return { argv, answer, error, events, seconds: Math.round(performance.now() - started) / 1000 };
}

const out = {};
out.push = await collect(["store.push", store, machine], (onProgress) =>
  lfs.store.push(store, machine, { on_progress: onProgress }));
out.pull = await collect(["store.pull", store], (onProgress) =>
  lfs.store.pull(store, { on_progress: onProgress }));

// a handler that throws at every event: the call must still finish, every event
// must still arrive, and the failures must be warnings, not refusals
const warnings = [];
const onWarning = (warning) => warnings.push(String(warning.message));
process.on("warning", onWarning);
const thrown = [];
let thrownSettled = false;
const thrownStarted = performance.now();
let thrownAnswer = null;
let thrownError = null;
try {
  thrownAnswer = await lfs.store.push(small, machine, {
    on_progress: (p) => {
      thrown.push({ phase: p.phase, settled: thrownSettled });
      throw new Error(`a handler that throws at ${p.phase}`);
    },
  });
} catch (error) {
  thrownError = { code: error?.code, message: String(error?.message ?? error) };
}
thrownSettled = true;
await new Promise((resolve) => setImmediate(resolve));
process.off("warning", onWarning);
const back = await collect(["store.pull", small], (onProgress) =>
  lfs.store.pull(small, { on_progress: onProgress }));
out.throwing = {
  answer: thrownAnswer,
  error: thrownError,
  phases: thrown,
  warnings: warnings.slice(0, 4),
  warning_count: warnings.length,
  seconds: Math.round(performance.now() - thrownStarted) / 1000,
};
out.small_back = back;
process.stdout.write(JSON.stringify(out) + "\n");
