# doctor-postgresql — PostgreSQL Doctor backend qualification

> group: filesystem · measures: correctness

The Doctor remaining-backend specification explicitly authorizes internal
crate-level diagnostic entry points and isolated database administration for
fault injection. This scoped qualification uses compiled LayerFS external tests;
it is not a CLI or performance benchmark. No cache or latency claim is made.

`python3 doctor-postgresql/fixtures.py up --state /absolute/private/state` creates
owned PostgreSQL 17 primary/standby containers, private volumes and a network.
The primary uses a fixture self-signed certificate and SCRAM password; Doctor
must reject its certificate under the ordinary trust policy. The generated
private environment file holds connection parameters. `down` removes only the
exact resources saved by this harness after checking their owner label.

Run from the selected LayerFS product checkout after its private worktree build:

```sh
python3 /absolute/benchmark/doctor-postgresql/run.py --state /absolute/private/state --timeout 100 -- python3 tools/worktree.py cargo --resources /absolute/private/resources.json --platform macos --timeout 90 -- test -j 2 -p layerfs-persistence -p layerfs-control --features layerfs-persistence/postgresql,layerfs-control/postgresql --test postgresql_diagnostic --test postgresql_doctor_access --test postgresql_doctor_physical --test postgresql_doctor_cancellation --test doctor_store_postgresql -- --nocapture
```

Build the same targets first with `--no-run`. The loader supplies all fixture
variables, including the explicitly disposable container required by Control's
saved-record test; environment-missing early returns are not qualification.
The five test executables cover actual Store snapshots and authority, logical
corruption, physical checks, provider faults, TLS and cancellation. Daemon and
bundle paths do not participate in this internal backend lane. Keep private
credentials, launcher receipts and logs outside this repository. The published
report pins the actual source, executable hashes, image and PostgreSQL version.

## Past runs

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-08 | `c011512bc1` | PASS: 27 PostgreSQL Doctor backend tests passed against actual owned PostgreSQL 17.11 primary/physical-standby fixtures, including TLS, corruption, privileges and cancellation | [report](../result/2026-11-08/doctor-postgresql/c011512bc129803215e33d0b7f93ac1becccc68a/report.md) |
<!-- runs:end -->
