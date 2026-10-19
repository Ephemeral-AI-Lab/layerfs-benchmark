// Untimed layout of one arm's three data files before any timed job: one
// exec runs fio's own layout phase (--create_only=1 with a read job, which
// makes fio write every byte of the file; --fallocate=none, since LayerFS
// refuses fallocate) for seq, rand and sync in 1 MiB writes, then lists the
// files. Its wall time is recorded for information only. One row goes to
// layout.jsonl and fio's output to ops/layout-<arm>.txt.
//
//   layout.mjs ARM
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { append, exec, home, lfs, session } from "../../common/session.mjs";
import { ARMS, armDir, FILES, OUT, readParams } from "./common.mjs";

const [arm] = process.argv.slice(2);
if (!ARMS.includes(arm)) throw new Error("usage: layout.mjs ARM");
const params = readParams(readFileSync(join(home, "params.env"), "utf8"));
const { path } = session();
const dir = armDir(arm, path);
const out = `${OUT}/${arm}`;
const fio = Object.entries(FILES).map(([f, size]) =>
  `fio --name=layout-${f} --filename=${dir}/${f} --size=${params[size]} --rw=read --bs=1M --create_only=1 --fallocate=none --output-format=normal`);
const run = await exec(path, [
  `mkdir -p ${out} || exit 90`,
  `s=$(date +%s%N); rc=0; for c in ${fio.map((c) => `'${c}'`).join(" ")}; do $c >>${out}/layout.log 2>&1 || rc=$?; done; e=$(date +%s%N)`,
  `echo "rc=$rc ns=$((e - s))"`,
  `ls -l ${dir}; du -k ${dir}/*; tail -c 20000 ${out}/layout.log`,
].join("\n"));
const m = /rc=(\d+) ns=(\d+)/.exec(run.stdout);
mkdirSync(join(home, "ops"), { recursive: true });
writeFileSync(join(home, "ops", `layout-${arm}.txt`), run.stdout + (run.stderr ? `=== stderr\n${run.stderr}` : ""));
append("layout.jsonl", { arm, rc: m ? Number(m[1]) : null, ns: m ? Number(m[2]) : null, exec_ms: run.ms, exec_exit: run.exitCode, fio });
await lfs.close();
if (!m || m[1] !== "0") throw new Error(`layout ${arm} failed: ${run.stdout.slice(-2000)} ${run.stderr.slice(-2000)}`);
