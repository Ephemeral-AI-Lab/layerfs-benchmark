// Shared by the fio clients: each arm's fio folder, the folder that keeps
// fio's own output, the three data files and the job table. The layerfs arm
// runs in the mounted Workspace (session.json's path), the sandbox-disk arm
// in the Sandbox container's own /tmp (overlayfs). fio's JSON and log go to
// the container's /tmp in both arms, so they do not land in the measured
// filesystem.
export const DISK = "/tmp/fio";
export const OUT = "/tmp/fio-out";
export const layerfsDir = (path) => `${path}/fio`;
export const armDir = (arm, path) => (arm === "layerfs" ? layerfsDir(path) : DISK);
export const ARMS = ["layerfs", "sandbox-disk"];

/** Data files, laid out before the timed jobs; each value names its params.env size key. */
export const FILES = { seq: "seq_size", rand: "rand_size", sync: "sync_size" };

/** Options every timed job shares: psync, no fallocate, no cache invalidation, fixed seed. */
export const COMMON = (runtime) => [
  "--ioengine=psync", "--iodepth=1", "--fallocate=none", "--invalidate=0", "--time_based", `--runtime=${runtime}`,
  "--ramp_time=0", "--randrepeat=1", "--randseed=365", "--percentile_list=50:99:99.9", "--group_reporting",
  "--output-format=json",
];

/** The timed jobs in plan order: file, rw, bs, numjobs, direct, sync and any extra fio option. */
export const JOBS = {
  "seq-write": { file: "seq", rw: "write", bs: "1M", numjobs: 1, direct: 0, sync: "end_fsync=1", extra: ["--end_fsync=1"] },
  "seq-read": { file: "seq", rw: "read", bs: "1M", numjobs: 1, direct: 0, sync: "none", extra: [] },
  "rand-write": { file: "rand", rw: "randwrite", bs: "4k", numjobs: 1, direct: 0, sync: "none", extra: [] },
  "rand-read": { file: "rand", rw: "randread", bs: "4k", numjobs: 1, direct: 0, sync: "none", extra: [] },
  "rand-read-4j": { file: "rand", rw: "randread", bs: "4k", numjobs: 4, direct: 0, sync: "none", extra: [] },
  "randrw-70-30": { file: "rand", rw: "randrw", bs: "4k", numjobs: 1, direct: 0, sync: "none", extra: ["--rwmixread=70"] },
  "sync-write": { file: "sync", rw: "write", bs: "4k", numjobs: 1, direct: 0, sync: "fsync=1", extra: ["--fsync=1"] },
  "rand-write-direct": { file: "rand", rw: "randwrite", bs: "4k", numjobs: 1, direct: 1, sync: "none", extra: [] },
  "rand-read-direct": { file: "rand", rw: "randread", bs: "4k", numjobs: 1, direct: 1, sync: "none", extra: [] },
};

/** fio's argv for JOB in DIR: the job's own options, then COMMON. */
export const jobArgs = (job, dir, params) => {
  const j = JOBS[job];
  return [
    `--name=${job}`, `--filename=${dir}/${j.file}`, `--size=${params[FILES[j.file]]}`, `--rw=${j.rw}`,
    `--bs=${j.bs}`, `--numjobs=${j.numjobs}`, `--direct=${j.direct}`, ...j.extra, ...COMMON(params.runtime),
  ];
};

/** RUN/params.env as an object (runtime and the three file sizes). */
export const readParams = (text) => Object.fromEntries(text.split("\n").filter(Boolean).map((l) => l.split("=", 2)));
