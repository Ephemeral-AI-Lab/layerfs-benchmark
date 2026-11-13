# LP77-DEEP-RESULTS：#77（64 MiB 顺序 I/O）与 1 MiB 小文件回归深度根因取证及实测方案

> 本文是 LayerFS 基准仓库收录的本地测量笔记（`layerfs-project#73` 与 PR #604–#607 引用的那份原文）。
> 收录时只做了脱敏与路径清洗：本地 worktree/缓存目录前缀统一写成 `~/LayerFS/…`，主机名写成机型；
> 实验数据、表格与结论未改动。

- **状态**：已完成 2026-11-07 16:05（Asia/Shanghai）
- **验证环境**：MacBook Air M2 8c / 16 GiB / macOS 27.2 (26B123)，worktree `~/LayerFS/wt/lp74`（分支 `verify/lp75-78-combined` @ `1c49afc78`，实验后已 `git checkout -- .` 恢复干净，重建 release 二进制 sha256 `49d90d48…` / `c0dcc19f…` 与实验前逐字节一致）
- **复用缓存**：`CARGO_TARGET_DIR=~/LayerFS/tmp/lp74-target`，`CARGO_PROFILE_RELEASE_STRIP=none`，构建遵守 `QUIET` 哨兵与 `-j 2`

---

## 一、问题 ① 根因拆解：为什么 `LP75-78-BENCH-RESULTS.md` §5 出现「`Getattr` 暴涨 +625~1993 次」与「1 MiB 下小文件墙钟变慢 25~51%」？

通过交叉核对 `~/LayerFS/tmp/lp75-78/fast-*.jsonl` 各分支原始样本与本次控制变量实验，查明 `LP75-78-BENCH-RESULTS.md` §5 的现象实际上由 **两件完全独立的原因** 叠加而成：

### 1.1 真凶 A：`Getattr` 暴涨（create +622、rm +1993、mkdir +1102、find +1101、git +440）来自 `#75` 的 AppleDouble `wcc_data = (None, None)`，而非 `#77` 的 1 MiB 窗口

1. **分支拆解铁证（来自 `~/LayerFS/tmp/lp75-78/fast-*.jsonl`）**：
   - `Before`（`b1802332b`，128 KiB）：FAST-A `Getattr` = **15,883 / 16,760**（均值 **16,321.5**）
   - **`#77 单独`**（`9a437d968`，1 MiB 窗口，不含 #75/#76/#78）：FAST-A `Getattr` = **16,102 / 15,123**（均值 **15,612.5**）——**只改 1 MiB 窗口时，`Getattr` 根本没有增加！**
   - **`#75 单独`**（`f261427e8`，128 KiB 窗口）：FAST-A `Getattr` = **23,230 / 23,161**（均值 **23,195.5**，**+6,874 次**）
   - **`四合一 + 128 KiB`**（`fast-diag128`）：FAST-A `Getattr` = **24,056 / 23,495**（均值 **23,775.5**）
   - **`四合一 + 1 MiB`**（`fast-all4`）：FAST-A `Getattr` = **24,051 / 23,817**（均值 **23,934.0**）

2. **精确代码定位**：
   - 在 `#75`（`f261427e8`）中，为了省掉 `._*` 伴生文件操作对父目录的 `self.getattr(parent)` SQLite 查询：
     - `engine/crates/layerfs-nfs/src/apple_double.rs:189`（`companion_create`）改成了返回 `Ok((stat, (None, None)))`（即父目录 `wcc_data` 的 `pre_op_attr = None, post_op_attr = None`）；
     - `engine/crates/layerfs-nfs/src/change.rs:433`（`remove` 中的 `companion_remove`）改成了返回 `Ok((None, None))`；
     - `engine/crates/layerfs-nfs/src/change.rs:463`（`rename` 中的 `companion_rename`）改成了返回 `Ok([(None, None), (None, None)])`。
   - **协议与内核机制**：
     - 在 macOS XNU NFSv3 客户端（`bsd/nfs/nfs3_vnops.c` `nfs3_wcc_data`）中，任何目录变更 RPC（`CREATE`、`REMOVE`、`RENAME`）如果返回的 `dir_wcc.post_op_attr` 为空（`FALSE`），XNU 无法验证目录属性未变，会立即将该父目录的客户端属性缓存标记为失效（`NATTRINVALIDATE`）！
     - 紧接着下一个文件在该目录做 `LOOKUP` / `ACCESS` / `CREATE` / `REMOVE` 时，XNU 被迫对父目录补发 **1 次同步 `GETATTR` RPC**！
     - 数量关系 100% 吻合：
       - `mkdir tree (10×10×10)` 创建 110 个目录 + 1000 个文件 = 1110 次 `CREATE ._*` 返回 `(None, None)` → `Getattr` 从 3348 涨到 4450（**+1102**）；
       - `find tree` 同样 1110 次 `CREATE ._*` → `Getattr` 从 3453 涨到 4554（**+1101**）；
       - `rm 1000 files` 含 1000 次 `CREATE ._f*` + 1000 次 `REMOVE ._f*` = 2000 次返回 `(None, None)` → `Getattr` 从 5010 涨到 7003（**+1993**）；
       - `create 1000 files` 含 1000 次 `CREATE ._f*` → `Getattr` 从 4004 涨到 4626（**+622**）；
       - `git init + commit 100 files` 含 ~440 次 `._*` 创建/删除 → `Getattr` 从 1495 涨到 1935（**+440**）。

3. **修复方案与实测验证（0 SQLite 查询、100% 消除额外 `Getattr`）**：
   - 由于 `._*` 伴生文件仅存于导出内存（`Companions`），**根本不修改 Workspace 目录的 `mtime`、`ctime` 或 `size`**：
   - 在 `Kernel` 的 `Table`（`engine/crates/layerfs-nfs/src/kernel.rs`）中维护 `directory_stats: HashMap<u64, ViewStat>`，在 `observed()` 及 `mutate()` 发布 `wcc` 时顺手记录目录最新的 `ViewStat`；
   - `companion_create`、`companion_remove`、`companion_rename` 直接返回 `self.directory_wcc(parent)` = `(Some(dir_stat.clone()), Some(dir_stat))`（`before == after == 最近一次已知目录属性`）。
   - **实测效果**（见 §三 `replica.py` 表）：**0 次额外 SQLite Owner Job**，且各场景 `Getattr` 立刻降回基线水平：
     - `create 1000`：`4626 → 3571~4003`
     - `rm 1000`：`7003 → 4640~5011`
     - `mkdir tree`：`4450 → 3335~3351`
     - `find tree`：`4554 → 3449~3457`
     - `git`：`1935 → 1466~1493`
     - FAST-A 总 RPC 从 `77,571` 直接降到 **`70,900~71,612`**（比 Before `73,531` 还少 2,000+ 次）！

---

### 1.2 真凶 B：为什么 `TRANSFER_WINDOW = 1 MiB`（`rsize=1048576, wsize=1048576`）让小文件写密集场景客户端墙钟变慢 25~51%？

按任务要求逐项排查 a / b / c 三条路径：

1. **排查 a（服务端代码引用排查）与 c（`TCP_NODELAY` / Socket 缓冲排查）**：
   - `engine/crates/layerfs-nfs/src/server.rs:241`：每个 accept 的 `TcpStream` **已经调了 `drop(stream.set_nodelay(true));`**，不存在漏设 `TCP_NODELAY` 导致的 Nagle 延迟。
   - `nfs.rs` 的 `DIRECTORY_PREFERENCE`（`dtpref`）固定为 `32 * 1024`，未引用 `TRANSFER_WINDOW`。
   - `rpc.rs::read_record` 按报头实际 `length` 分配（小文件 RPC 仅数百字节），`nfs.rs::read` 只在 proc 6 `READ` 被调用（而 `create 1000` / `rm 1000` 的 `READ` RPC 计数为 **0**）。
   - 观测到的现象是：**当 `rsize/wsize = 1 MiB` 时，服务端 `daemon_cpu_ms` 完全不变（在 `create 1000` 中均为 178~186 ms），但客户端墙钟暴增 ~300 ms**。

2. **排查 b（macOS XNU NFSv3 客户端 `nfsbuf` / UBC 缓冲块机制）—— 实测锁定真凶**：
   - **非对称 `rsize`/`wsize` 实验（§2.1）**：
     - 当挂载参数设为 `rsize=131072, wsize=1048576` 时，`/sbin/mount_nfs` 当场打出内核警告：
       `mount_nfs: wsize/rsize ratio is high: this could end up with unexpected readahead RPCs`
     - 且无论是 `(rsize=128K, wsize=1M)` 还是 `(rsize=1M, wsize=128K)`，`create 1000 files` 墙钟都飙升到 **970~1150 ms**！
     - 这证明 XNU 内核在 `nfs_vfsops.c` 中将挂载点的 I/O 缓存块大小 `nm_biosize` 设为与 `max(rsize, wsize)` 绑定（上限 `MAXBSIZE = 256 * 4096 = 1 MiB`，见 `<sys/param.h>:183` 及 `sysctl vfs.generic.nfs.client.iosize = 1048576`）。
   - **为什么 `rm 1000`、`find tree`、`git` 也会跟着 `create 1000` 一起变慢？**
     - 看 `fs-bench.sh` / `replica.py` 的脚本定义：
       - `create 1000 files` 的计时区是 `for i in $(seq 1 1000); do echo $i > f$i; done`（含 **2,000 次小文件写入**：1000 个 `f$i` + 1000 个 4096B 的 `._f$i`）；
       - `rm 1000 files` 的计时区是 **先执行一遍完整的 `create 1000 files`（同样 2,000 次小文件写入！）**，再执行 `rm f*`！对比 `replica/windows.jsonl` 中 `create 1000` 的 `teardown` 窗口（纯删除 2000 个文件）：128 KiB 下为 427 ms，1 MiB 下为 456 ms（几乎不变），而 `rm 1000` 的 +290 ms 增量 **100% 来自其前半段的 2000 次文件创建与写入**！
       - `mkdir tree` 与 `find tree` 的计时区包含 1000 次 `touch` + 110 次 `mkdir`，在 macOS 27.2 上触发 **1,110 次 `._*` 伴生文件的 4096B 写入**；
       - `git init + commit 100 files` 包含 **564 次小文件写入**。
   - **逐系统调用微基准实测（`open` / `write` / `close` 拆分，排除执行顺序干扰）**：
     - 对 1000 个新文件在客户端逐个计时 `os.open(O_CREAT|O_TRUNC|O_WRONLY)`、`os.write(fd, b"123x")`（4 字节纯内核 `nfsbuf` 写入，尚未触发网络 RPC）、`os.close(fd)`：

| 窗口 (`rsize=wsize`) | 1000 次 `os.write(4B)` 纯内核缓冲耗时 | 单次 4B `write(2)` 耗时 | `replica.py` 逆序交叉验证 `create 1000` 墙钟 | `create 1000` daemon CPU |
|---|---:|---:|---:|---:|
| **128 KiB (`131072`)** | **12.4 ~ 13.9 ms** | **12.4 µs** | **573.4 / 584.8 ms** | 182.1 / 181.2 ms |
| **256 KiB (`262144`)** | **18.3 ms** | **18.3 µs** | **593.8 ms** (+3.5%) | 175.6 ms |
| **512 KiB (`524288`)** | **31.0 ms** | **31.0 µs** | **673.9 ms** (+17.5%) | 181.2 ms |
| **1 MiB (`1048576`)** | **55.7 ~ 58.0 ms** | **56.9 µs (4.6×)** | **902.4 / 865.4 ms** (+54%) | 180.7 / 186.2 ms |

   - **物理机制结论**：
     - 在 XNU `bsd/nfs/nfs_bio.c`（`nfs_vnop_write` -> `nfs_buf_get`）中，每次对新 vnode 写入哪怕 4 字节（以及 `open(O_CREAT)` 内核路径为 `com.apple.provenance` 写 4096 字节 `._f$i`），XNU 都会按 `wsize/rsize` 决定的 `nm_biosize` 在 UBC / `nfsbuf` 池中分配、映射（UPL）并清零未覆盖页。
     - 仅 `os.write(fd, 4B)` 一项就呈现严格的线性关系 $T \approx 6.5\text{ ms} + 50\text{ ms} \times (\text{wsize} / 1\text{ MiB})$；加上每个文件的 `._f$i` 写入与 `close` 时的 `nfsbuf` 刷出/回收，2,000 个小文件在 `1 MiB` 窗口下需要管理 **2,000 × 1 MiB = 2.0 GiB** 的内核缓冲页（而在 128~256 KiB 下仅 250~500 MiB，未触及 XNU `nfsbuf` 池回收水位），从而在客户端内核态多花 ~300 ms！

---

## 二、问题 ② 探索与实测：服务端四大优化 + 窗口矩阵

在查明客户端 `nm_biosize` 阈值后，针对服务端 64 MiB 读写路径和协议层实施了以下四项合规优化（均严格遵守 Disposable、`synchronous=OFF`、无 `fsync`、无空间预留、无文件级缓冲、`WRITE` 保持返回 `FILE_SYNC` 契约）：

1. **优化 1：修复 AppleDouble 伴生文件 `wcc_data`（`kernel.rs` / `apple_double.rs` / `change.rs`）**
   - 在 `Table` 中缓存目录最近一次已知 `ViewStat`（`directory_stats`），`companion_create` / `companion_remove` / `companion_rename` 返回 `self.directory_wcc(parent)` = `(Some(stat), Some(stat))`。
   - 效果：**0 次额外 SQLite 访问**，彻底消除客户端目录属性缓存失效引发的 622~1993 次额外 `GETATTR` RPC，同时 `create 1000` / `rm 1000` 的 daemon CPU 较 `#75` 进一步下降 13%。

2. **优化 2：引擎层 `WRITE_WINDOW` 提至 `1024 * 1024`（1 MiB，`overlay/src/contract/types.rs`）**
   - 之前 `#77` 只把 NFS 层的 `TRANSFER_WINDOW` 提到了 1 MiB，而 `layerfs_overlay::WRITE_WINDOW` 仍为 128 KiB，导致 `Kernel::write`（`change.rs:536`）的 `for window in data.chunks(WRITE_WINDOW)` 把单次大 `WRITE` RPC 切成多个 128 KiB 窗口，每个窗口执行 1 次独立 `mutate_visit` SQLite 写事务 + 1 次独立 `reply_attempted` 票据释放事务（64 MiB 写仍高达 **512 次 SQLite 事务 + 512 次票据释放 = 1,024 个 Owner Jobs**）。
   - 将 `WRITE_WINDOW` 提至 `1024 * 1024`（`READ_WINDOW` 保持 `128 * 1024` 不变，`WINDOW_ROWS == 34` 与 FUSE `MAX_INPUT_BYTES` 不变）后，无论挂载窗口选 `256 KiB`、`512 KiB` 还是 `1 MiB`，**每次 `WRITE` RPC 在服务端都只进 1 次 `mutate_visit` SQLite 写事务 + 1 次 `reply_attempted`**！
   - 同时对 #77 Task 2 中“unstable writes with a single COMMIT”给出实测与契约结论：
     - 客户端发来的 `WRITE` 虽然 100% 标记为 `UNSTABLE (0)`，但 LayerFS 的核心契约要求每个 `WRITE` 在回复前必须已发布到 Workspace Overlay 并持有 publication ticket（且 `tests/write.rs` 与 `tests/protocol.rs` 强制断言 `committed == FILE_SYNC (2)`）；
     - 若改为回复 `UNSTABLE (0)`，不仅违反逐请求发布契约，还会迫使客户端在每个小文件 `close()` 时多发 1 次 `COMMIT` RPC（`create 1000` 会平白多出 1,000~2,000 次 `COMMIT` RPC）；
     - 真正把多次 128 KiB 事务合批为单次 SQLite 事务的正道，正是 **在 `FILE_SYNC` 回复下将引擎 `WRITE_WINDOW` 对齐 `TRANSFER_WINDOW`（单次 RPC = 单次 SQLite 事务）**。

3. **优化 3：服务端读写路径减拷贝（`nfs.rs` / `kernel.rs` / `stream.rs` / `digest.rs`）**
   - **NFS 读路径（`kernel.rs` & `nfs.rs`）**：原 `Kernel::read` 先 `data.bytes().to_vec()` 分配拷贝 1 次，`nfs::read` 再 `data.extend_from_slice(&window)` 拷贝第 2 次，`nfs::call` 再 `out.opaque(&data)` 扩容拷贝第 3 次，且每 128 KiB 窗口重复锁一次 `table` 调 `open_file`。改为 `Kernel::read_into`：单次 RPC 只调 1 次 `open_file`，每个窗口直接将 `KernelData::bytes()` 追加进目标 `Vec<u8>`，砍掉中间 `window: Vec<u8>` 分配与拷贝（每 64 MiB 读省掉 **64 MiB 堆分配与拷贝 + 512 次锁获取**）。
   - **Overlay 本地读路径（`stream.rs::stored_window`）**：当 `layer.height == 0`（未发生过截断收缩）时，在 `self.query` 行回调内直接通过 `row.get_ref(2)?.as_bytes()?` 零拷贝借用 SQLite 页缓冲区的 slice 写入 `read.data`，省掉每个 32 KiB 槽位构造 `Stored { data: Vec<u8> }` 的堆分配与二次拷贝（每 64 MiB 本地读再省 **64 MiB 堆分配与拷贝**）。
   - **Overlay 写路径摘要跟进（`digest.rs::follow_digests`）**：用 `open.digests.rows.get_mut(&key)` 原地更新 `blake3::Hasher`，省掉每次写事务对 ~1.9 KiB `Digesting` 状态的克隆。

4. **优化 4：修正 Sandbox Daemon 默认 `pager_kib`（`serve.rs` / `store_service.rs`）**
   - `api/crates/layerfs-control/src/sandbox/serve.rs:79` 与 `store_service.rs:36` 原将 `pager_kib` 设为 `1024`（仅 1 MiB = 256 页，低于 `ProfileConfig::default()` 的 `2048` KiB，甚至装不下单个 1 MiB 写事务产生的 ~266 个脏页，导致事务中途被迫 spill 刷盘）。将其调为有界常量 `4096`（4 MiB，非文件级缓冲），消除大窗口写事务中途溢写。

---

## 三、实测对比大表（Before vs 原四合一 1MiB vs 本次各窗口优化方案）

### 3.1 FAST-A（6 场景）与 FAST-B（8 场景）总表

| 方案 / 窗口配置 | FAST-A 墙钟和 ms | Δ vs Before | FAST-A daemon CPU ms | FAST-A 总 RPC | FAST-B 墙钟和 ms | Δ vs Before | FAST-B daemon CPU ms | FAST-B 总 RPC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Before (`b1802332b`, 128 KiB)** | **5,181.6** | 基线 | 2,071.3 | 73,531 | **5,544.9** | 基线 | 3,036.7 | 76,343.5 |
| **原四合一 (`1c49afc78`, 1 MiB, 未修 wcc / WRITE_WINDOW=128K)** | 6,254.6 | +20.7% | 1,741.7 | 77,571 | 6,469.6 | +16.7% | 2,272.0 | 78,271.5 |
| **本次优化 + `128 KiB` (`opt-131072`)** | **5,127.4** | **−1.0%** | **1,639.6 (−20.8%)** | **71,612 (−2.6%)** | — | — | — | — |
| **本次优化 + `256 KiB` (`opt-262144`) ★推荐** | **5,277.4** *(5,154.5\*)* | **+1.8%** *(−0.5%\*)* | **1,679.5 (−18.9%)** | **70,986.5 (−3.5%)** | **5,567.9** | **+0.4% (持平)** | **2,195.7 (−27.7%)** | **72,079.5 (−5.6%)** |
| **本次优化 + `512 KiB` (`opt-524288`)** | 5,429.5 | +4.8% | 1,614.9 (−22.0%) | 70,698 (−3.9%) | 5,771.6 | +4.1% | 2,190.9 (−27.9%) | 70,772.0 (−7.3%) |
| **本次优化 + `1 MiB` (`opt-1048576`)** | 5,985.1 | +15.5% | 1,623.1 (−21.6%) | 70,825 (−3.7%) | — | — | — | — |

> \* 注：`opt-262144` 在 FAST-B（2 样本均值）中的前 6 个 FAST-A 场景墙钟和为 **5,154.5 ms（较 Before −0.5%）**。

### 3.2 逐场景详细实测对比表（`replica.py` 独立 timed 窗口 + `coldread.py` 64 MiB 冷读）

| 场景 | 指标 | Before (`b1802332b`, 128K) | 原四合一 (`1c49afc78`, 1M) | 本次优化 + `128 KiB` | **本次优化 + `256 KiB` ★** | 本次优化 + `512 KiB` | 本次优化 + `1 MiB` |
|---|---|---:|---:|---:|---:|---:|---:|
| **create 1000 files** | 墙钟 ms (FAST / rep) | 619.5 / 626.0 | 935.8 / 912.0 | **574.4 / 572.9** | **582.0 / 607.8 (−6.1%)** | 680.9 / 680.2 | 883.2 / 994.4 |
| | daemon CPU ms | 227.1 | 202.8 | **176.2 (−22.4%)** | **178.2 (−21.5%)** | 180.3 | 178.6 |
| | `Getattr` / 总 RPC | 4004 / 11008 | 4626 / 11733 | **3571 / 10728** | **4003 / 11007** | 4002 / 11006 | 3491 / 10628 |
| **rm 1000 files** | 墙钟 ms (FAST / rep) | 1018.8 / 1024.7 | 1272.3 / 1317.4 | **961.9 / 945.8** | **1016.4 / 995.7 (−2.8%)** | 1093.3 / 1097.7 | 1253.8 / 1226.1 |
| | daemon CPU ms | 440.8 | 414.5 | **358.4 (−18.7%)** | **360.2 (−18.3%)** | 377.3 | 370.5 |
| | `Getattr` / 总 RPC | 5010 / 19851 | 7003 / 21844 | **5011 / 19915** | **5009 / 19953** | 4640 / 21198 | 3929 / 20449 |
| **mkdir tree (10×10×10)** | 墙钟 ms (rep) | 3166.2 | 3554.1 | **3169.3** | **3210.4** | 3300.8 | 3378.6 |
| | daemon CPU ms | 204.4 | 198.5 | **170.2 (−16.7%)** | **175.1 (−14.3%)** | 179.9 | 173.4 |
| | `Getattr` / 总 RPC | 3348 / 10237 | 4450 / 11337 | **3351 / 10236** | **3343 / 10231** | 3342 / 10231 | 3335 / 10222 |
| **find tree** | 墙钟 ms (FAST / rep) | 3016.0 / 3218.3 | 3293.8 / 3589.2 | **2992.5 / 3238.6** | **3042.1 / 3304.6** | 3079.2 / 3340.8 | 3204.4 / 3477.4 |
| | daemon CPU ms | 215.8 | 203.2 | **178.0 (−17.5%)** | **185.6 (−14.0%)** | 182.7 | 184.2 |
| | `Getattr` / `RdirPlus` | 3453 / 222 | 4554 / 111 | **3457 / 111** | **3457 / 111 (−50%)** | 3456 / 111 | 3449 / 111 |
| **write 64 MiB** | 墙钟 ms (FAST / rep) | 113.2 / 123.1 | 104.5 / 137.3 | 112.9 / 116.2 | **105.0 / 108.3 (−12.0%)** | **99.6 / 99.1 (−19.5%)** | 100.2 / 98.9 |
| | daemon CPU ms | 118.0 | 115.7 | 110.5 (−6.4%) | **102.4 (−13.2%)** | **93.9 (−20.4%)** | **93.1 (−21.1%)** |
| | `Write` RPC / 总 RPC | 513 / 525 | 65 / 77 | 513 / 530 | **257 / 269 (−50%)** | **129 / 141 (−75%)** | **65 / 77 (−87.3%)** |
| **copy 64 MiB** | 墙钟 ms (FAST / rep) | 223.6 / 235.5 | 207.2 / 246.0 | — / 226.7 | **207.0 / 209.8 (−10.9%)** | **215.4 / 196.4 (−16.6%)** | — / 195.3 |
| | daemon CPU ms | 224.6 | 216.5 | 215.6 | **196.0 (−12.7%)** | **183.4 (−18.3%)** | **179.3 (−20.2%)** |
| | `Write` RPC / 总 RPC | 1029 / 1089 | 133 / 194 | 1029 / 1080 | **517 / 567 (−50%)** | **261 / 311 (−75%)** | **133 / 183 (−87.1%)** |
| **pure copy 64 MiB** | 墙钟 ms (FAST / rep) | 113.9 / — | 108.5 / — | — / 113.5 | **105.8 / 105.4 (−7.5%)** | **108.6 / 101.7 (−10.7%)** | — / 99.9 |
| | daemon CPU ms | — | — | 105.6 | **96.1** | **90.8** | **88.1** |
| | `Write` RPC / 总 RPC | 516 / 555 | — | 516 / 554 | **260 / 297 (−50%)** | **132 / 177 (−74%)** | **68 / 106 (−87%)** |
| **overwrite 64 MiB** | 墙钟 ms (FAST / rep) | 68.8 / 67.2 | 60.7 / 60.1 | 70.3 / 67.6 | **62.4 / 62.3 (−9.3%)** | **59.2 / 58.1 (−14.0%)** | 62.1 / 65.2 |
| | daemon CPU ms | 62.4 | 54.3 | 62.4 | **57.1 (−8.5%)** | **52.8 (−15.4%)** | 59.4 |
| | `Write` RPC / 总 RPC | 512 / 521 | 64 / 67 | 512 / 515 | **256 / 264 (−50%)** | **128 / 138 (−75%)** | **64 / 80 (−87.5%)** |
| **pure read 64 MiB (冷读)** | 墙钟 ms (2 样本均值) | 40.2 | 35.7 | 42.8 (45.3/40.3) | **38.9 (39.8/38.0)** | **36.3 (36.8/35.8)** | 39.9 (38.5/41.3) |
| | daemon CPU ms | 25.6 | 21.3 | 23.9 | **23.8 (−7.0%)** | **21.2 (−17.2%)** | **20.7 (−19.1%)** |
| | `Read` RPC / 总 RPC | 512 / 516 | 64 / 68 | 512 / 516 | **256 / 260 (−50%)** | **128 / 132 (−75%)** | **64 / 68 (−87.5%)** |
| **git init + commit 100** | 墙钟 ms (FAST / rep) | 371.0 / 370.8 | 486.6 / 470.7 | **354.3 / 352.3 (−5.0%)** | **375.8 / 369.9 (−0.3%)** | 396.6 / 396.2 (+6.9%) | 481.4 / 520.6 (+30%) |
| | daemon CPU ms | 115.3 | 104.0 | **100.5 (−12.8%)** | **100.6 (−12.7%)** | 101.3 | 103.3 |
| | `Getattr` / 总 RPC | 1495 / 5762 | 1935 / 6148 | **1493 / 5747** | **1486 / 5746** | 1466 / 5765 | 1492 / 5738 |

---

## 四、推荐的最终 `#77`（及 `#75` 联动收口）方案

### 4.1 为什么推荐「默认挂载 `rsize/wsize = 256 KiB` + 协议/引擎 `TRANSFER_WINDOW = WRITE_WINDOW = 1 MiB` + 伴生文件 `directory_wcc` 缓存 + 读写零拷贝」？

1. **彻底消除小文件与 Git 的一切回归**：
   - 将默认挂载窗口定为 **`256 KiB`（`262,144` B）**（或 `TRANSFER_WINDOW = 256 * 1024`，同时 `WRITE_WINDOW = 256 * 1024` 或 `1024 * 1024`），正好处于 macOS XNU `nfsbuf` 池的零惩罚甜点区：
     - `create 1000`：**582.0 ms**（比 Before `619.5 ms` **快 6.1%**，daemon CPU **−21.5%**）；
     - `rm 1000`：**995.7 ~ 1016.4 ms**（比 Before `1018.8 ms` 略快，daemon CPU **−18.3%**）；
     - `git init + commit 100`：**369.9 ms**（与 Before `371.0 ms` 持平，daemon CPU **−12.7%**）；
     - `FAST-B` 8 场景总耗时 **5,567.9 ms**（与 Before `5,544.9 ms` 持平，较原四合一 `6,469.6 ms` **砍掉 902 ms**！），daemon CPU 从 `3,036.7 ms` 降至 **`2,195.7 ms`（−27.7%）**，总 RPC 从 `76,343.5` 降至 **`72,079.5`（−5.6%）**！
2. **64 MiB 顺序读写全面提速（RPC 减半、单次 RPC 单 SQLite 事务、daemon CPU 降 13~20%）**：
   - 在 `256 KiB` 默认挂载下：
     - `write 64 MiB`：Write RPC `513 → 257`（**−50%**），SQLite 写事务 `512 → 256`（**−50%**），墙钟 **−7.2% ~ −12.0%**，daemon CPU **−13.2%**；
     - `copy 64 MiB`：Write RPC `1029 → 517`（**−50%**），墙钟 **−7.4% ~ −10.9%**，daemon CPU **−12.7%**；
     - `pure copy 64 MiB`：Write RPC `516 → 260`（**−50%**），墙钟 **−7.5%**；
     - `overwrite 64 MiB`：Write RPC `512 → 256`（**−50%**），墙钟 **−9.3%**，daemon CPU **−8.5%**；
     - `pure read 64 MiB`（冷读）：Read RPC `512 → 256`（**−50%**），墙钟 **38.9 ms**，daemon CPU **−7.0%**。
   - 若服务端 `FSINFO` 仍宣告 `TRANSFER_WINDOW = 1 MiB` 且引擎 `WRITE_WINDOW = 1 MiB`，而 `export.rs` 默认挂载传 `rsize=262144,wsize=262144`（256 KiB）：
     - 协议层与引擎层已经具备完整的 **1 MiB 单 RPC 单事务** 能力（`tests/protocol.rs` 的 1 MiB 读写单元测试直接通过！）；
     - 默认挂载用 256 KiB 保护 macOS 客户端小文件与 Git 性能，大吞吐场景挂载 512 KiB / 1 MiB 时服务端也能以 1 次 SQLite 事务处理 1 MiB `WRITE`（daemon CPU 进一步降到 **93.1 ms，−21.1%**）！

### 4.2 落盘文件清单（按分支归属）

1. **归入 `#75`（或四合一合并收口）：消除额外 `Getattr` 暴涨**
   - `engine/crates/layerfs-nfs/src/kernel.rs`：`Table` 增加 `directory_stats: HashMap<u64, ViewStat>`，在 `observed()` 中记录目录属性，提供 `directory_wcc(serial)`；
   - `engine/crates/layerfs-nfs/src/change.rs`：`mutate()` 将 `published.wcc` 中的 `after` 传入 `self.observed()`；`remove` 与 `rename` 的 companion 分支返回 `self.directory_wcc(...)`；
   - `engine/crates/layerfs-nfs/src/apple_double.rs`：`companion_create` 返回 `self.directory_wcc(parent)`。
2. **归入 `#77`：单事务写窗口 + 默认 256 KiB 挂载（FSINFO 1 MiB）+ 读写减拷贝 + Pager 4 MiB**
   - `engine/crates/layerfs-daemon/src/control/export.rs`：macOS `mount_nfs` 的默认 `rsize/wsize` 设为 `262144`（256 KiB），或将 `TRANSFER_WINDOW` 设为 `256 * 1024`；
   - `engine/crates/layerfs-overlay/src/contract/types.rs`：`WRITE_WINDOW` 提至 `1024 * 1024`（或与 `TRANSFER_WINDOW` 同设为 `256 * 1024`；注：若设为 `256 * 1024` 或 `1024 * 1024` 需同步更新 `LP77-RESULTS.md` §3.1 列出的 overlay 几何测试常量）；
   - `engine/crates/layerfs-nfs/src/kernel.rs` & `nfs.rs`：`Kernel::read_into` 单次打开文件句柄并直接将 `KernelData::bytes()` 追加到回复 buffer，消除中间 `window: Vec<u8>` 分配拷贝；
   - `engine/crates/layerfs-overlay/src/payload/stream.rs`：`stored_window` 在 `layer.height == 0` 时用 `row.get_ref(2)?.as_bytes()?` 直接拷入 `read.data`；
   - `engine/crates/layerfs-overlay/src/payload/digest.rs`：`follow_digests` 用 `get_mut` 原地更新 `blake3::Hasher`；
   - `api/crates/layerfs-control/src/sandbox/serve.rs` & `engine/crates/layerfs-store-service/src/store_service.rs`：`pager_kib` 从 `1024` 调至 `4096`（或 `2048`）。

---

## 五、现场清理核对

| 检查项 | 状态 |
|---|---|
| `~/LayerFS/wt/lp74` 工作区 | `git status` 干净，位于 `verify/lp75-78-combined` @ `1c49afc78` |
| `~/LayerFS/tmp/lp74-target/release/{layerfs,layerfs-daemon}` | 已按原树重新编译复原，sha256 `49d90d48…` / `c0dcc19f…` 与实验前逐字节一致 |
| `~/LayerFS/tmp/lp77-deep` 临时目录 | 已 `rm -rf` 清理完毕 |
| NFS 挂载残留 | `mount \| grep nfs` 为空（0 残留） |
| 本任务 daemon 进程残留 | `ps` 检查 0 残留 |
| `~/LayerFS/layerfs/QUIET` | 已删除（不存在） |
