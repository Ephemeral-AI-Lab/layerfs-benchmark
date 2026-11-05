# fs-bench-quick — 2026-11-06

> Status: Research; informative and not a product contract.

**96/96 CLI execution checks passed. Case and final runtime cleanup: COMPLETE.**
**All timings are INELIGIBLE diagnostics. Verification: SKIPPED; content correctness: UNVERIFIED.**

LayerFS: `b919f50eaf9cce79671f8501a580279d23cc5f3c` (`layerfs_v2_0_0`, resolved at run start).
Harness code: `5c1a4c58741cc429dc8fa24264bce371adfa43cb`. Date: campaign completion in Asia/Singapore.

Host: macOS arm64 / Darwin 25.4.0, 14 logical CPUs, 36 GiB RAM. Lima and Apple Container:
2 CPUs / 2 GiB each. PostgreSQL 17.11: one dedicated server, 1 CPU / 512 MiB, 48 isolated
databases, synchronous commit off. SQLite: Disposable/WAL/OFF. Provider routes/resources differ.

## Main observations

- Native C02/C04/C05 Exec observations were about 3–4.4 seconds. These are diagnostic observations, not an attributed filesystem-performance finding.
- C01/SQLite Lima spent 2692.5 ms creating its Sandbox versus Docker 289.2 ms. Its shorter Exec/Commit calls therefore did not imply a shorter complete case.
- Empty preparation: 41–323 ms; committed-base preparation: 980–2370 ms; case cleanup: 61–855 ms. Final runtime teardown: 2614 ms.
- Each of 36 guest SQLite transfers was 208 KiB. The 64 MiB bases were built on the destination; ready execution required no transfer.

## Reading the tables

All times are **milliseconds**. Each row is one observation. Docker ratios are machine time
divided by Docker time for the same cell/database/metric: **below 1 means less elapsed time**.

- **Create:** Sandbox creation through the CLI.
- **Exec:** CLI workload call; includes CLI launch/routing overhead. C12 includes its Git commit here.
- **Commit:** the separate LayerFS Commit call.
- **Cleanup:** Sandbox close and Store removal/disconnection; excludes the measured unmount.
- **End-to-end:** Create, mount, Exec, Commit, unmount and Cleanup, plus harness work. It excludes preparation and initial Python startup/configuration checks.

Every LayerFS lifecycle step used the public CLI. Runs were serial in **cell → machine → database**
order: C01–C12; native, Docker, Lima, Apple Container; SQLite then PostgreSQL.

| Cell | Work |
| --- | --- |
| C01 | Create 1,000 files |
| C02 | Create files, then stat each |
| C03 | Create files, then delete them |
| C04 | Create 110 directories and 1,000 files |
| C05 | Create that tree, then find/count |
| C06 | Write 64 MiB |
| C07 | Write 64 MiB, then copy it |
| C08 | Write 64 MiB, then read it |
| C09 | Read committed 64 MiB |
| C10 | Copy committed 64 MiB |
| C11 | Overwrite committed 64 MiB |
| C12 | Git init/add/commit 100 files |

## SQLite

| Cell | Machine | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C01 | native | 922.3 | 767.4 | 132.9 | 61.3 | 1967.7 | 2.52 | 1.68 | 1.98 |
| C01 | docker | 289.2 | 304.0 | 79.1 | 256.6 | 995.9 | 1.00 | 1.00 | 1.00 |
| C01 | lima | 2692.5 | 207.9 | 73.1 | 556.4 | 3614.3 | 0.68 | 0.92 | 3.63 |
| C01 | apple-container | 1075.5 | 209.4 | 67.5 | 855.4 | 2282.5 | 0.69 | 0.85 | 2.29 |
| C02 | native | 37.1 | 4175.7 | 131.3 | 75.6 | 4528.1 | 5.70 | 1.66 | 3.01 |
| C02 | docker | 309.4 | 732.3 | 79.1 | 278.7 | 1503.9 | 1.00 | 1.00 | 1.00 |
| C02 | lima | 737.2 | 571.2 | 72.2 | 144.4 | 1637.9 | 0.78 | 0.91 | 1.09 |
| C02 | apple-container | 64.9 | 564.6 | 71.8 | 75.7 | 891.4 | 0.77 | 0.91 | 0.59 |
| C03 | native | 26.8 | 924.2 | 63.3 | 87.3 | 1230.6 | 2.01 | 3.79 | 1.04 |
| C03 | docker | 291.2 | 460.8 | 16.7 | 283.1 | 1182.8 | 1.00 | 1.00 | 1.00 |
| C03 | lima | 719.6 | 355.0 | 11.0 | 153.2 | 1373.3 | 0.77 | 0.66 | 1.16 |
| C03 | apple-container | 60.0 | 409.5 | 11.7 | 79.4 | 696.0 | 0.89 | 0.70 | 0.59 |
| C04 | native | 39.2 | 3661.6 | 152.9 | 107.6 | 4130.0 | 5.35 | 1.67 | 2.69 |
| C04 | docker | 293.6 | 684.8 | 91.4 | 302.7 | 1533.5 | 1.00 | 1.00 | 1.00 |
| C04 | lima | 739.2 | 598.3 | 82.3 | 188.5 | 1769.7 | 0.87 | 0.90 | 1.15 |
| C04 | apple-container | 49.7 | 593.1 | 82.2 | 99.6 | 1029.3 | 0.87 | 0.90 | 0.67 |
| C05 | native | 25.8 | 2984.0 | 142.7 | 124.1 | 3481.2 | 4.10 | 1.53 | 2.14 |
| C05 | docker | 287.8 | 727.5 | 93.4 | 315.5 | 1624.5 | 1.00 | 1.00 | 1.00 |
| C05 | lima | 734.0 | 525.9 | 76.0 | 184.7 | 1710.5 | 0.72 | 0.81 | 1.05 |
| C05 | apple-container | 72.5 | 509.2 | 79.2 | 103.2 | 967.6 | 0.70 | 0.85 | 0.60 |
| C06 | native | 24.9 | 136.8 | 328.6 | 122.6 | 819.9 | 0.61 | 1.41 | 0.59 |
| C06 | docker | 329.5 | 226.0 | 233.3 | 338.8 | 1383.9 | 1.00 | 1.00 | 1.00 |
| C06 | lima | 717.3 | 105.6 | 223.8 | 200.2 | 1471.5 | 0.47 | 0.96 | 1.06 |
| C06 | apple-container | 57.9 | 162.9 | 243.2 | 118.7 | 831.8 | 0.72 | 1.04 | 0.60 |
| C07 | native | 24.0 | 272.8 | 541.4 | 128.7 | 1211.5 | 0.86 | 1.22 | 0.72 |
| C07 | docker | 309.7 | 315.7 | 443.7 | 327.9 | 1675.6 | 1.00 | 1.00 | 1.00 |
| C07 | lima | 717.2 | 294.9 | 457.4 | 213.7 | 1945.4 | 0.93 | 1.03 | 1.16 |
| C07 | apple-container | 59.5 | 265.4 | 424.1 | 167.4 | 1227.1 | 0.84 | 0.96 | 0.73 |
| C08 | native | 22.9 | 149.4 | 304.1 | 139.4 | 879.5 | 1.05 | 1.36 | 0.69 |
| C08 | docker | 282.4 | 142.2 | 223.0 | 331.9 | 1275.6 | 1.00 | 1.00 | 1.00 |
| C08 | lima | 737.4 | 127.2 | 220.3 | 215.2 | 1582.7 | 0.89 | 0.99 | 1.24 |
| C08 | apple-container | 62.7 | 157.6 | 222.4 | 133.5 | 891.5 | 1.11 | 1.00 | 0.70 |
| C09 | native | 24.1 | 44.3 | 66.8 | 141.3 | 570.4 | 0.56 | 6.77 | 0.59 |
| C09 | docker | 268.4 | 78.7 | 9.9 | 313.4 | 972.0 | 1.00 | 1.00 | 1.00 |
| C09 | lima | 713.6 | 48.1 | 9.0 | 223.4 | 1295.7 | 0.61 | 0.91 | 1.33 |
| C09 | apple-container | 42.8 | 78.4 | 8.7 | 144.5 | 576.8 | 1.00 | 0.88 | 0.59 |
| C10 | native | 24.0 | 163.9 | 122.2 | 163.3 | 799.1 | 0.89 | 2.31 | 0.64 |
| C10 | docker | 267.5 | 184.3 | 52.8 | 386.1 | 1251.8 | 1.00 | 1.00 | 1.00 |
| C10 | lima | 701.3 | 170.9 | 46.6 | 279.6 | 1570.8 | 0.93 | 0.88 | 1.25 |
| C10 | apple-container | 51.9 | 190.7 | 44.7 | 167.1 | 836.1 | 1.03 | 0.85 | 0.67 |
| C11 | native | 25.9 | 117.6 | 189.9 | 192.4 | 922.4 | 0.97 | 1.66 | 0.71 |
| C11 | docker | 277.0 | 120.7 | 114.3 | 379.8 | 1291.3 | 1.00 | 1.00 | 1.00 |
| C11 | lima | 733.0 | 92.8 | 111.2 | 280.1 | 1630.9 | 0.77 | 0.97 | 1.26 |
| C11 | apple-container | 46.1 | 114.0 | 105.5 | 213.1 | 887.3 | 0.94 | 0.92 | 0.69 |
| C12 | native | 22.0 | 325.6 | 90.6 | 192.8 | 1037.4 | 1.70 | 2.04 | 0.78 |
| C12 | docker | 291.6 | 191.5 | 44.5 | 365.2 | 1324.5 | 1.00 | 1.00 | 1.00 |
| C12 | lima | 715.9 | 101.1 | 37.2 | 269.9 | 1543.7 | 0.53 | 0.84 | 1.17 |
| C12 | apple-container | 58.4 | 166.2 | 39.1 | 182.3 | 864.9 | 0.87 | 0.88 | 0.65 |

## PostgreSQL

| Cell | Machine | Create ms | Exec ms | Commit ms | Cleanup ms | End-to-end ms | Exec / Docker | Commit / Docker | End-to-end / Docker |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C01 | native | 69.9 | 548.1 | 222.0 | 80.9 | 1049.7 | 3.22 | 1.32 | 0.82 |
| C01 | docker | 509.4 | 170.0 | 167.8 | 257.4 | 1272.4 | 1.00 | 1.00 | 1.00 |
| C01 | lima | 917.2 | 214.6 | 178.1 | 133.9 | 1626.2 | 1.26 | 1.06 | 1.28 |
| C01 | apple-container | 360.1 | 260.7 | 218.6 | 79.3 | 1162.4 | 1.53 | 1.30 | 0.91 |
| C02 | native | 68.2 | 4435.3 | 228.5 | 89.7 | 4980.1 | 6.92 | 1.19 | 2.77 |
| C02 | docker | 492.8 | 640.6 | 191.6 | 270.8 | 1797.6 | 1.00 | 1.00 | 1.00 |
| C02 | lima | 894.1 | 567.2 | 181.7 | 151.4 | 1997.5 | 0.89 | 0.95 | 1.11 |
| C02 | apple-container | 287.1 | 554.5 | 232.9 | 96.4 | 1431.5 | 0.87 | 1.22 | 0.80 |
| C03 | native | 76.0 | 962.6 | 111.5 | 103.3 | 1447.0 | 2.34 | 3.20 | 0.99 |
| C03 | docker | 497.1 | 411.0 | 34.8 | 291.9 | 1459.3 | 1.00 | 1.00 | 1.00 |
| C03 | lima | 925.1 | 352.5 | 34.0 | 151.3 | 1705.7 | 0.86 | 0.97 | 1.17 |
| C03 | apple-container | 282.7 | 383.7 | 63.1 | 128.0 | 1103.9 | 0.93 | 1.81 | 0.76 |
| C04 | native | 94.9 | 3267.0 | 282.5 | 122.5 | 4001.3 | 5.10 | 1.07 | 2.01 |
| C04 | docker | 516.0 | 641.2 | 265.1 | 286.1 | 1987.3 | 1.00 | 1.00 | 1.00 |
| C04 | lima | 927.0 | 651.0 | 287.6 | 176.8 | 2304.4 | 1.02 | 1.08 | 1.16 |
| C04 | apple-container | 275.2 | 550.0 | 266.3 | 145.1 | 1581.6 | 0.86 | 1.00 | 0.80 |
| C05 | native | 93.9 | 3395.9 | 305.8 | 128.9 | 4193.5 | 4.85 | 1.19 | 2.00 |
| C05 | docker | 533.6 | 700.1 | 257.3 | 298.3 | 2091.8 | 1.00 | 1.00 | 1.00 |
| C05 | lima | 912.8 | 524.0 | 231.1 | 168.8 | 2134.5 | 0.75 | 0.90 | 1.02 |
| C05 | apple-container | 286.8 | 495.3 | 259.2 | 122.8 | 1552.2 | 0.71 | 1.01 | 0.74 |
| C06 | native | 84.3 | 168.3 | 420.1 | 139.4 | 1094.5 | 1.14 | 1.52 | 0.71 |
| C06 | docker | 482.3 | 147.2 | 277.0 | 308.9 | 1552.3 | 1.00 | 1.00 | 1.00 |
| C06 | lima | 906.3 | 110.5 | 282.7 | 200.1 | 1834.2 | 0.75 | 1.02 | 1.18 |
| C06 | apple-container | 290.5 | 168.8 | 320.4 | 136.6 | 1305.5 | 1.15 | 1.16 | 0.84 |
| C07 | native | 74.0 | 292.0 | 667.8 | 148.8 | 1492.4 | 1.01 | 1.32 | 0.71 |
| C07 | docker | 568.7 | 287.8 | 506.9 | 340.2 | 2095.1 | 1.00 | 1.00 | 1.00 |
| C07 | lima | 947.5 | 229.8 | 482.5 | 203.3 | 2224.7 | 0.80 | 0.95 | 1.06 |
| C07 | apple-container | 284.2 | 284.3 | 538.4 | 142.8 | 1678.7 | 0.99 | 1.06 | 0.80 |
| C08 | native | 71.2 | 165.6 | 366.7 | 157.5 | 1088.0 | 1.04 | 1.28 | 0.64 |
| C08 | docker | 545.7 | 158.6 | 286.2 | 316.8 | 1710.3 | 1.00 | 1.00 | 1.00 |
| C08 | lima | 937.9 | 122.2 | 277.9 | 219.1 | 1934.3 | 0.77 | 0.97 | 1.13 |
| C08 | apple-container | 320.6 | 168.8 | 315.7 | 152.2 | 1433.0 | 1.06 | 1.10 | 0.84 |
| C09 | native | 80.5 | 68.4 | 96.3 | 168.9 | 776.4 | 0.60 | 5.77 | 0.58 |
| C09 | docker | 427.1 | 113.7 | 16.7 | 367.7 | 1333.6 | 1.00 | 1.00 | 1.00 |
| C09 | lima | 831.8 | 56.1 | 16.6 | 224.6 | 1557.1 | 0.49 | 0.99 | 1.17 |
| C09 | apple-container | 243.4 | 113.7 | 42.7 | 168.6 | 1056.0 | 1.00 | 2.56 | 0.79 |
| C10 | native | 71.7 | 190.8 | 179.1 | 184.5 | 1031.3 | 0.93 | 2.02 | 0.67 |
| C10 | docker | 408.0 | 204.4 | 88.6 | 362.4 | 1531.3 | 1.00 | 1.00 | 1.00 |
| C10 | lima | 853.4 | 178.6 | 85.7 | 245.0 | 1836.6 | 0.87 | 0.97 | 1.20 |
| C10 | apple-container | 250.8 | 243.9 | 115.6 | 214.6 | 1412.8 | 1.19 | 1.30 | 0.92 |
| C11 | native | 83.7 | 141.6 | 264.7 | 208.0 | 1171.0 | 1.24 | 1.99 | 0.77 |
| C11 | docker | 421.8 | 113.9 | 133.3 | 356.6 | 1513.4 | 1.00 | 1.00 | 1.00 |
| C11 | lima | 892.5 | 91.2 | 136.1 | 260.0 | 1884.1 | 0.80 | 1.02 | 1.24 |
| C11 | apple-container | 205.4 | 171.1 | 190.2 | 210.7 | 1372.9 | 1.50 | 1.43 | 0.91 |
| C12 | native | 91.9 | 347.3 | 191.5 | 207.8 | 1317.6 | 1.61 | 1.23 | 0.73 |
| C12 | docker | 505.7 | 215.2 | 155.6 | 376.9 | 1796.9 | 1.00 | 1.00 | 1.00 |
| C12 | lima | 906.4 | 138.4 | 182.6 | 268.9 | 2002.0 | 0.64 | 1.17 | 1.11 |
| C12 | apple-container | 328.7 | 191.5 | 179.6 | 212.1 | 1530.8 | 0.89 | 1.15 | 0.85 |

## Limits and cleanup

Cold live-Workspace cache state before Commit was not demonstrated. Setup reuse, OS/guest/daemon
caches, PostgreSQL buffers and C07/C08 own-write warmth prevent qualified speed claims. Other owners
also used the host. These Docker ratios remain diagnostic arithmetic, not qualified comparisons.

No independent product proof was selected. Command-only in-Sandbox time, complete remote CPU/memory
and storage peaks, and C01 outer process wall time are unavailable. Earlier harness versions retained
hashes but not source bytes. No performance or release qualification is claimed.

All campaign runtime resources, database data, temporary homes and password files were released;
the Apple Container service was restored to its prior stopped state. A macOS build cache/worktree
held by a pre-existing VM remains protected; pinned artifacts and local evidence are retained.

Harness checks: 57 tests and Ruff formatting/lint passed. No benchmark samples were repeated for
this report. Raw receipts and logs stay local in the ignored working-results directory.
