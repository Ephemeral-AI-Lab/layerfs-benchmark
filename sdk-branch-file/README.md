# sdk-branch-file — saved branch/file API route conformance
> group: history · measures: correctness, compatibility

The CLI-only qualifier drives public Store, branch and file calls on a private
Disposable SQLite or synchronous_commit=off PostgreSQL Store. It checks main
publication/source identity, typed saved heads, pinned history pages, four mixed
Commit/Layer comparisons, attribution-only changes, aligned owners, inherited
blame, revision, missing sides, project/scope refusals and pinned search reads.
No SDK import, private worker call, direct Store SQL or performance claim is made.
Focused product tests separately compare actual JS/Python/CLI responses.

Run one route per command, under an outer timeout of 120 seconds. The driver
has a 110-second ceiling and every child command has at most 20 seconds:

```sh
python3 sdk-branch-file/run.py --cli /absolute/pinned/layerfs \
  --source-dir /absolute/layerfs-checkout --source FULL_SHA \
  --route native --output sdk-branch-file/receipts/UNIQUE_RUN
```

For PostgreSQL, provision a fresh private database with its owning infrastructure
tools and add `--route postgresql --pg-url postgresql://USER@HOST:PORT/DATABASE`.
URLs may not contain passwords. Worker SQLite requires `--route worker --bundle
/absolute/matching/sealed/linux-bundle`; `--image` names an already installed
runtime image. Build the matching CLI and sealed bundle before running.

Each run owns a unique home/input folder. The driver removes/disconnects its
Store through the CLI and stops its worker after PASS. It retains the home and
any stopped infrastructure for exact owner-controlled release; failures preserve
custody without replay. Record actual cleanup in the report. JSON receipts and
per-command outputs remain local/ignored; reports go under `result/`.
