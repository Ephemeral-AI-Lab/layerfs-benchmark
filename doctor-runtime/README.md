# doctor-runtime — real Doctor runtime and S3 qualification
> group: filesystem · measures: correctness

Runs the existing public LayerFS CLI against explicitly owned homes and runtime
resources. This is qualification, with warm setup permitted; it makes no
performance or cold-cache claim. Backend specification:
`docs/architecture/control/management/doctor-remaining-spec.md`, B6.

`src/record.py` records one public CLI invocation, the exact source/binary pin,
requested check outcomes and logical-home hashes before/after Doctor. Doctor
invocations are bounded at100 seconds. Setup commands are recorded separately;
no failed or uncertain operation is automatically replayed.

Provide `--environment` pointing to a private JSON file with absolute `cli`,
`source`, `home`, optional `bundle` and `daemon` paths. Optional `environment`
contains credentials; keep that file and all receipts outside Git. Values are
used as child environment only and redacted from captured output. New Store
setup uses the CLI's explicitly Disposable profile. Provider administration
uses its own tools, with exact ownership recorded in the final report.

```sh
python3 doctor-runtime/src/record.py --environment /private/env.json \
  --output /private/receipts --case native-machine \
  --expect machine.provider=pass --no-mutation -- doctor machine native --timeout 10s
```

Never point mutating setup at an existing user's home. Preserve unknown cleanup
outcomes and exact possibly retained probe keys/versions. R2 qualification is
read-only connection/listing; the requested write test must remain unsupported
before any PUT. Versioned MinIO uses only an isolated bucket and verifies
existing versions/unrelated objects survive the owned-version probe.

<!-- runs:begin -->
| Date | LayerFS commit | Outcome | Report |
| --- | --- | --- | --- |
| 2026-11-08 | `6b9640783c` | PASS — B6 Doctor expectations passed, including the integrated Linux worker and full/quick SQLite routes; an independent native NFS teardown failure remains preserved in issue #136 | [report](../result/2026-11-08/doctor-runtime/6b9640783c4652b7ad662d9610ab8a89670a7d85/report.md) |
<!-- runs:end -->
