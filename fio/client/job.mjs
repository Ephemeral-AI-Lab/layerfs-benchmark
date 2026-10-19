// One timed fio job in one arm: a measured sandbox.exec that runs fio alone
// (--output-format=json to a file in the container's /tmp; wall time taken
// inside the Sandbox with date +%s%N around fio, plus the exec's client-side
// time), then an untimed exec that reads back fio's JSON and log. The
// read-back goes to ops/<job>-<arm>.txt and one row to results.jsonl;
// report.py parses both.
//
//   job.mjs JOB ARM
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { append, exec, home, lfs, session } from "../../common/session.mjs";
import { ARMS, armDir, jobArgs, JOBS, OUT, readParams } from "./common.mjs";

const [job, arm] = process.argv.slice(2);
if (!JOBS[job] || !ARMS.includes(arm)) throw new Error("usage: job.mjs JOB ARM");
const params = readParams(readFileSync(join(home, "params.env"), "utf8"));
const { path } = session();
const name = `${job}-${arm}`;
const out = `${OUT}/${arm}`;
const argv = jobArgs(job, armDir(arm, path), params).join(" ");

const run = await exec(path, [
  `mkdir -p ${out} || exit 90`,
  `l=$(cut -d' ' -f1 /proc/loadavg); s=$(date +%s%N); fio ${argv} --output=${out}/${job}.json >${out}/${job}.log 2>&1; rc=$?; e=$(date +%s%N)`,
  `echo "rc=$rc ns=$((e - s)) loadavg=$l"`,
].join("\n"));
const m = /rc=(\d+) ns=(\d+) loadavg=([\d.]+)/.exec(run.stdout);

const back = await exec(path, `cd ${out} || exit 90; echo '=== log'; tail -c 20000 ${job}.log; echo '=== json'; cat ${job}.json`);
mkdirSync(join(home, "ops"), { recursive: true });
writeFileSync(join(home, "ops", `${name}.txt`), back.stdout + (back.stderr ? `=== stderr\n${back.stderr}` : ""));

append("results.jsonl", {
  case: name, job, arm, ...JOBS[job], size: params[`${JOBS[job].file}_size`], runtime: Number(params.runtime), argv,
  rc: m ? Number(m[1]) : null, tool_ns: m ? Number(m[2]) : null, sandbox_loadavg: m ? Number(m[3]) : null,
  exec_ms: run.ms, exec_exit: run.exitCode, exec_stdout: run.stdout.slice(0, 2000), exec_stderr: run.stderr.slice(0, 2000),
  truncated: run.truncated || back.truncated, readback_exit: back.exitCode,
});
await lfs.close();
