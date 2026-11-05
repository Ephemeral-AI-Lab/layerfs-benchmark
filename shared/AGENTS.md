# Shared benchmark helpers

Extend the root CLI/cache rules. `src/runner.py` owns lifecycle and custody,
`src/measure.py` owns deadlines/cache eligibility, `src/report.py` publishes one
Markdown file. Suite entrypoints execute runner code with their own cases module;
`CASE_IDS`, `get_case`, and optional `parse_result` define the workload.
No SDK routes, automatic retries, cold-cache self-certification or duplicated
lifecycle implementation. Keep measured execution serial. Runtime tool paths and
capabilities live in machine configuration; canonical workload hashes do not
embed private host paths. Shared infrastructure has one campaign owner.
