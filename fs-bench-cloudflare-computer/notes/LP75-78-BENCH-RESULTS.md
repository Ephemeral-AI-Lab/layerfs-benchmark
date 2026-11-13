# LP75-78-BENCH：#75–#78 四合一 FAST 子集实测 + #78 新增提交只读审阅

> 本文是 LayerFS 基准仓库收录的本地测量笔记（`layerfs-project#73` 与 PR #604–#607 引用的那份原文）。
> 收录时只做了脱敏与路径清洗：本地 worktree/缓存目录前缀统一写成 `~/LayerFS/…`，主机名写成机型；
> 实验数据、表格与结论未改动。

- **状态**：已完成 2026-11-07 15:05（Asia/Shanghai）；**§12 是 2026-11-07 17:05 的 FINALIZE 复测（256 KiB 窗口定案 + 最终四合一 `85a0865cd`），§0–§11 保持原样**
- **机器**：本机 MacBook Air M2 8c / 16 GiB / macOS 27.2 (26B123)，本任务期间没有别的编译或测试在跑（load 2.4–3.2，低于 #74 采样时的 4.1–6.1）
- **Before pin**：`upstream/layerfs_v2_0_0` @ `b1802332b`（release CLI/daemon sha256 `3d640147…ff57407` / `f54b1d41…7cb03c9`，**与 #74 实测用的二进制逐字节相同**，本次在同一 target 目录重建后复现）
- **After pin**：本地组合分支 `verify/lp75-78-combined` @ `1c49afc78`（= `feat/lp78-nfs-git` `d355a4ece` + `merge feat/lp76-nfs-readdir` `cc7024c7b` + `merge feat/lp77-nfs-seq-io`；release sha256 `49d90d48…4e3c5be` / `c0dcc19f…f92bae2`）
- **审阅对象**：`git diff f261427e8..d355a4ece`（#78 的单个新增提交，父 `f261427e8` = #75）
- **没有做的事**：不 push、不开 PR、不发 GitHub 评论；没有改产品代码（唯一一次改代码是 §7 的诊断实验，已 `git checkout` 复原并逐字节核对）

---

## 0. 结论摘要（先看这段）

| 项 | 结果 |
|---|---|
| #78 审阅 | **阻塞 0 / 建议 3**（无泄漏、无阻塞；3 条都是边界/注释级，详见 §1） |
| 四合一 `cargo test -p layerfs-nfs` | **27 passed / 0 failed**（含 60.09 s 的 helper_deadline 有界等待用例；无用例超 120 s） |
| 四合一 release 构建 | 成功，`--locked -j 2`，增量 39.5 s；`CARGO_PROFILE_RELEASE_STRIP=none` |
| FAST-A（6 行）总耗时 | Before **5,181.6 ms** → After **6,254.6 ms**（**+20.7%**） |
| FAST-A 总 RPC | Before **73,531** → After **77,571**（**+5.5%**） |
| FAST-B（8 行）总耗时 | Before **5,544.9 ms** → After **6,469.6 ms**（**+16.7%**） |
| FAST-B 总 RPC | Before **76,343.5** → After **78,271.5**（**+2.5%**） |
| daemon CPU | FAST-A 2,071 → 1,742 ms（**−15.9%**）；FAST-B 3,037 → 2,272 ms（**−25.2%**） |
| 64 MiB 顺序 I/O | **全面变好**：Write RPC 513→65（−87%）、冷读 Read RPC 512→64（−87.5%），冷读墙钟 −11.2% |
| 元数据场景 | **全面变差**：create +51%、rm +25%、find +9%、git +23%；`mkdir tree` +12% |
| 归因结论 | **墙钟回归全部来自 #77 的 1 MiB `rsize/wsize`（`TRANSFER_WINDOW`）**；同 #77 代码但把 FSINFO/挂载窗口退回 128 KiB 后，FAST-A 回到 5,364.3 ms、create 599.9 ms（§7 诊断实测） |
| 建议 | 四合一**不要原样合入**：要么 #77 的 1 MiB 传输窗口改为按场景/可配置（或先降到 256–512 KiB 复测），要么接受「大文件变快、小文件与 git 变慢」的明确取舍并由维护者决定 |

> 一句话：**#75、#76、#78 单独和组合都没有让墙钟变差（RPC 甚至 +12%，但墙钟持平）；#77 让 64 MiB 顺序 I/O 的 RPC 掉 8 倍、单场景墙钟 −5~12%，代价是元数据/小文件/`git` 场景墙钟 +9~51%。**

---

## 1. #78 新增提交审阅（`f261427e8..d355a4ece`，阻塞 0 / 建议 3）

### 1.1 变更范围（8 文件，+361/−119，其中测试 +109）

| 文件 | 改动 |
|---|---|
| `engine/crates/layerfs-nfs/src/change.rs` | `prepare_replace`/`Retire`（RENAME 目标在发布事务里回收）、`rename` 去掉前后 `existing()`、`renamed_taken`（用发布事务带回的 `moved` 定位被移动节点）、`commit()` 走 `held_stat` |
| `engine/crates/layerfs-nfs/src/changing.rs` | RENAME 的 `wcc_data` 两半都来自发布事务；COMMIT 改调 `kernel.commit()`，删掉 `attributes()` 辅助 |
| `engine/crates/layerfs-nfs/src/kernel.rs` | `Held.size` → `Held.stat: ViewStat`；`observed_size` → `observed`；新增 `held_stat`；`file_taken` 收 `&ViewStat` |
| `engine/crates/layerfs-mount-ports/src/operations/mutation.rs` | `Published` 透传 `moved` |
| `engine/crates/layerfs-workspace/src/operations/kernel_mutation.rs` | `KernelMutationOutcome.moved` |
| `engine/crates/layerfs-workspace/src/operations/kernel_visit.rs` | RENAME 分支从 `changes.directory_entries` 的 `Binding::Bound { serial }` 取被移动节点，交给 `before_stat` 生成 `moved` |
| `docs/architecture/engine/kernel-routes/nfs.md` | 契约表 3 行同步（`wcc_data` 全过程同一事务、RENAME 不前置查询、COMMIT 0 owner job） |
| `tests/write.rs` | 新增 1 例：`rename_over_an_existing_target_and_commit_avoid_redundant_owner_jobs_and_orphans`（+109 行） |

### 1.2 契约核对（逐条通过）

1. **发布票据**：仍只有 `tickets.0.push(mutation)` 一个出口，回复失败也保留；`tests/write.rs::tickets_are_released_only_after_the_reply` 在四合一树上通过。0 阻塞。
2. **一次尝试、无重试**：`rename`/`remove`/`rmdir` 都是单次 `mutate`；失败即 `Err`，没有 busy 处理或重放。0 阻塞。
3. **Disposable / 无 `fsync`**：本提交没有触碰 profile、`synchronous`、`sync_data`。0 阻塞。
4. **假 orphan**：`prepare_replace` 把被替换目标的隐式描述符交给发布事务，`changes.detached`（`job.rs:159` 用 `nlink == 0` 精确定位）在 `detach_orphan` 之前把核引用归零；测试断言 `resources.open.orphan_files == 0` 且被替换 inode 的句柄 STALE、`server.held() == (files 1, lookups 1)`。0 阻塞。
5. **`wcc_data` 形状**：RENAME 失败时两个 `wcc` 都是 `(None, None)`（RFC 1813 允许 pre/post 均缺省）；同目录成功时 `from_wcc == to_wcc`，测试断言 `before` 相同、`after.fileid` 都等于父目录。0 阻塞。
6. **`moved` 的取值来源**：`changes.detached` 由 `job.rs` 用 `find(nlink == 0)` 选出，所以 `kernel_visit.rs:443` 的 `changes.inodes.last()` 在“同目录 1 个目录 + 被替换节点”“跨目录 2 个目录 + 被替换节点”两种形状下都恰好是被替换节点（`rename.rs:147` 把 `dereferenced(old)` 追加在最后）。0 阻塞。
7. **泄漏**：`Held` 从 `{handle,size,tick,writable}` 变成 `{handle,stat,tick,writable}`，句柄上限 `FILES_HELD.min(lookups_held/2)`（≤1024）→ 每个句柄多存一个 `ViewStat`，量级 ~100 KiB，随 `close_file`/`unlinked` 释放；`Retire` 是 `Copy`。0 阻塞。
8. **产品码卫生**：`git diff` 里没有新增 `unwrap/expect/panic!/todo!/eprintln!/dbg!`（只有测试代码用 `unwrap`），没有新增 `#[allow]`/`#[ignore]`。0 阻塞。
9. **文档**：`nfs.md` 三行契约与实现一致（含“被替换目标在其重命名事务内回收，因此不会成为导出自身引用的 orphan”）。0 阻塞。

### 1.3 建议（3 条，均不阻塞）

1. **`Retire::open()` 的判定比实际需要宽**：`open()` 只看“`by_name` 里有没有这个名字”，而 `prepare_kernel_mutation` 用的是发布事务算出的 `changes.detached`（真正的 `nlink == 0` 节点）。两者只有在本导出的 `by_name` 与树当前绑定不一致（另一连接并发替换同名项）时才会指向不同 serial。此时 `kernel_file_row(mount, serial, handle)` 的配对检查会挡住“关错描述符”，但 job 内仍会 `drop_kernel_lookup`(detached)，随后 `finish_unlink` 走 `unlinked()` 再 `forget` 一次（引擎已无行 → Stale，被 `drop(...)` 忽略）。结论是只多一次无副作用 RPC；建议把 `Retire` 收紧成“只有确认指向同一 serial 才让 job 内回收”，或在 `prepare_kernel_mutation` 里以 `retire.serial == changes.detached` 为前提。
2. **`held_stat` 的注释强于实现**：`live` 用的是本导出自己的 `table.names`/`pinned`，只能发现“本导出删掉了最后一条名字”，发现不了“另一连接删了这个名字”。后者仍会返回上一次观测到的属性并回成功（COMMIT 的 `post_op_attr` 可选、`actimeo=60` 内属性本就可能旧，可接受），但注释写的“answers stale”在这种情形不成立。建议改注释或补一条测试说明该边界。
3. **`JobOutcome::Unchanged` 分支的 `wcc[1]` 是 `(None, None)`**：rename 成两名字同 inode（硬链接）时 `wcc[0]` 复用了同一个 stat，`wcc[1]` 缺省。RFC 允许，但对客户端等于“to 目录属性不可用”，与文档“one directory answers both halves”的措辞不完全一致。建议 Unchanged 分支也复用 `wcc[0]`。

### 1.4 本提交的正向证据（实测）

- 新增测试断言 **COMMIT 0 owner job**、**RENAME 1 个 mutate_visit + 0 observe/close_file/forget**、被替换 inode 句柄 STALE、`orphan_files == 0`、跨目录 RENAME 同样 1 个 job。
- 四合一树上 `layerfs-nfs` 全绿（27 passed）。
- 实测 `git init + commit 100 files`：RENAME 19 次、COMMIT 全程 0（客户端只发 `fsync`→ 现在 0 owner job），分过程为 §5 的 git 行。

---

## 2. 构建与测试（四合一）

```
worktree  ~/LayerFS/wt/lp74
分支      verify/lp75-78-combined  (基于 d355a4ece，依次 merge --no-edit feat/lp76-nfs-readdir feat/lp77-nfs-seq-io；零冲突)
HEAD      1c49afc78  (merge 'feat/lp77-nfs-seq-io')
CARGO_TARGET_DIR=~/LayerFS/tmp/lp74-target   CARGO_PROFILE_RELEASE_STRIP=none
构建      cargo +1.85.1 build --release --locked -j 2 --bin layerfs --bin layerfs-daemon
          → Finished in 39.51 s（增量）；唯一告警是既有的 layerfs-persistence `unused import ORDINAL_END`
测试      cargo +1.85.1 test --locked -j 2 -p layerfs-nfs
          → 27 passed / 0 failed（1 个用例 60.09 s 为有界等待，未超 120 s 上限）
```

`layerfs` sha256 `49d90d483dee24c64dc7789b84263dd7e844b5e471c19c8d969feee104e3c5be`
`layerfs-daemon` sha256 `c0dcc19f80cd4cb7be09a13b8a0c2e9db98ed43ae1d277e8abfd2a266f92bae2`
（`~/LayerFS/tmp/lp75-78/state/sha-after.txt`）

`QUIET` 哨兵在构建开始前 `touch`、构建结束立即删除；收尾时已确认不存在（§9）。

---

## 3. 口径（与 #74 完全一致）

| 项 | 值 |
|---|---|
| 场景驱动 | `~/LayerFS/tmp/lp74-run/fast.py`（一次冻结脚本调用打一个子集，记录脚本自报 `date +%s%N` 行、整次调用墙钟、`nfsstat -c` NFSv3 过程差分、daemon 进程 CPU） |
| 分场景窗口 | `~/LayerFS/tmp/lp74-run/replica.py`（逐场景 pre/timed/teardown 三窗口，只取 timed） |
| 冷读 | 本次新增 `~/LayerFS/tmp/lp75-78/coldread.py`，方法照抄 #74 §18（写 64 MiB → `workspace commit` → `unmount`+`mount` → `cat`） |
| bash | `~/LayerFS/tools/fs-bench/bin/bash` = GNU bash 5.2.37(1) |
| 冻结脚本 | `fs-bench.sh` sha256 `0e2004339a9269b88c2de451d56575957477bde16b96a10cf1837519e37230ef`（与 #74 pin 相同） |
| RPC | `/usr/bin/nfsstat -c` 前后快照差分（每次调用从 0 起算的 export 计数器不是公开接口，仍用客户端差分） |
| daemon CPU | `proc_pid_rusage(RUSAGE_INFO_V4)` 的 user+sys，mach 时间基换算纳秒 |
| 每场景前置 | 每个组合都用**全新私有 home + 全新 Store + 全新挂载**（`store create` → `project init` 同一 seed 4 文件 → `branch fork` → `sandbox create` → `workspace mount`），与 #74 的 PREP §4 顺序一致 |
| 样本 | 每个配置每个子集 2–4 次独立调用（#74 是 1 次）；表里给均值，噪声带 ≥10% 的另行标注 |
| host 对照 | 同一 `~/LayerFS/tmp/lp74-run/apfs/work` APFS 目录，用于抵消机器漂移 |

**可复现性检查（重要）**：本次用 `b1802332b` 重建的 Before 二进制与 #74 采样时**逐字节相同**（sha256 一致），在同一台机器上重测得到 FAST-A 5,181.6 ms / 73,531 RPC（#74 记录 5,307.4 / 74,756）、FAST-B 5,544.9 ms / 76,343 RPC（#74 记录 5,653.9 / 76,130）、host 2,189.5 ms（#74 记录 2,218.1）。偏差 −1.6%~−2.4%，说明**本次 After 与 #74 的 Before 可以直接比较**。

---

## 4. Before vs After 总表

### 4.1 FAST-A（6 行：create / rm / find / write / overwrite / git）

| arm | 样本 | 脚本自报和 ms | host 和 ms | LayerFS 净增 ms | daemon CPU ms | NFSv3 RPC |
|---|---:|---:|---:|---:|---:|---:|
| Before `b1802332b` | 2 | **5,181.6** | 2,189.5 | **2,992.1** | **2,071.3** | **73,531** |
| After `verify/lp75-78-combined` | 4 | **6,254.6** | 2,262.1 (n=1) | **3,992.5** | **1,741.7** | **77,571** |
| 变化 | — | **+20.7%** | +3.3% | **+33.4%** | **−15.9%** | **+5.5%** |

### 4.2 FAST-B（8 行：FAST-A + copy 64 MiB + pure copy 64 MiB）

| arm | 样本 | 脚本自报和 ms | host 和 ms | LayerFS 净增 ms | daemon CPU ms | NFSv3 RPC |
|---|---:|---:|---:|---:|---:|---:|
| Before `b1802332b` | 2 | **5,544.9** | 2,454.4 | **3,090.5** | **3,036.7** | **76,343.5** |
| After `verify/lp75-78-combined` | 2 | **6,469.6** | 2,331.6 | **4,138.0** | **2,272.0** | **78,271.5** |
| 变化 | — | **+16.7%** | −5.0% | **+33.9%** | **−25.2%** | **+2.5%** |

> host 两臂相差 3~5%（同一目录重复跑，噪声带），LayerFS 净增的 +33% 远大于它，不受 host 漂移解释。

---

## 5. 逐场景对比大表（Before → After）

墙钟 = `fast.py`（脚本自报 `mean`）均值；daemon CPU 与 RPC = `replica.py` timed 窗口单样本。百分比相对 Before。

| 场景 | 墙钟 Before ms | 墙钟 After ms | Δ墙钟 | daemon CPU B→A ms | 总 RPC B→A | 关键过程 B→A |
|---|---:|---:|---:|---|---|---|
| create 1000 files | 619.5 | **935.8** | **+51.1%** | 227.1 → 202.8 (−10.7%) | 11,008 → 11,733 (**+6.6%**) | Create 2000→2000；Write 2000→2000；Lookup 2001→2104；**Getattr 4004→4626 (+15.5%)**；Setattr 1000→1000 |
| rm 1000 files | 1,018.8 | **1,272.3** | **+24.9%** | 440.8 → 414.5 (−6.0%) | 19,851 → 21,844 (**+10.0%**) | Remove 2000→2000；Lookup 6835→6836；**Getattr 5010→7003 (+39.8%)**；RdirPlus 2→1 |
| mkdir tree (10×10×10) | 3,166.2 | **3,554.1** | **+12.3%** | 204.4 → 198.5 | 10,237 → 11,337 (**+10.7%**) | Create 2110→2110；Mkdir 110→110；Lookup 2224→2223；**Getattr 3348→4450 (+32.9%)** |
| find tree | 3,016.0 | **3,293.8** | **+9.2%** | 215.8 → 203.2 (−5.8%) | 10,560 → 11,551 (**+9.4%**) | **RdirPlus 222→111 (−50%)**；Lookup 2222→2222；**Getattr 3453→4554 (+31.9%)** |
| write 64 MiB | 113.2 | **104.5** | **−7.7%** | 118.0 → 115.7 | 525 → **77 (−85.3%)** | **Write 513→65 (−87.3%)**；每调用 131,072 B → 1,048,576 B |
| copy 64 MiB | 223.6 | **207.2** | **−7.3%** | 224.6 → 216.5 | 1,089 → **194 (−82.2%)** | **Write 1029→133**；Setattr 18→18；Getattr 17→19 |
| pure copy 64 MiB | 113.9 | **108.5** | **−4.7%** | 未测* | 未测* | 未测（replica 本轮只跑了 FAST-B 的 8 行，不含 pure copy） |
| overwrite 64 MiB | 68.8 | **60.7** | **−11.8%** | 62.4 → 54.3 | 521 → **67 (−87.1%)** | **Write 512→64**；Lookup 4→0 |
| git init + commit 100 files | 371.0 | **486.6** | **+31.2%** | 115.3 → 104.0 (−9.8%) | 5,762 → 6,148 (**+6.7%**) | Rename 19→19；**Getattr 1495→1935 (+29.4%)**；Lookup 1789→1745；RdirPlus 8→5；Remove 218→218 |

\* `pure copy` 本轮只测了墙钟：daemon CPU / RPC 留空，不从别的轮次借数。

**两处口径不一致（照实记录）**：`write 64 MiB` 与 `copy 64 MiB` 的墙钟在 `fast.py`（整次调用：−7.7% / −7.3%）与 `replica.py`（逐场景窗口：+11.5% / +4.5%）上方向不同。两者都是单样本、跨会话，差异都在 15% 以内；daemon CPU 两臂持平（118.0→115.7、224.6→216.5），RPC 掉 82~87%。本节墙钟列以 `fast.py` 为准，`replica.py` 的 64 MiB 墙钟不单独作结论。

**git 专项补测（只跑 git 场景、每个 3 样本、每次全新 Store+挂载）**

| arm | 样本 | 脚本自报 ms | daemon CPU ms | RPC |
|---|---:|---|---:|---:|
| Before | 3 | 380.8 / 366.9 / 358.5（均值 368.7） | 193.4 | 8,890 |
| After | 3 | 498.7 / 431.5 / 432.6（均值 454.3） | 161.6 | 9,267 |
| 变化 | — | **+23.2%** | **−16.5%** | +4.2% |

### 5.1 读表要点

1. **#75/#76/#78 消除的 daemon 工作是真的**：元数据场景 daemon CPU 全部下降（create −11%、rm −6%、find −6%、git −10%，FAST-B 合计 −25%），`RdirPlus` 精确减半（222→111），`Remove`/`Create`/`Write`/`Setattr`/`Rename` 计数一个不差——说明“服务端少做活”的目标达到了。
2. **但客户端 RPC 反而多 6~10%（Getattr 为主）**：create +625、rm +1993、mkdir +1102、find +1101、git +440。这批新增 GETATTR 不是服务端行为，而是客户端在重构后的回复（`wcc_data` 现在与变更同一事务、CREATE 带隐式描述符）下多做的属性刷新；墙钟上它被服务端省下的部分抵消，所以 #75/#78 组合的 FAST-A 反而持平（§7）。
3. **#77 的 1 MiB 窗口是唯一的墙钟回归源**：§7 的逐分支bisect 与 §7.2 的诊断实验都把回归锁定在“挂载/FSINFO 声明 1 MiB”这一件事上，而不是 #77 的 daemon 侧代码（`write_vectored`、读窗口拼装、`appended` 零 shape 读）。

---

## 6. 64 MiB 冷读与 `rsize/wsize`（#77 主目标）

### 6.1 `nfsstat -m` 协商结果

| arm | Original mount options | **Current mount parameters** |
|---|---|---|
| Before | `…rsize=1048576,wsize=1048576…` | **`rsize=131072,wsize=131072`**（被服务端 FSINFO 夹回 128 KiB，#74 §8 现象） |
| After | `…rsize=1048576,wsize=1048576…` | **`rsize=1048576,wsize=1048576`**（`readahead=16,dsize=32768,rdirplus`） |

→ **1 MiB 协商已生效**（`engine/crates/layerfs-nfs/src/nfs.rs` 的 `TRANSFER_WINDOW` 与 `export.rs` 的挂载参数同源）。

### 6.2 冷读（写 64 MiB → commit → unmount+remount → `cat`）

| 窗口 | 墙钟 ms | daemon CPU ms | NFSv3 RPC | Read | Write |
|---|---:|---:|---:|---:|---:|
| Before：write 64 MiB（冷目标） | 113.9 | 105.2 | 526 | 0 | **513** |
| Before：**pure read 64 MiB（冷）** | 40.2 | 25.6 | 516 | **512** | 0 |
| Before：pure read 64 MiB（随即热读） | 12.8 | 0.0 | 0 | 0 | 0 |
| After：write 64 MiB（冷目标） | 97.5 | 81.1 | 78 | 0 | **65** |
| After：**pure read 64 MiB（冷）** | 35.7 | 21.3 | 68 | **64** | 0 |
| After：pure read 64 MiB（随即热读） | 11.7 | 0.0 | 0 | 0 | 0 |

- **Read RPC 512 → 64（−87.5%）**、**Write RPC 513 → 65（−87.3%）**，与“1 MiB 窗口 = 64 次”精确对应；每次调用字节数 131,072 → 1,048,576。
- 冷读墙钟只 −11.2%（40.2 → 35.7 ms）、daemon CPU −16.8%（25.6 → 21.3 ms）：#74 §18 已判定冷读墙钟的一半以上在客户端（readahead/vnode 页入），RPC 减少只吃掉了往返那一段，**这与 #74 的预期一致**。
- 冷读绝对值比 #74 记录的 52.0/61.4/59.6 ms 低：那是 #74 采样窗口（load 4–6）与本窗口（load 2.5）的机器差；同一窗口内 Before 40.2 vs After 35.7 才是可比对。
- 热读两臂都是 **0 RPC**（客户端页缓存），复现 #74 的“假零”现象。

---

## 7. 归因：逐分支 bisect（都在同一 target、同一口径、每次全新 Store+挂载，n=2）

### 7.1 FAST-A 逐组合（6 行脚本自报均值）

| 组合 | 合计 ms | create | rm | find | write 64 MiB | overwrite | git | daemon CPU ms | RPC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Before `b1802332b` | **5,181.6** | 621.1 | 995.0 | 3,012.4 | 114.2 | 69.8 | 369.1 | 2,071.2 | 73,531 |
| #75 `f261427e8` | 5,291.9 | 589.2 | 1,021.8 | 3,113.4 | 118.6 | 73.4 | 375.5 | 1,808.5 | 81,894 |
| #75+#78 `d355a4ece` | 5,246.7 | 602.5 | 1,020.1 | 3,084.9 | 111.9 | 67.0 | **360.3** | 1,781.0 | 81,785 |
| #75+#76+#78 `cc7024c7b` | 5,227.8 | 578.3 | 1,019.0 | 3,088.6 | 112.4 | 68.2 | 361.1 | 1,722.0 | 78,039 |
| **#77 单独** `9a437d968` | **6,194.4** | **951.0** | **1,314.2** | 3,264.8 | 102.1 | 61.5 | **500.8** | 2,057.8 | 73,188 |
| **四合一** `1c49afc78` | **6,197.0** | **880.8** | **1,312.3** | 3,323.1 | 104.4 | 60.8 | **515.5** | 1,723.8 | 77,977 |

> 本节每档 n=2（各自全新 Store + 挂载）。§4 的四合一行用 n=4（多算第一次会话的 2 个样本），所以两处合计/RPC 略有差别（6,254.6 / 77,571 vs 6,197.0 / 77,977），结论一致。
| 四合一 + `TRANSFER_WINDOW=128 KiB`（诊断） | **5,364.3** | **599.9** | **1,010.5** | 3,137.3 | 121.3 | 74.8 | 420.5 | 1,757.7 | 78,487 |

结论：
- `#75`、`#75+#78`、`#75+#76+#78` 三者都在 Before ±2% 内（create 甚至更快 4~7%）；**没有任何一档因为 #75/#76/#78 变慢**。
- `#77` 单独就已经把 create +53%、rm +32%、git +36% 拉起来；四合一等于“#75/#76/#78 的持平”加上“#77 的回归”。
- `#77` 代码全部保留、只把 `TRANSFER_WINDOW` 退回 128 KiB（诊断，非产品）后，FAST-A 5,364.3 ms、create 599.9 ms、rm 1,010.5 ms、git 420.5 ms —— **回到 Before 水平**，而 64 MiB 的大小优势同时消失（write 121.3 ms，接近 Before 114.2）。

### 7.2 诊断实验（`DIAGNOSTIC`，已复原）

- 做法：在 `verify/lp75-78-combined` 上把 `engine/crates/layerfs-nfs/src/nfs.rs` 的 `pub const TRANSFER_WINDOW: u32 = 1024 * 1024;` 临时改成 `128 * 1024`，重建 release，跑 FAST-A ×2，然后 `git checkout -- engine/crates/layerfs-nfs/src/nfs.rs`，重建并核对 sha256 与实验前完全一致（`49d90d48…`），`git status` 干净。没有提交、没有改任何产品语义。
- 结果：见 §7.1 末行。**回归 = 1 MiB `rsize/wsize` 的客户端效应**，不是 #77 的 daemon 代码。
- 机制（待验证，本次未做抓包/内核侧取证）：1 MiB 后 macOS NFSv3 客户端按 rsize/wsize 调整了 I/O 缓冲与 readahead（`readahead=16`），小文件/元数据密集场景的客户端侧分配与等待变重；观测证据是**墙钟涨、daemon CPU 降、RPC 不涨**（客户端时间，不是服务端时间）。

---

## 8. 未完成 / NOT_RUN

| 项 | 状态 | 原因 |
|---|---|---|
| 1 MiB 窗口导致元数据变慢的客户端侧根因（抓包/ktrace/内核行为） | **NOT_RUN** | 需要 tcpdump/代理重放与更长窗口，超出本任务；本次只做到“关掉 1 MiB 就恢复”的因果级证据 |
| `#77` 中间窗口（256/512 KiB）是否两全 | **NOT_RUN** | 需要再改一版诊断构建 + 复测，留给 #77 决策 |
| AppleDouble `._*` 的 `Create`/`Write`/`Remove` 计数下降 | **NOT_RUN（未达成）** | 客户端仍照发 `._*`（1000 文件仍是 2000 Create/2000 Write）；#75 只是把它的 daemon 侧 SQLite 成本降到 0（daemon CPU 下降可见），RPC 计数不会变 |
| Durable profile | **NOT_RUN** | 按仓库策略长期禁用，未执行 |
| PostgreSQL Store | **NOT_RUN** | #74/#75–#78 口径只测 SQLite Store |
| `LFS 12 场景全量` | **NOT_RUN** | 本任务是 FAST 子集（FAST-B 8 行）+ 冷读，#79 再用快子集扩 |

---

## 9. 现场清理与状态

| 项 | 状态 |
|---|---|
| NFS 挂载 | `mount \| grep nfs` 为空（本次所有 Workspace 挂载已 `workspace unmount --discard`；最后一次复检 0 条） |
| 本任务 daemon | 0 个（`ps` 过滤 `layerfs-daemon --config …lp75-78…` 无结果；随 sandbox close 退出） |
| 临时 Store / home | `~/LayerFS/tmp/lp75-78/home*` 全部删除（10 个私有 home，含 Store + workspace） |
| `~/LayerFS/layerfs/QUIET` | 已删除（`ls` 报 No such file） |
| worktree | `~/LayerFS/wt/lp74` 已切回 `verify/lp75-78-combined` @ `1c49afc78`，`git status` 干净 |
| 本地分支 | `verify/lp75-78-combined`（未 push、未开 PR、未合并到任何共享分支） |
| 诊断改动 | 已 `git checkout` 复原，`diff` 与 `1c49afc78:nfs.rs` 完全一致 |
| release 二进制 | `~/LayerFS/tmp/lp74-target/release/{layerfs,layerfs-daemon}` = 四合一构建（246 MB 的 target 目录保留，供 #79 复用）；debug 构建产物 1.4 GB 已删 |
| 证据目录 | `~/LayerFS/tmp/lp75-78/`（69 MB）：`fast*/`、`replica*/`、`cold-*/`、`state/`（env、sha、`nfsstat -m`）、`bin-before/`、`bin-after/`、`build*.log`、`test-nfs.log`、`probe.sh`/`subset.sh`/`coldread.py`/`gitonly.sh` |

---

## 10. 给决策的三句话

1. **#75、#76、#78 可以按原样推进**：三档组合的 FAST-A 都持平或略快，daemon CPU −11~−17%，`RdirPlus` 精确减半，git 场景 RENAME/COMMIT 的冗余 owner job 归零（测试+实测双证）。
2. **#77 需要一次取舍决定**：1 MiB 让 64 MiB 读写 RPC 掉 8 倍、单场景墙钟 −5~12%，但把小文件/元数据/git 场景墙钟抬高 9~51%，FAST-A/B 合计因此 +20.7%/+16.7%。建议先按 256 KiB 或 512 KiB 复测，或让传输窗口可配置（默认 128 KiB，大文件路径显式开启）。
3. **#78 可以合入**：0 阻塞，3 条建议都是边界收口（`Retire` 收紧、`held_stat` 注释、Unchanged 的 `wcc[1]`）。

---

## 11. 后续状态（2026-11-07 16:21，不改本文任何实测数字与结论）

本文 §5/§7 把「元数据场景 `Getattr` +625~1993」归因到 #75 的伴生文件 `wcc_data = (None, None)`，§1.3 对 #78 提了 3 条建议。这两项已在 Lane A 的两个分支上落地（细节见 `LP75-RESULTS.md` §七 与 `LP78-RESULTS.md` §七），本文的 Before/After 数字仍是 `b1802332b` vs `1c49afc78` 那次实测的原始记录：

| 项 | 落地提交 |
|---|---|
| 伴生文件父目录 `wcc_data` 缓存（消除 `NATTRINVALIDATE` 引起的额外 `Getattr`） | `feat/lp75-nfs-create-unlink` `467d0c53a` |
| `Kernel::read_into`（单次 `open_file`、窗口字节直接追加进回复缓冲） | 同上 |
| `apple_double.rs` 模块注释与 `nfs.md` 规则同步 | 同上 |
| 合并 `#75` 新 head 进 `#78` | `feat/lp78-nfs-git` `9bc4093e8` |
| 伴生 / 客户端 silly 名 `RENAME` 两半取自目录缓存；`Retire::open()` 收紧；`held_stat` 注释对齐；`Unchanged` 分支 `wcc[1]` 用测试钉死 | `feat/lp78-nfs-git` `6fb19d412` |

尚未做的：**带这些修复的挂载实测（`Getattr` 是否回到 `LP77-DEEP-RESULTS.md` §三 的 `3457~5011` 基线、256 KiB 挂载是否仍是甜点）留给 #79 单跑**；本文 §8 的 NOT_RUN 项状态不变。

> **2026-11-07 17:05 更新（§12）**：这两项已在 FINALIZE 复测里做了。结论：256 KiB 挂载确实是甜点（元数据 ±1%、64 MiB RPC −50%、`rsize/wsize=262144` 未被夹回）；`create 1000 files` 的 `Getattr` 仍 +24%（3,223→4,001），**没有**回到基线，但墙钟持平。
---

## 12. FINALIZE（2026-11-07 17:0x）：最终四合一重测，窗口定案 256 KiB

本节是**发 PR 前对「最终四合一」的复测**。§4–§7、§11 的原始记录一个字都没改；本节是同一台机器、同一驱动、同一口径下的一次**受控重测**，Before 与 After 都在本窗口内重新跑了一遍（不是跟 §4 的历史数字比）。

### 12.1 pin 与二进制

| 项 | 值 |
|---|---|
| Before pin | `upstream/layerfs_v2_0_0` @ `b1802332b`（沿用 `~/LayerFS/tmp/lp75-78/bin-before`，sha256 `3d640147…ff57407` / `f54b1d41…7cb03c9`） |
| After pin | `verify/lp75-78-combined` @ **`85a0865cd`**（= `feat/lp78-nfs-git` `6fb19d412`（含 `#75` 的 `467d0c53a`）+ `#76` `f1ed75786` + `feat/lp77-nfs-seq-io` `a0e752b7b`，后者已 merge `upstream/layerfs_v2_0_0` `aa131e394`；三次 merge 全部 0 冲突） |
| After release sha256 | `eb2e3160…df0d3a`（`layerfs`）/ `1626eab8…7bfda`（`layerfs-daemon`） |
| 构建 | `CARGO_TARGET_DIR=~/LayerFS/tmp/lp74-target CARGO_PROFILE_RELEASE_STRIP=none cargo +1.85.1 build --release --locked -j 2 --bin layerfs --bin layerfs-daemon` → Finished 55.49 s（21 个第一方 crate 全部重编，第三方依赖命中缓存）；`QUIET` 哨兵在构建前 `touch`、编完立即删除（收尾已确认不存在） |
| 机器 | MacBook Air M2 8c / 16 GiB / macOS 27.2 (26B123)，load 2.8–3.2（GUI 常驻进程，无编译/测试并发） |
| 驱动 | `~/LayerFS/tmp/lp75-78-final/finalize.sh`（一次调用 = 全新私有 home + Store + project + Sandbox + 挂载，然后 FAST-A / FAST-B / NINE 各 2 轮 → `replica.py` 逐场景窗口 → `coldread.py` 冷读） |
| 口径 | 与 §3 完全一致：冻结脚本 `0e200433…37230ef`、GNU bash 5.2.37、`RANDOMIZE_TARGETS=0`、脚本自报 `date +%s%N`、`nfsstat -c` 差分、`proc_pid_rusage` CPU |

`nfsstat -m` 实测协商（本次新采）：
- Before：`Original … rsize=131072,wsize=131072` → `Current … rsize=131072,wsize=131072,readahead=16,rdirplus`
- After：`Original … rsize=262144,wsize=262144` → **`Current … rsize=262144,wsize=262144,readahead=16,rdirplus`**
- 即 256 KiB 挂载参数**没有被服务端夹回**（对比 §6.1：1 MiB 那次 Before 被 FSINFO 夹回 128 KiB），传输窗口与服务端宣告完全一致。

### 12.2 三档合计（每档 n=2，2 轮独立调用）

| 档 | arm | 脚本自报和 ms | 整次调用墙钟 ms | daemon CPU ms | NFSv3 RPC |
|---|---|---:|---:|---:|---:|
| FAST-A（6 行） | Before | **5,207.2** | 6,869.4 | **2,117.7** | **73,627.5** |
| FAST-A（6 行） | After `85a0865cd` | **5,226.1** | 6,578.3 | **1,643.7** | **71,648** |
| | 变化 | **+0.4%** | −4.2% | **−22.4%** | −2.7% |
| FAST-B（8 行） | Before | **5,623.9** | 8,120.5 | **3,266.5** | **76,182** |
| FAST-B（8 行） | After | **5,548.8** | 7,272.2 | **2,304.6** | **72,272.5** |
| | 变化 | **−1.3%** | −10.4% | **−29.5%** | −5.1% |
| NINE（9 行 = FAST-B + `mkdir tree`） | Before | **8,574.1** | 11,558.2 | **3,699.7** | **97,464.5** |
| NINE（9 行） | After | **8,495.8** | 10,674.0 | **2,688.3** | **92,901.5** |
| | 变化 | **−0.9%** | −7.7% | **−27.3%** | −4.7% |

> 与 §4 那次（Before 5,181.6 / After 6,254.6，+20.7%）的差别只有一个：**After 侧的传输窗口从 1 MiB 换成了 256 KiB**。Before 两侧 5,181.6 vs 5,207.2（+0.5%）再次复现了这台机器的可比性。

### 12.3 逐场景（NINE 档，墙钟 = `fast.py` 脚本自报，n=2 均值）

| 场景 | Before ms | After ms | Δ | daemon CPU ms B→A | 总 RPC B→A | 关键过程 B→A |
|---|---:|---:|---:|---|---|---|
| create 1000 files | 619.0 | 620.6 | **+0.3%** | 222.1 → 187.3 (−15.7%) | 10,356 → 11,006 (+6.3%) | Create 2000→2000；Write 2000→2000；**Getattr 3,223→4,001 (+24%)**；Lookup 2,130→2,002 |
| rm 1000 files | 1,016.2 | 1,019.5 | **+0.3%** | 450.3 → 382.6 (−15.0%) | 19,922 → 19,867 (−0.3%) | Remove 2000→2000；Getattr 5,009→5,009；**RdirPlus 2→1** |
| mkdir tree (10×10×10) | 2,954.9 | 2,937.9 | −0.6% | 215.2 → 181.9 (−15.5%) | 10,234 → 10,239 (+0.05%) | Create 2110→2110；Mkdir 110→110；Getattr 3,345→3,345 |
| find tree | 3,041.1 | 3,023.2 | −0.6% | 215.9 → 185.5 (−14.1%) | 10,567 → 10,449 (−1.1%) | **RdirPlus 222→111 (−50%)**；Getattr 3,460→3,453；Lookup 2,223→2,222 |
| write 64 MiB | 123.3 | 111.7 | **−9.4%** | 119.4 → 115.8 (−3.0%) | 527 → **270 (−48.8%)** | **Write 513→257**；每调用 131,072 B → **262,144 B** |
| copy 64 MiB | 240.2 | 222.3 | **−7.5%** | 246.8 → 229.0 (−7.2%) | 1,079 → **567 (−47.4%)** | **Write 1029→517**；Setattr 18→18 |
| pure copy 64 MiB | 126.0 | 115.2 | **−8.6%** | 120.9 → 111.9 (−7.4%) | 554 → **297 (−46.4%)** | **Write 516→260** |
| overwrite 64 MiB | 80.8 | 69.6 | **−13.9%** | 76.9 → 71.8 (−6.6%) | 519 → **259 (−50.1%)** | **Write 512→256**；Lookup 2→0 |
| git init + commit 100 files | 372.6 | 375.9 | +0.9% | 115.6 → 102.4 (−11.4%) | 5,759 → 5,724 (−0.6%) | Rename 19→19；Getattr 1,499→1,484；**RdirPlus 8→5**；Remove 218→218 |

**读表要点**
1. **元数据/小文件场景回到持平**：create +0.3%、rm +0.3%、mkdir −0.6%、find −0.6%、git +0.9%，全部在 ±1% 内（§5 那版 1 MiB 是 +9~51%）。
2. **64 MiB 顺序 I/O 的优势保住了一半**：Write RPC 精确减半（512/513 → 256/257，−50%），四个大文件场景墙钟 −7.5~−13.9%。这是 256 KiB 相对 128 KiB 的净收益，相对 1 MiB 少了一半 RPC 节省。
3. **daemon 侧工作量全部下降**：9 个场景的 daemon CPU 无一上升（−3.0%~−15.7%），整次调用 −27.3%。
4. **`create 1000 files` 的 `Getattr` 仍是 +24%（3,223 → 4,001）**：§11 记录的 `directory_wcc` 修复（`467d0c53a`）本轮确实在树上，但它没有把这批 `GETATTR` 消掉（其余 8 个场景 `Getattr` 持平或微降）。这批客户端属性刷新不影响墙钟（create +0.3%），但**"`Getattr` 回到基线"这个预期在本轮没有达成**，照实记录。
5. **整次调用墙钟（含 setup/teardown）−4.2%~−10.4%**：`fast.py` 的 `outer_wall` 比脚本自报和降得更多，与 §5.1 第 2 条的客户端行为一致。

### 12.4 64 MiB 冷读（write → commit → unmount+remount → `cat`，n=1）

| 窗口 | arm | 墙钟 ms | daemon CPU ms | NFSv3 RPC | Read | Write |
|---|---|---:|---:|---:|---:|---:|
| write 64 MiB（冷目标） | Before | 126.6 | 119.9 | 526 | 0 | **513** |
| write 64 MiB（冷目标） | After | **118.8** | 112.1 | **270** | 0 | **257** |
| **pure read 64 MiB（冷）** | Before | **41.6** | 27.7 | 516 | **512** | 0 |
| **pure read 64 MiB（冷）** | After | **37.6** | 23.7 | **260** | **256** | 0 |
| pure read 64 MiB（随即热读） | Before | 11.9 | 0.0 | 0 | 0 | 0 |
| pure read 64 MiB（随即热读） | After | 12.0 | 0.0 | 0 | 0 | 0 |

- **Read RPC 512 → 256（−50%）**、**Write RPC 513 → 257（−50%）**，与 256 KiB 窗口精确对应（64 MiB ÷ 256 KiB = 256）。冷读墙钟 −9.6%、daemon CPU −14.4%；热读两臂都是 0 RPC（客户端页缓存）。
- 对比 §6.2 的 1 MiB 那版（Read 64 / Write 65，冷读 35.7 ms）：256 KiB 的 RPC 是它的 4 倍，冷读墙钟只慢 5%（37.6 vs 35.7 ms），**换来的正是元数据场景那 9~51% 的回归消失**。

### 12.5 结论

1. **四合一现在可以按原样合**：三档合计都不比 Before 慢（FAST-A +0.4%、FAST-B −1.3%、NINE −0.9%），daemon CPU −22%~−30%，64 MiB 的 RPC 减半、墙钟 −7.5~−13.9%，元数据场景全部回到 ±1%。
2. **`#77` 的窗口取舍定案为 256 KiB**（`TRANSFER_WINDOW = WRITE_WINDOW = 256 KiB`，编译期断言相等；`pager_kib` 1024→4096）。三种候选里这是唯一"两头都不亏"的一档：元数据持平、大文件 RPC 减半。
3. 仍未达成的：`create 1000 files` 的 `Getattr` +24%（不影响墙钟）；`#77` 的 5 处架构文档仍写 128 KiB（见本节 §12.6）。两者都记在 PR 草稿的「已知限制」里。

### 12.6 本轮发现的待办（不阻塞合入，但发 PR 前应处理）

| 项 | 证据 | 建议 |
|---|---|---|
| `#77` 改 `WRITE_WINDOW` 128→256 KiB，但 5 处架构文档仍写 128 KiB | `docs/architecture/engine/overlay/README.md:97`、`overlay/payload.md:108`、`workspace/README.md:126`、`kernel-routes/README.md:118-119`、`kernel-routes/fuse.md:136` | 按仓库"文档随实现更新"的规矩，发 PR 前一并改；`#77` 自己的提交只同步了 `nfs.md` |
| FUSE 写边界校验用的是 `WRITE_WINDOW`（现 256 KiB），而挂载协商的 `max_write` 与 `MAX_INPUT_BYTES`（`READ_WINDOW + 2*255` = 131,582 B）仍按 128 KiB | `engine/crates/layerfs-fuse/src/request/callbacks.rs:557` vs `dispatch/types.rs:13` | 防御性收口：把该校验收成 `READ_WINDOW`，使它与自身协商闭环，不随 overlay/NFS 窗口漂移 |
| `create 1000 files` 的 `Getattr` +24% | §12.3 | 留给 #79 的八行报告观察，不在本 PR 里改 |

### 12.7 现场清理（本轮）

| 项 | 状态 |
|---|---|
| NFS 挂载 | `mount \| grep 127.0.0.1:/` 为空（两臂各自的 Workspace 都已 unmount，冷读的 remount 也已卸载） |
| 本任务 daemon | 0 个（`pgrep -f "layerfs-daemon --config .*lp75-78-final"` 无结果） |
| `~/LayerFS/layerfs/QUIET` | 已删除（构建结束即删，收尾 `ls` 确认不存在） |
| 私有 home / Store | `~/LayerFS/tmp/lp75-78-final/home-{before,final}` 待收尾删除（见任务单 LP75-78-PR-DRAFTS §6） |
| 二进制留档 | `bin-final/`（本轮 After）、`bin-before/`（`b1802332b`）、`bin-after-1c49afc78/`（上一轮 1 MiB 的 After） |
| 证据目录 | `~/LayerFS/tmp/lp75-78-final/`：`fast-{before,final}/fast.jsonl`、`replica-{before,final}/{windows,replica-rpc}.jsonl`、`cold-{before,final}/`、`state/`（`sha-*.txt`、`nfsstat-m-*.txt`、mount/daemon pid）、`run-{before,final}.log` |
