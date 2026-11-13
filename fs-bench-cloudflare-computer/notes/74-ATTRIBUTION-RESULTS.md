# #74 macOS 原生 NFS 耗时归因 — 正式测量结果（LP74-RUN）

> 本文是 LayerFS 基准仓库收录的本地测量笔记（`layerfs-project#73` 与 PR #604–#607 引用的那份原文）。
> 收录时只做了脱敏与路径清洗：本地 worktree/缓存目录前缀统一写成 `~/LayerFS/…`，主机名写成机型；
> 实验数据、表格与结论未改动。

- 日期：2026-11-07（Asia/Shanghai）。第一轮 LP74-RUN 采样 11:36–11:58（收尾 12:00）；第二轮 LP74-SUPP 补齐 12:12–12:40（§17–§20 为第二轮）。
- 范围：**只测量**。未改产品分支、未 commit、未 push、未发 GitHub 评论。第一轮未编译任何产品代码；第二轮为拿到 `Server::counters()` 与 AppleDouble 对照，编了一个**临时诊断构建**，测完把三个文件 `git checkout` 复原、二进制按 sha256 换回原件（§20）。
- 前置：`tasks/LP74-PREP-RESULTS.md`（环境与脚本准备）、`tasks/LP74-CODE-SCAN.md`（静态摸底）。
- 原始数据：`~/LayerFS/tmp/lp74-run/`（第一轮：jsonl + 每场景 nfsstat 快照 + 汇总表 `state/tables.md`）、`~/LayerFS/tmp/lp74-run2/`（第二轮：`proc12/`、`cold2/`、`adarms*/`、`proxy3/`、`appledouble/`、`DIAGNOSTIC.patch`）。

---

## 0. 通过 / 失败 / 未运行

| | 数量 | 明细 |
|---|---|---|
| 通过 | 12 | ①12 场景正式采样（24 行全部 `OK`，退出 0）②replica 干净窗口采样（24 行 `OK`）③FAST-A/FAST-B 基线（4 轮 `OK`）④Exec 启动开销量化 ⑤挂载选项对照（6 个变体，全部有 `nfsstat -m` 生效证据）⑥AppleDouble 侧写取证（RPC 级）⑦`LAYERFS_NFS_MOUNT` 钩子可达性判定 ⑧噪声带复测（同一配置重复 5 次）⑨现场清理。第二轮 3 项：⑩**逐过程 daemon 计数**（12 场景 × calls+nanoseconds，§17；WRITE 的 stable/unstable 与每调用字节数见 §17.5）⑪**64 MiB 冷读真路径**（3 样本，512 次 READ RPC，§18）⑫**AppleDouble 抑制实验**（客户端选项矩阵 + 服务端三条策略实测，§19） |
| 失败 | 0 | — |
| 未运行/不可得 | 3 | ①daemon 侧 `OwnerWork`/`StatementWork`（SQL 次数与耗时）/`PayloadWork` **本构建仍取不到**（本机无 `Request::Observed` 调用方，见 §11；逐过程纳秒已由 §17 补齐）②`LAYERFS_NFS_MOUNT` 钩子不可达（daemon 被 `env_clear` 派生，改用手工二次挂载，见 §9.1）③PostgreSQL 行（#74 范围外） |

---

## 1. 机器与 pin 声明

| 项 | 值 |
|---|---|
| 机器 | MacBook Air（Apple M2，8 核，16 GiB），macOS 27.2（26B123） |
| 状态 | 桌面机，非专用机：测量期间 `load average 4.1–6.0`，WindowServer/Chrome/WeChat/linkd/mds_stores 等常驻。**已按单线程顺序跑**，两臂逐场景交替，但噪声带约 ±10%（§2.3） |
| worktree | `~/LayerFS/wt/lp74`，detached @ `b1802332b1c4ee04251449a13bb2851b80f5fc1f`（干净，未改） |
| `layerfs` | `~/LayerFS/tmp/lp74-target/release/layerfs`，sha256 `3d6401477c9463ed3d7963d5a10592ee0e97541afc21ba1126cfc7416ff57407`（未重编） |
| `layerfs-daemon` | 同目录，sha256 `f54b1d418f33044ddd06d638567e6af2c2afaa1644b996c698b8437717cb03c9` |
| 冻结脚本 | `~/LayerFS/tools/fs-bench/fs-bench.sh`，sha256 `0e2004339a9269b88c2de451d56575957477bde16b96a10cf1837519e37230ef`（pin `6358760a`，与 `cases.py` 常量一致，未改） |
| bash | 同一把 `~/LayerFS/tools/fs-bench/bin/bash` 5.2.37（两臂完全相同） |
| PATH | 两臂完全相同：`<tools>/bin:/usr/bin:/bin:/usr/sbin:/sbin`，`LANG=C LC_ALL=C` |
| 计时口径 | 脚本自身 `date +%s%N`（`REPS=1 WARMUP=0 RANDOMIZE_TARGETS=0`，单样本）；另记外层墙钟与 daemon CPU |
| 挂载 | `127.0.0.1:/ on <home>/machine/native/run/lfs-9b8a8f87-tests/workspaces/1 (nfs, nodev, nosuid, noatime, nobrowse)`，普通用户挂载 |
| Store | `lprun`（sqlite / native / **disposable**，`store create` 默认），project `lprun/demo`，branch `agent` |

第二轮（LP74-SUPP）在同一个 worktree / 同一个 CLI 上做，唯一区别是 daemon 换成一个**临时诊断构建**（`6ab53d02…7800`，后来又加了 deny 开关 `33b6f02b…045c`；补丁、构建命令、还原证据全在 §20），以及一个新建的 `~/LayerFS/tmp/lp74-run2/home`（同样 disposable、同样只跑 native NFS）。

**两臂定义**：`host` = 纯 APFS 目录 `~/LayerFS/tmp/lp74-run/apfs/work`（同一卷、同一脚本、同一 bash）；`layerfs` = 上述 native NFS 挂载目录。两臂的 nfsstat 差分均为零（host 12 场景 RPC 合计 0–8，属别处噪声）。

---

## 2. 方法

### 2.1 三轮采样

1. **正式轮（r1）**：冻结脚本，每场景一次独立调用（`SCENARIOS="<该场景名>"`），host 与 layerfs **逐场景交替**（先 host 再 layerfs），保证同一场景两臂受同一时段的机器负载影响。数字 = 脚本自报 `mean`。
2. **干净窗口轮（replica）**：用冻结脚本**逐字复制**的命令（`replica.py` 里的字符串与 `fs-bench.sh` 一致），自己切三个窗口：`prep` / `timed` / `teardown`。冻结脚本把建目录、`dd` 预置和收尾 `rm -rf` 都放在计时区外，但 `nfsstat` 差分把它们都算进来（PREP §5.4-1），此轮把 RPC 计数与 daemon CPU 精确归到 **timed 区**。r1 与 replica 的墙钟互相校验（差 <3%，见两表），因此后续归因一律引用 replica 的窗口数据。
3. **噪声带轮**：同一挂载、同一配置重复 5 次（base/base2/base4/base5 + 1 次带 `sample` 的 base3），用于标定单样本可比性。

### 2.2 计数与 CPU 口径

- **客户端 NFS 过程计数**：`/usr/bin/nfsstat -c` 前后差分，只取 `NFSv3 RPC Counts` 段（其余段有多词表头，位置对齐不安全），每场景保留 before/after 原始快照。RPC 计数是确定量：同一场景重复 5 次，`Create/Write/Getattr/Remove` 逐项完全一致（§9 表）。
- **daemon CPU**：`proc_pid_rusage(RUSAGE_INFO_V4)` 的 `ri_user_time + ri_system_time`。注意该 API 返回的是 **mach absolute 单位**（本机 timebase 125/3 ≈ 41.67 ns），已按 `mach_timebase_info` 换算；与 `ps -o utime,stime` 交叉核对一致（1515 ms vs 0.77+0.75 s）。
- 不含客户端内核态 CPU（无 root，取不到 per-mount 内核时间）；`wall − daemonCPU` 含客户端内核 + RPC 往返 + 调度，只能整体当作"客户端与协议侧"。

### 2.3 噪声带（必须带上）

同一挂载、同一配置、连跑 5 次 `create 1000 files`：

| 次 | create ms | RPC | Create |
|---|---:|---:|---:|
| base | 964.6 | 11011 | 2000 |
| base2 | 724.7 | 11010 | 2000 |
| base3（同时 `sample` 采样） | 1343.9 | 11008 | 2000 |
| base4 | 698.1 | 11012 | 2000 |
| base5 | 648.6 | 11012 | 2000 |

→ **墙钟噪声 ±20%（create，短场景）/ ±8%（find tree, rm）**；**RPC 计数零噪声**。故：墙钟差异 <10% 不下结论；RPC 计数与 `nfsstat -m` 生效值可直接下结论。

---

## 3. 十二场景正式结果（r1，单样本，两臂交替）

| 场景 | host ms | LayerFS ms | 倍数 | 净增 ms | LayerFS daemon CPU ms* |
|---|---:|---:|---:|---:|---:|
| create 1000 files | 69.6 | 670.1 | **9.63×** | +600.5 | 486.9 |
| stat 1000 files | 4265.8 | 4814.2 | 1.13× | +548.4 | 475.3 |
| rm 1000 files | 101.2 | 1050.4 | **10.38×** | +949.2 | 449.7 |
| mkdir tree (10x10x10) | 1906.6 | 3076.1 | 1.61× | +1169.5 | 450.3 |
| find tree | 1930.9 | 3129.6 | 1.62× | +1198.7 | 445.1 |
| write 64 MiB | 23.8 | 125.2 | 5.26× | +101.4 | 625.5 |
| copy 64 MiB | 134.1 | 246.5 | 1.84× | +112.4 | 1044.1 |
| read 64 MiB | 60.7 | 135.1 | 2.23× | +74.4 | 554.0 |
| pure read 64 MiB | 10.8 | 11.3 | 1.05× | +0.5 | 278.0 |
| pure copy 64 MiB | 41.3 | 117.4 | 2.84× | +76.1 | 523.7 |
| overwrite 64 MiB | 20.3 | 69.8 | 3.44× | +49.5 | 313.0 |
| git init + commit 100 files | 110.1 | 378.1 | 3.43× | +268.0 | 206.6 |
| **合计** | **8675.2** | **13823.8** | **1.59×** | **+5148.6** | — |

\* r1 的场景调用把收尾 `rm -rf` 也罩在 `nfsstat`/CPU 差分里（见 §2.1-2），所以这一列只作量级参考；**精确的 daemon 侧数字见 §4 的 replica 表**。

读法：

- 十二场景**合计净增 5.15 s**，其中 **mkdir/find tree 占 2.37 s**、**create/rm 占 1.55 s**、**64 MiB 五场景占 0.41 s**、git 0.27 s、`stat` 0.55 s。
- `stat 1000 files` 的 1.13× 是**假低**：它其实是 1000 次 `fork+exec` 基准（§6），NFS 只贡献约 100 ms。
- `pure read 64 MiB` 1.05× 是**假零**：客户端页缓存命中，NFS `READ` 计数为 0（§4.3）。

---

## 4. 逐场景归因（replica 干净窗口，timed 区独占）

`daemon CPU` = daemon 进程在 timed 窗口内的 user+sys；`客户端与协议` = 墙钟 − daemon CPU。

| 场景 | host ms | LayerFS ms | daemon CPU ms | **客户端与协议 ms** | NFSv3 RPC | RPC/用户文件 | 主要过程（次数） |
|---|---:|---:|---:|---:|---:|---:|---|
| create 1000 files | 63.5 | 639.9 | 235.1 | 404.8 | 11006 | 11.0 | Getattr 4001 · Lookup 2001 · Create 2000 · Write 2000 · Setattr 1000 |
| stat 1000 files | 4230.1 | 4960.9 | 231.1 | 4729.8 | 11006 | 11.0 | 与 create 完全相同（1000 次 `stat` 未产生额外 RPC） |
| rm 1000 files | 99.9 | 1065.7 | 451.0 | 614.7 | 19858 | 19.9 | Lookup 6849 · Getattr 5003 · Create 2000 · Remove 2000 · Write 2000 |
| mkdir tree (10x10x10) | 2155.2 | 3206.3 | 214.0 | 2992.3 | 10222 | 10.2/1000 文件 | Getattr 3333 · Lookup 2224 · Create 2110 · Setattr 1110 · Mkdir 110 |
| find tree | 2116.0 | 3269.8 | 216.1 | 3053.7 | 10560 | 10.6/1000 文件 | 同上 + RdirPlus 222（110 目录 ×2） |
| write 64 MiB | 19.7 | 127.0 | 120.9 | 6.1 | 526 | — | Write 513（512×128 KiB） |
| copy 64 MiB | 47.4 | 255.8 | 244.2 | 11.6 | 1087 | — | Write 1029（写 2×64 MiB） |
| read 64 MiB | 29.0 | 136.1 | 120.0 | 16.1 | 537 | — | Write 513 · **Read 0**（页缓存） |
| pure read 64 MiB | 11.5 | 12.6 | 0.1 | 12.5 | 2 | — | 全命中客户端缓存 |
| pure copy 64 MiB | 40.1 | 130.3 | 122.3 | 8.0 | 554 | — | Write 516 |
| overwrite 64 MiB | 19.6 | 82.7 | 77.5 | 5.2 | 515 | — | Write 512 |
| git init + commit 100 files | 101.6 | 368.7 | 116.5 | 252.2 | 5737 | 28.7 | Lookup 1783 · Getattr 1481 · Create 569 · Write 563 · Setattr 478 · Remove 218 · Link 102 · Rename 19 |

### 4.1 归因结构（三类，量纲不同）

1. **daemon 侧 CPU 占大头、且几乎线性于 RPC 数（64 MiB 类）**：write/pure copy/overwrite 的 daemon CPU 就是墙钟的 93–95%（120.9/127.0、122.3/130.3、77.5/82.7），客户端与协议侧只剩 5–16 ms。→ 优化点全在 Overlay/SQLite 写路径（#77）。
2. **元数据类（create/rm/git）是往返 + 每 op 固定成本**：create 1000 文件 640 ms 里 daemon CPU 235 ms（37%），其余 405 ms 是 11,000 次 RPC 的往返与客户端内核开销 → **平均 36 µs/RPC**，daemon 侧 **21 µs/RPC**、**118 µs/新建 inode**（2000 inode / 235 ms）。
3. **进程 spawn 类（stat / mkdir tree / find tree 的 shell 循环）**：与文件系统几乎无关（§6），必须从"文件系统归因"里剔出去看。

### 4.2 每个用户文件实际是 2 个 inode（本轮最大发现，见 §5；**inode 这一条在第二轮被修正**）

`create 1000 files` 的 2000 次 CREATE 不是重试，也不是 2 次落同一个名字：**每个新文件伴随一个 `._<name>` AppleDouble 侧文件**。RPC 与协议动作确实是两倍，所以 per-user-file 成本要除以 2 才能和 per-protocol-object 对比：0.32 ms/文件、5.5 RPC/对象、~118 µs daemon CPU/对象。

但第二轮（§19.2）把 inode 那一半修正了：本构建的 export 把 `._*` **只留在 daemon 内存里**（`engine/crates/layerfs-nfs/src/apple_double.rs`），1000 个用户文件在工作区里只占 **1000 个 inode**（`workspace status` 实测 2→1002），不是 2000。也就是说：**协议侧翻倍，存储侧不翻倍**。

### 4.3 读路径在第一轮无信号，第二轮已用冷读打通（见 §18）

`read 64 MiB`、`copy 64 MiB` 的 `Read` 过程计数都是 **0**（PREP §5.4-2 的判断被本轮确认）。`pure read 64 MiB` 全程命中客户端页缓存（2 次 RPC、daemon CPU 0.1 ms）。要测读必须换冷缓存设计（另开挂载/`actimeo=0`/改预置位置），属测量设计变更，需授权。

---

## 5. 关键发现 A：CREATE 翻倍的真凶是 AppleDouble 侧写（RPC 级取证）

PREP §5.5 留下的第一优先验证项（"每个新文件约 2 次 CREATE、2 次 WRITE"）已确认。方法：写了一个**用户态 TCP 代理**（`nfsproxy.py`，无需 root）串在 mount 与 daemon 之间，解 RPC 记录的 XDR 参数：

```
LOOKUP  q1                NOENT
CREATE  q1    UNCHECKED   OK
LOOKUP  ._q1              NOENT
CREATE  ._q1  UNCHECKED   OK
...（q2、q3、qdir 同形：目录也带 ._qdir）
rm q1:
LOOKUP  q1    OK → LOOKUP q1 OK → REMOVE q1 OK
LOOKUP  ._q1  OK → LOOKUP ._q1 OK → REMOVE ._q1 OK
```

- `._q2` 在客户端可见为 4096 字节的普通文件（`stat` 实测 `size=4096 blocks=8 mode=-rw-r--r--`），内容是 AppleDouble 头（`\0\x05\x16\x07 ... Mac OS X`）。
- 原因是 macOS 27.2 对新建文件打 `com.apple.provenance` 扩展属性；NFSv3 无 xattr 通道，客户端就把元数据写进同名 `._` 文件。代理日志里**没有任何 xattr 侧程序尝试**（只有 `MOUNT/1` 2 次、NFSv3 其余），即客户端直接落到 AppleDouble，没有先探测服务端能力。
- 客户端自己的 `readdir` 会隐藏 `._` 名字（`ls`、`find` 都看不到，`find . -type f` 计数 1000 而不是 2000），所以基准数字不暴露它，但 **daemon 侧真实承担了双倍 inode、双倍 CREATE/WRITE/SETATTR，删除时双倍 REMOVE**。

量化影响（1000 个用户文件）：2000 CREATE + 2000 WRITE + 1000 SETATTR + 2000 LOOKUP + 4001 GETATTR；删除时 2000 REMOVE。若服务端能承接 xattr（或工作区能免掉 provenance 落盘），#75 的 create/unlink 成本**结构性减半**，且每个文件省 4 KiB。

> **第二轮修正（§19）**：本构建**已经**把 `._*` 挡在工作区之外（只在 export 内存里持有），所以“每个用户文件 2 个 inode”只对 RPC/协议动作成立，对工作区 inode 与 4 KiB 存储不成立：实测 1000 个用户文件 = 1002 inode（含根与目录）。把抑制关掉才会变 2003 inode，那时 create 贵 21%、rm 贵 24%（§19.2）。而如果改成“直接回 NFS3ERR_ACCES”，create 再降 29%。所以 #75 的取向不是“让 `._` 消失”（客户端不给任何选项），而是“选哪种服务端策略”，三条策略的实测见 §19.2。

> 这是"产品行为"层面的发现，不是 LayerFS 的 bug（任何 NFSv3 服务端在这台客户端上都会收到 `._` 文件）；但它是 #75 成本模型里最大的一项，优先级高于任何单 op 微优化。

---

## 6. 关键发现 B：`stat 1000 files` 是 fork/exec 基准，不是文件系统基准

issue #74 第 4 项要求的 Exec 开销验证（三轮取最小值，同一把 tools bash）：

| 路线 | 用例 | 最小 ms | 样本 ms |
|---|---|---:|---|
| host APFS shell | 1 × `/usr/bin/true` | 1.9 | 2.5, 2.2, 1.9, 2.0, 1.9 |
| LayerFS 挂载 shell | 1 × `/usr/bin/true` | 1.8 | 1.8, 2.0, 2.0, 2.0, 2.1 |
| host APFS shell | 1 × `/usr/bin/stat f0` | 4.5 | 4.6, 4.6, 4.6, 5.2, 4.5 |
| LayerFS 挂载 shell | 1 × `/usr/bin/stat f0` | 4.2 | 4.5, 4.2, 4.7, 4.4, 4.3 |
| host APFS shell | 1000 × `/usr/bin/true` | 1620.1 | 1624.7, 1620.1, 1637.9 |
| LayerFS 挂载 shell | 1000 × `/usr/bin/true` | 1622.2 | 1627.1, 1683.2, 1622.2 |
| host APFS shell | 1000 × `/usr/bin/stat f0` | 4188.3 | 4188.3, 4205.5, 4288.4 |
| LayerFS 挂载 shell | 1000 × `/usr/bin/stat f0` | 4295.5 | 4295.5, 4313.7, 4320.1 |
| `layerfs store list`（纯 CLI 启动） | — | 3.3 | 3.7, 3.7, 3.7, 3.6, 3.3 |
| `layerfs workspace exec` | 1 × `/usr/bin/true` | 14.2 | 16.4, 14.4, 14.2, 14.8, 14.3 |
| `layerfs workspace exec` | 1 × `/usr/bin/stat f0` | 16.7 | 16.9, 16.7, 16.7, 17.4, 17.4 |
| `layerfs workspace exec` | 1000 × `/usr/bin/true` | 1582.2 | 1582.2, 1593.1, 1595.0 |
| `layerfs workspace exec` | 1000 × `/usr/bin/stat f0` | 4244.6 | 4244.6, 4318.7, 4273.3 |
| 挂载 shell | create 1000 + stat 1000 | 5313.2 | 5378.5, 5492.1, 5313.2 |
| `workspace exec` 内 | create 1000 + stat 1000 | 5265.8 | 5571.0, 5390.9, 5265.8 |

结论：

1. **NFS 对进程启动零成本**：`/usr/bin/true` 在 APFS 与在 NFS 挂载里都是 1.8–2.1 ms，1000 次差 2 ms。`stat` 单次 4.5 vs 4.2 ms（挂载里反而略快，属噪声）。1000 次 `stat` 4.19 s vs 4.30 s → **NFS 占 2.5%**。
2. **`stat 1000 files`(4.8 s) = 1000 次 `/usr/bin/stat` 进程启动（4.2 s）+ create 1000 文件（0.64 s）**。更直接的证据：`stat` 场景的 RPC 计数与 `create` 场景**完全相同**（11,006 / 4001 Getattr），1000 次 `stat` 一次 RPC 都没多发——`actimeo=60` 把它们全挡在客户端属性缓存里。**这条场景在 #74/#75 里不能当文件系统信号用。**
3. **Exec 自身开销 = 约 11 ms/次调用**（14.2 − 3.3 CLI 启动 − 1.9 spawn ≈ 9；`exec bash -c true` 13.4 ms）。构成：CLI 进程 3.3 ms + 控制连接/记录查询 + `bash -c` 派生。**没有 Seatbelt**：native 路线的 exec 是 `Sandbox::HostProcess`，实测进程链是 `layerfs workspace exec → sleep`（没有 `sandbox-exec`、没有中间 shell），且 1000 条命令经 exec 走 **1582 ms**，与裸 shell 1620 ms 相同——若每条命令套一层沙箱，这个数字会翻倍。
4. **`workspace exec` 里没有额外每命令成本**：1000 次 stat 经 exec 4244.6 ms ≈ 挂载 shell 4295.5 ms；`stat 1000 files` 在 exec 内 5265.8 ms ≈ 挂载 shell 5313.2 ms。

---

## 7. 关键发现 C：READDIRPLUS 缺属性在 macOS 27.2 上**不**产生额外 LOOKUP

LP74-CODE-SCAN §3.2-A 的假设是：`directory.rs:56-57` 对每个 `READDIRPLUS` 条目写 `name_attributes=None, name_handle=None`，于是 macOS 客户端必须逐条 `LOOKUP`，导致 `find tree` 多 ~566 ms。本轮直接反证：

| 变体 | find tree ms | NFSv3 RPC | Lookup | RdirPlus | Readdir |
|---|---:|---:|---:|---:|---:|
| 默认（`rdirplus`） | 3665 | 10556 | 2222 | **222** | 0 |
| `nordirplus`（`nfsstat -m` 已生效） | 3861 | 10552 | **2222** | 0 | **222** |

- `nordirplus` 确实生效（协议从 READDIRPLUS 换成 READDIR，222 次），但 **Lookup 一次没少、总 RPC 一样、墙钟在噪声带内**。
- 另一个旁证：`find tree` 相对 `mkdir tree` 只多 63 ms（3270 vs 3206）和 338 次 RPC（222 RdirPlus + 116 Getattr/其它），不是 issue #73/#74 里写的 +566 ms。
- 结论：**对这台 macOS 27.2 客户端，"READDIRPLUS 不带属性"没有惩罚**——它本来就要 `getattr` 来判 `-type f`，而 `stat` 命中的是属性缓存。**#76 若以"补 READDIRPLUS 属性"为主攻方向，需要先在 26.4.1（#73 机器）上复现同一条对照**，否则可能优化掉一个不存在的成本。
- `find tree` 真正的开销是 1220 次进程 spawn（110 mkdir + 1000 touch + 1 find）≈ 2.0 s 的 host 基线，加上 2000 个协议对象（1000 个文件 + 1000 个 `._`；后者不占工作区 inode，见 §19）。

---

## 8. 关键发现 D：`rsize/wsize` 被服务端 FSINFO 夹在 128 KiB

issue #74 第 5 项要求判断"改挂载参数能否提升 64 MiB 吞吐"。实测（手工二次挂载同一 export，用 `nfsstat -m` 证明生效）：

```
请求：rsize=1048576,wsize=1048576
Original mount options: ... rsize=1048576,wsize=1048576 ...        ← 内核接受了请求
Current  mount parameters: ... rsize=131072,wsize=131072 ...       ← 实际生效被夹到 128 KiB
```

- 64 MiB 写的 `Write` 计数在 wsize=1 MiB 下仍是 **513**（512×128 KiB + 1），墙钟 152 ms vs 基线 140 ms（噪声内）。
- 夹点在上游：`engine/crates/layerfs-nfs/src/nfs.rs:252` 用 `READ_WINDOW/WRITE_WINDOW`（`layerfs-overlay/src/contract/types.rs:26,28` = 128 KiB）填 FSINFO 的 `rtmax/wtmax`，客户端取 `min(mount wsize, wtmax)`；`export.rs:103` 的 `rsize/wsize` 只是上限请求。
- **所以 #77 不可能靠挂载选项提速**：必须同时改 FSINFO（`nfs.rs:252`）+ 窗口常量（`types.rs:26,28`）+ `WRITE_LIMIT`/`changing.rs` 的切块，然后再谈 `write_record` 的整包拷贝。

---

## 9. 挂载选项对照（issue #74 第 5 项）

### 9.1 先决结论：`LAYERFS_NFS_MOUNT` 钩子在本构建里**不可达**

`engine/crates/layerfs-daemon/src/application/filesystem.rs:52-66` 确实读 `LAYERFS_NFS_MOUNT` 等四个变量，但 daemon 是由 CLI 以 **`env_clear()`** 派生的（`connect/crates/layerfs-sandbox/src/local/create.rs:217`，之后只注入 `PATH` + deploy 里的固定环境），调用方 shell 的变量不会传进去。

证据（本机实测）：

1. 设 `LAYERFS_NFS_MOUNT="/usr/bin/false {port} {dir}"` 后重启 daemon 再 `workspace mount` → **挂载仍然成功**（`{"kind":"Mounted",…}`）；若钩子生效，mount helper 失败必然拒绝挂载。
2. 设 `LAYERFS_NFS_MOUNT="…actimeo=3600…"` 后 `nfsstat -m` 的 **Original mount options 仍是默认串**（`acregmin=60 … rsize=131072`）。
3. 同理我第一轮"经钩子的选项实验"（`~/LayerFS/tmp/lp74-run/mountopt/`）**作废**：那些差异全是噪声。已保留目录并在本报告里明确标注，不当结论用。

**替代做法（本报告采用）**：daemon 的 export 是 `127.0.0.1:/`，可以对**同一个正在服务的 export** 用手工 `mount_nfs` 再挂一个客户端（不需要 root），然后用 `nfsstat -m` 的 `Original/Current` 两行证明参数真的生效。这套挂载与 daemon 自己的挂载同时存在，测量时只访问手工挂载点。

### 9.2 实测（每个变体一次，daemon 固定，同一天同一负载段）

`a create/RPC` 列是 `create 1000 files` 的墙钟与 NFSv3 总次数：

| 变体（`nfsstat -m` 已确认生效） | create ms | create RPC | Create 次数 | rm ms | rm RPC | find ms | find RPC | write 64 MiB ms | Write |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| base（默认：`locallocks,nfc,noatime,actimeo=60,rsize/wsize=131072…`） | 964.6 | 11011 | 2000 | 1327.8 | 19865 | 4083 | 10555 | 185.1 | 513 |
| base2（重复） | 724.7 | 11010 | 2000 | 1078.7 | 19873 | 3665 | 10556 | 139.8 | 513 |
| base4（重复） | 698.1 | 11012 | 2000 | 1152.3 | 19820 | 3666 | 10557 | 128.3 | 513 |
| base5（重复） | 648.6 | 11012 | 2000 | 1088.5 | 19912 | 3537 | 10552 | 156.4 | 513 |
| `actimeo=0` | **2012.5** | **62925** | 2000 | **2993.1** | **93688** | **5031** | **111411** | 142.4 | 513 |
| `actimeo=3600` | 700.0 | 11011 | 2000 | 1101.2 | 19801 | 3458 | 10562 | 153.2 | 513 |
| `rsize=wsize=1048576` | 741.8 | 11009 | 2000 | 1250.2 | 19900 | 3712 | 10556 | 151.8 | 513（被夹回 128 KiB） |
| `nordirplus` | 679.2 | 11016 | 2000 | 1192.6 | 19953 | 3861 | 10552（RdirPlus 0 / Readdir 222） | 138.8 | 513 |
| 去掉 `nfc` | 711.1 | 11015 | 2000 | 1099.4 | 19851 | 3433 | 10557 | 150.0 | 513 |
| 去掉 `locallocks` | **1708.6** | **15004** | **3000** | **1876.9** | **21843** | **4831** | **14328** | 164.6 | 512 |
| 去掉 `nfc` + `locallocks`（= 上一行的复现） | 1954.2 | 15002 | 3000 | 2133.0 | 21817 | 4642 | 14328 | 170.6 | 512 |

结论：

1. **`actimeo=60` 是这套挂载的关键收益项**：改成 0 后 RPC 涨 5.7×（create）/ 10.5×（find），墙钟涨 2.8×/1.4×，daemon CPU 从 235 ms 涨到 900 ms。改成 3600 相对 60 **没有任何额外收益**（700 ms / 11,011 RPC）→ 现行默认值选得对，不要动。
2. **`locallocks` 不是装饰**：去掉它，客户端的 create 协议**整体换形**（每文件 3 CREATE + 2 REMOVE + 1 Write，Setattr 归零），RPC +36%，create 墙钟 2.4×。默认串里有它，任何 #75/#77 的挂载实验都不能顺手删。
3. **`nfc` 无影响**（本工作负载全是 ASCII 名），可以不动。
4. **`nordirplus` 生效但无收益**（§7）。
5. **`rsize/wsize` 提高无效**（§8），瓶颈在服务端 FSINFO。
6. 噪声提示：base 四次 648–965 ms，因此除 `actimeo=0` 与去 `locallocks` 这两个**超过 2×** 的变体外，其余差异都在噪声带内、不作结论。

---

## 10. FAST 快子集基线（#75–#79 的回归铁证）

一轮 = 冻结脚本单次调用；`脚本合计` = 脚本自报各行 mean 之和；`整轮墙钟` = 我在外层测的整次调用（含脚本自己的建目录/收尾删除与进程开销）；`daemon CPU`/`RPC` 为整轮差分。

| 子集 | 臂 | 命中行数 | 脚本合计 ms | 整轮墙钟 ms | daemon CPU ms | NFSv3 RPC |
|---|---|---:|---:|---:|---:|---:|
| FAST-A | host APFS | 6 | 2218.1 | 2506.0 | — | 0 |
| FAST-A | LayerFS native | 6 | **5307.4** | 7045.9 | 2240.6 | **74756** |
| FAST-B | host APFS | 8 | 2269.4 | 2627.6 | — | 2 |
| FAST-B | LayerFS native | 8 | **5653.9** | 8212.8 | 3337.4 | **76130** |

FAST-A 逐行（LayerFS / host，ms）：create 636.1/59.7、rm 1066.1/96.7、find tree 3021.5/1916.8、write 64 MiB 130.0/22.8、overwrite 64 MiB 82.9/19.6、git 370.8/102.5。
FAST-B 追加两行：copy 64 MiB 255.3/45.8、pure copy 64 MiB 130.6/28.6。

定义（与 PREP §7 一致，勿改）：

```
FAST-A: SCENARIOS="create 1000 files,rm 1000 files,find tree,write 64 MiB,git init + commit 100 files"   → 命中 6 行（write 带出 overwrite）
FAST-B: 上面再加 copy 64 MiB                                                                                → 命中 8 行（copy 带出 pure copy）
```

用途：#75–#78 合并前后各跑一次（约 7–8 s 一轮），**只有 RPC 计数与 ≥10% 的墙钟变化可信**；要下结论仍用全量 12 场景 + replica 干净窗口。

---

## 11. 未能取得的 daemon 侧 SQL / OwnerWork 数据（结论：本构建取不到）

issue #74 要求"daemon 侧 OwnerWork / StatementWork（SQL 次数与耗时）/ PayloadWork"，以及每过程纳秒。第一轮四条路径全被现构建堵死，逐条给出证据；**其中“每过程纳秒”已在第二轮用临时诊断构建取得（§17）**，其余仍缺：

| 路径 | 状态 | 证据 |
|---|---|---|
| 公开状态调用（`workspace status` / `sandbox get` / `machine status` / `doctor`） | **不提供** | 它们只回 overlay inodes/entries、activity、revision、dirty；`MountWork` 里 `served/completed` 是 `Server::counters()` 的 calls 求和（`engine/crates/layerfs-daemon/src/control/export.rs:287-302`），没有过程表也没有纳秒 |
| `Request::Observed` 诊断行（含 `StatementWork`/`PayloadWork`/`jobs`/`lock_wait_ns`/`hold_ns`） | **无调用方** | 实现完整（`application/diagnostics.rs:139` 起，`resources.rs:147` 起向 daemon stderr 写第 28/30/34 段），但只有 `Request::Observed{scope,traced}` 才走；scope 来自 SDK 在调用参数里加的 `observe` 字段，而 `common/trace.rs:34 take_scope` 与 `run` **在 `api/` 全仓没有调用方**（项目自己的记录：`core/docs/issues/535/receipts/…/K2/RESULTS.md:143`、`core/docs/issues/536/DECISIONS.md:77`），CLI 也不注入该字段 |
| `LAYERFS_TRACE` | **native 路线不写** | `api/crates/layerfs-control/src/common/trace.rs:112` 只在 "connection to a machine's worker" 时写一行；native 直连 daemon 不经过 worker。实测：带 `LAYERFS_TRACE` 跑完整轮，文件未产生 |
| 每过程纳秒（`Server::counters()`） | **第一轮仅进程内；第二轮已取到** | `engine/crates/layerfs-nfs/src/server.rs` 的 `Server::counters()`；daemon 只把 calls 求和（上表第 1 行）。第二轮用一个**临时诊断构建**（标记文件变化时把 22+6 个过程的 calls/nanoseconds 追写 `/tmp/lp74-proc-counters.jsonl`，补丁见 `lp74-run2/DIAGNOSTIC.patch`，已复原）拿到全 12 场景的逐过程数据，见 §17 |
| 每个过程里的 SQL 次数/耗时（`StatementWork`） | **仍缺** | 同上：它只随 `Request::Observed` 出现，而该请求没有调用方；§17 的计数器只到 NFS 过程边界，不拆到 SQL |

**替代与替代品的边界**（本报告采用）：①每场景的 **daemon 进程 CPU 纳秒**（`proc_pid_rusage`，与 `ps` 交叉验证一致）——这是"daemon 侧耗时"的可靠上界；②**客户端逐过程 RPC 计数**（精确、可复算）；③`wall − daemonCPU` 作为"客户端内核 + RPC 往返"的合并项；④（第二轮）**daemon 逐过程 calls/nanoseconds**（§17）：它是 `answer()` 一圈（解码→服务→编码）的进程内计时，比进程 CPU 更窄——两者之差就是后台线程（Save 完成、发布、WAL checkpoint）的 CPU，这个差本身就是结论。

`sample` 采样也试过（`state/sample-create-find.txt`，6 s/1 ms）：按叶子聚合后 **97.4% 的样本落在 `__accept`/`__recvfrom` 等阻塞等待**，剩下 sqlite 0.7%、pwrite 1.0%、内存拷贝 0.3%——它把所有阻塞线程都算进分母，**不能当 CPU 火焰图用**，故未据此下任何结论（保留原始文件备查）。

---

## 12. 代码根因对照（改动点在 #75–#78，不是本轮改动）

| 现象（本轮实测） | 对应代码位置（`b1802332b`） |
|---|---|
| 每新建文件 2 个 inode（真身 + `._` AppleDouble），每个都是完整 create 事务 | 服务端无 xattr 通道；`created` 走 `engine/crates/layerfs-nfs/src/change.rs:225`（create 前的 `existing()`）→ `mount-ports` mutation → overlay insert。客户端侧见 §5 |
| create 1000 文件 11,006 RPC / 235 ms daemon CPU（21 µs/RPC） | `changing.rs:144`（每次 WRITE 前多一次 `attributes`）、`change.rs:225/251`（`existing()` = lookup+add+forget）、`change.rs` create 后 `unlinked()` 顺序问题（CODE-SCAN §3.1） |
| rm 1000 文件 19,858 RPC（含 create 段）、daemon CPU 451 ms | `change.rs:367`（REMOVE 前 `existing()`）、`changing.rs:162/209`（父目录 before/after 各一次 getattr，SETATTR 在 `changing.rs:123` 亦同）、假 orphan 路径（CODE-SCAN §3.1） |
| git 每文件 28.7 RPC、19 次 RENAME、Link 102 | `change.rs:413/431`（RENAME 两个 `existing()`）、`changing.rs:218-225`（RENAME 四次 `attributes`：from/to 各 before+after） |
| write 64 MiB：121 ms daemon CPU / 127 ms 墙钟（95%） | `changing.rs:144`（每次 WRITE 前一次 extra getattr）+ `changing.rs:155`（失败时再一次）；`overlay/src/payload/stream.rs` 的 32 KiB cell 写入 + 2 MiB pager cache；`rpc.rs:121` 整包 `framed` 拷贝；`nfs.rs:252` FSINFO 128 KiB |
| find/mkdir tree 主要成本 = 1220 次 spawn + 2000 inode | `directory.rs:56-57`（READDIRPLUS 无属性，**本轮证明无惩罚**）；`directory.rs:113-115`（本批读完仍回 `eof=false`，每目录固定 2 次 READDIRPLUS：实测 222 = 110×2） |
| `stat 1000 files` 4.8 s | 与 NFS 无关（§6）；仅 create 段的 640 ms 是文件系统成本 |
| `rsize/wsize` 挂不上 | `export.rs:103`（请求）+ `nfs.rs:252` / `types.rs:26,28`（真正的夹具） |
| 挂载选项无法用环境钩子实验 | `application/filesystem.rs:52-66`（读变量）vs `layerfs-sandbox/src/local/create.rs:217`（`env_clear` 派生 daemon） |

---

## 13. 复现

```bash
export LAYERFS_HOME=~/LayerFS/tmp/lp74-run/home      # 私有 home（0700）
L=~/LayerFS/tmp/lp74-target/release/layerfs
$L store create lprun ; $L project init lprun/demo <seed>
$L branch fork lprun/demo agent main
$L machine update native --daemon ~/LayerFS/tmp/lp74-target/release/layerfs-daemon
$L sandbox create lprun/demo tests native
$L workspace mount tests agent --name w1          # → path

# 12 场景，两臂逐场景交替（脚本内的场景名即冻结脚本里的名字）
~/LayerFS/tmp/lp74-run/run-formal.sh r1 "create 1000 files" "stat 1000 files" "rm 1000 files" \
  "mkdir tree (10x10x10)" "find tree" "write 64 MiB" "copy 64 MiB" "read 64 MiB" \
  "pure read 64 MiB" "pure copy 64 MiB" "overwrite 64 MiB" "git init + commit 100 files"

# 干净窗口（RPC/daemon CPU 归到 timed 区）
python3 ~/LayerFS/tmp/lp74-run/replica.py --arm layerfs --base "$M" --out <out> \
  --daemon-pid "$(cat ~/LayerFS/tmp/lp74-run/state/daemon-pid)" --scenarios "<名单>"

# 表：把 jsonl 变成 markdown
python3 ~/LayerFS/tmp/lp74-run/summarize.py            # → state/tables.md
```

工具与数据全在 `~/LayerFS/tmp/lp74-run/`：`measure.py`（正式轮）、`replica.py`（干净窗口）、`fast.py`（FAST 子集）、`exec-overhead.py`（Exec 开销）、`manualopt.sh`（手工挂载选项）、`nfsproxy.py`（RPC 级取证）、`summarize.py`（出表）。

---

## 14. 现场状态（两轮收尾后，2026-11-07 12:40）

| 项 | 结果 |
|---|---|
| NFS 挂载 | `mount \| grep -c nfs` = **0**（daemon 自身的挂载与手工二次挂载都已卸载） |
| `layerfs-daemon`（本任务） | **无**。第一轮按 `lp74-run/home` 查为空；第二轮按 `lp74-run2/home` 查为空。机器上仍有 3 个既有 T3 daemon（pid 61445/62286/62798，属 T3 环境，未动） |
| RPC 代理 | 已退出（`pkill -f nfsproxy2.py`；12049 无监听）；手工挂载点 `/tmp/lp74mnt` 已卸载并删目录 |
| 临时 Store | 第一轮 `lprun` 已 `store remove`；第二轮 `lp74-run2/home`（含 `lprun`）与种子目录已删 |
| 临时诊断构建 | 三个文件已 `git checkout` 复原；`layerfs`/`layerfs-daemon` 已换回原件（sha256 与 §1 完全一致，见下表）；`~/LayerFS/layerfs/QUIET` 已删除 |
| 保留 | `~/LayerFS/wt/lp74`（`b1802332b`，`git status --short` 为空）、`~/LayerFS/tmp/lp74-target`（已恢复原二进制）、`~/LayerFS/tmp/lp74-bench`、`~/LayerFS/tmp/lp74-run`（2.8 MB）、`~/LayerFS/tmp/lp74-run2`（1.3 MB：计数快照、代理日志、补丁） |
| 磁盘 | 58 Gi 可用（87% 已用） |
| 产品代码 | 未改（worktree 干净）；未 commit / 未 push / 未发评论 |

二进制 sha256（第二轮前后对照，均来自本次实际执行）：

| 文件 | 测量前（= 第一轮原件） | 诊断版 | 收尾后（恢复） |
|---|---|---|---|
| `layerfs` | `3d6401…7407` | 未重编（全程不变） | `3d6401…7407` |
| `layerfs-daemon` | `f54b1d…03c9` | `6ab53d…7800`（计数器）/ `33b6f0…045c`（+deny） | `f54b1d…03c9` |

---

## 15. 给 #75–#78 的建议（两轮证据合并，按优先级排序）

1. **#75 的第一件事：决定 AppleDouble 用哪种服务端策略（§19.2 已把三条策略量完）。** 客户侧无解（`mount_nfs` 与 `nfs.conf` 都没有这个开关，未知选项还会被静默忽略）。现行“留内存”已把工作区 inode 从 2000 降回 1000；若改成“对 `._*` 直接回 `NFS3ERR_ACCES`”，1000 文件 create 从 641.5 降到 **453.8 ms（−29%）**、RPC 从 10,873 降到 **8,915（−18%）**、rm 从 440.1 降到 **376.4 ms（−14%）**，且工作区仍然干净（1002 inode）；代价是 FinderInfo/resource fork 立刻丢（留内存至少在本 export 生命周期内能读回）。**反向证据也拿到了**：关掉抑制就是 2003 inode + create 779.5 ms（+21%）+ rm 544.2 ms（+24%）。
2. **#75 的成本模型不要写“每个用户文件 2 个 inode”**（第一轮曾这么写，第二轮修正）：协议侧确实是 2 倍（2000 CREATE + 2000 WRITE），但工作区 inode 与 4 KiB 存储只有 1 份。单 op 微优化（去掉 `existing()`、`wcc` 的 before/after、假 orphan）仍成立，实测上限见 §17：CREATE 27.4 µs/次、REMOVE 43.3 µs/次、LOOKUP 7.9 µs/次。
3. **#76**：先用 `nordirplus` 对照在 #73 的 26.4.1 机器上复核 §7；若同样无差别，把优先级降到 `directory.rs:113-115` 的“每目录 2 次 READDIRPLUS（多一次纯 EOF 往返）”——§17 里 `find tree` 的 222 次 READDIRPLUS 共 3.1 ms（14.1 µs/次，每目录两次），它确实不是主项。**不要**把“补 READDIRPLUS 属性”当主攻。
4. **#77**：服务端窗口（FSINFO `rtmax/wtmax` + `WRITE_WINDOW` + 切块）仍是唯一能提 64 MiB 吞吐的方向，挂载选项无效；新增两条硬数据：①**WRITE 每调用 161.9–249.1 µs**，新建 249.1 µs vs 覆写 161.9 µs（覆写便宜 35%，因为少一次 create 链上的额外 getattr）；②**客户端从不要 stable 写**：714 次 WRITE 全部 `UNSTABLE`，`FILE_SYNC`/`DATA_SYNC` 与 `COMMIT` 计数都是 **0**，所以这条路径上不存在“服务端被迫 fsync”的成本，优化点全在每次 WRITE 的 cell 写入/拷贝与 RPC 次数。
5. **新增：#75/#77 的收益上限有一半在后台线程。** 1000 文件 create 的 daemon 进程 CPU 228.9 ms，而 `answer()` 内计时只 131.2 ms —— **43% 不在请求路径上**（rm 39%、git 46%）。只改 `change.rs`/`changing.rs` 最多拿到 57%，剩下要查 Save 完成与发布/WAL checkpoint 的时机。
6. **#78**：git 的高 RPC 是 RENAME 的 4 次 `attributes` + 2 次 `existing()`（每个 `.lock`/松散对象都走一遍），与 #75 同源，可合并开发流（与 CODE-SCAN §4.2 一致）。§17 里 git 场景逐过程：LOOKUP 1797（15.3 ms）、CREATE 569（14.5 ms）、WRITE 563（9.0 ms）、SETATTR 478（5.6 ms）、REMOVE 218（5.3 ms）、LINK 102（3.4 ms）、RENAME 19（1.9 ms，97.7 µs/次，单次最贵）。
7. **测量纪律**：本机噪声 ±10%，create ±20%；任何 <10% 的墙钟差都不算数。用 RPC 计数 + `nfsstat -m` 生效值做硬判据。涉及 daemon 侧 SQL/OwnerWork 的下一步，必须先把诊断行接上（要么给 `observe` 一个调用方，要么继续用 §20 的临时诊断构建）；逐过程计时已不再需要为此改代码。

---

## 16. 可直接贴到 `Ephemeral-AI-Lab/layerfs-project#74` 的评论草稿

> 本节已合入第二轮（LP74-SUPP）的补充测量：逐过程 daemon 耗时（§17）、64 MiB 冷读（§18）、AppleDouble 抑制实验（§19）。

> **#74 macOS 原生 NFS 耗时归因 — 实测数据（`b1802332b`，M2 / macOS 27.2 / sqlite disposable）**
>
> 单样本、两臂逐场景交替、同一把 bash 与 PATH；同一配置连跑 5 次标定噪声带 ±10%（create ±20%）。冻结脚本 `fs-bench.sh` pin `6358760a` 未改。RPC 计数用 `nfsstat -c` 前后差分（零噪声），daemon 侧耗时用 `proc_pid_rusage` 取进程 CPU ns（与 `ps` 核对一致）。**逐过程 calls/nanoseconds 已从 `Server::counters()` 取到**：用一个测完即复原的临时诊断构建落盘（3 个文件、107 行，二进制测完按 sha256 换回原件），12 场景全部覆盖；`OwnerWork`/`StatementWork` 仍取不到（`take_scope`/`run` 无调用方、daemon 以 `env_clear` 派生），故未编造。
>
> **12 场景（host APFS → LayerFS native，ms）**
>
> | 场景 | host | LayerFS | 倍数 | 净增 |
> |---|---:|---:|---:|---:|
> | create 1000 files | 69.6 | 670.1 | 9.63× | +600 |
> | stat 1000 files | 4265.8 | 4814.2 | 1.13× | +548 |
> | rm 1000 files | 101.2 | 1050.4 | 10.38× | +949 |
> | mkdir tree 10×10×10 | 1906.6 | 3076.1 | 1.61× | +1170 |
> | find tree | 1930.9 | 3129.6 | 1.62× | +1199 |
> | write 64 MiB | 23.8 | 125.2 | 5.26× | +101 |
> | copy 64 MiB | 134.1 | 246.5 | 1.84× | +112 |
> | read 64 MiB | 60.7 | 135.1 | 2.23× | +74 |
> | pure read 64 MiB | 10.8 | 11.3 | 1.05× | +1 |
> | pure copy 64 MiB | 41.3 | 117.4 | 2.84× | +76 |
> | overwrite 64 MiB | 20.3 | 69.8 | 3.44× | +50 |
> | git init + commit 100 files | 110.1 | 378.1 | 3.43× | +268 |
> | **合计** | **8675.2** | **13823.8** | **1.59×** | **+5149** |
>
> **干净窗口（timed 区独占；daemon CPU = daemon 进程 user+sys）**
>
> | 场景 | 墙钟 ms | daemon CPU ms | 客户端+协议 ms | NFSv3 RPC | 主要过程 |
> |---|---:|---:|---:|---:|---|
> | create 1000 | 639.9 | 235.1 | 404.8 | 11006 | Getattr 4001 · Lookup 2001 · **Create 2000** · Write 2000 · Setattr 1000 |
> | rm 1000 | 1065.7 | 451.0 | 614.7 | 19858 | Lookup 6849 · Getattr 5003 · Create 2000 · **Remove 2000** · Write 2000 |
> | find tree | 3269.8 | 216.1 | 3053.7 | 10560 | RdirPlus 222（110 目录×2）· Create 2110 · Getattr 3451 |
> | write 64 MiB | 127.0 | 120.9 | 6.1 | 526 | Write 513（512×128 KiB） |
> | git 100 files | 368.7 | 116.5 | 252.2 | 5737 | Lookup 1783 · Getattr 1481 · Create 569 · Remove 218 · Link 102 · Rename 19 |
>
> **六个结论**
>
> 1. **CREATE/REMOVE 翻倍来自 AppleDouble 侧写，不是重试；但它只让协议动作翻倍，不让工作区 inode 翻倍。** 用户态 TCP 代理解 XDR 后逐条可见：`LOOKUP f1 → CREATE f1 → LOOKUP ._f1 → CREATE ._f1 → WRITE ._f1`（4096 B），删除时 `REMOVE f1` 与 `REMOVE ._f1` 各一次。原因是 macOS 27.2 给新文件打 `com.apple.provenance` 而 NFSv3 无 xattr 通道；`nfsstat` 的 Retries 为 0。所以 1000 个用户文件在协议上是 **2000 CREATE + 2000 WRITE + 1000 SETATTR**，删除时 **2000 REMOVE**；但 `workspace status` 实测工作区只有 **1002 个 inode**——本构建的 export 已经把 `._*` 只养在 daemon 内存里（`apple_double.rs`）。关掉抑制才是 2003 inode、create 779.5 ms、rm 544.2 ms。
> 2. **`stat 1000 files` 不是文件系统场景。** 1000×`/usr/bin/stat` 在 APFS 4.19 s、在 NFS 挂载 4.30 s（**NFS 占 2.5%**）；`stat` 场景的 RPC 计数与 create 场景**一模一样**（11,006 / Getattr 4001）——1000 次 `stat` 一次 RPC 都没发，全命中 `actimeo=60` 属性缓存。Exec 侧同样干净：`workspace exec` 固定开销 ≈**11 ms/次**（CLI 3.3 ms + 控制往返 + `bash -c` 派生），**无 Seatbelt**（进程链是 `layerfs workspace exec → 目标进程`，1000 条命令经 exec 1582 ms vs 裸 shell 1620 ms）。
> 3. **`READDIRPLUS` 缺属性在这台客户端没有惩罚。** `nordirplus` 生效（Readdir 222 / RdirPlus 0）后 `find tree` 的 Lookup 仍 2222、总 RPC 10552（默认 10556）、墙钟在噪声内；`find tree` 只比 `mkdir tree` 多 63 ms。→ #76 的"补 READDIRPLUS 属性"前提需要先在 26.4.1 上复现，否则会优化掉不存在的成本；真正可量化的是每目录固定 2 次 READDIRPLUS（多一次纯 EOF 往返，222 = 110×2）。
> 4. **`rsize/wsize` 提不上去，因为服务端 FSINFO 夹在 128 KiB。** 手工二次挂载请求 `rsize=wsize=1048576`，`nfsstat -m` 显示 Original 接受、**Current 被夹回 131072**，64 MiB 写的 `Write` 仍是 513。→ #77 必须改 `nfs.rs:252` 的 FSINFO + `types.rs:26,28` 的窗口常量，挂载选项无效。另：daemon CPU 已占 write 64 MiB 墙钟的 **95%**（120.9/127.0），优化面向减少 RPC 次数与 cell 写入/拷贝。
>
> 5. **逐过程 daemon 耗时（`Server::counters()`，12 场景全覆盖）。** 全 12 个 timed 窗口合计：**WRITE 55.6%、CREATE 20.0%、LOOKUP 9.2%、REMOVE 6.5%**（只算元数据场景：CREATE 37.0%、WRITE 18.0%、LOOKUP 17.0%）。单价：WRITE **161.9 µs（覆写）–249.1 µs（新建）**、CREATE 27.4 µs、REMOVE 43.3 µs、LOOKUP 7.9 µs、SETATTR 8.3 µs、MKDIR 39.3 µs、RENAME 97.7 µs。更重要的是：**daemon 进程 CPU 在元数据场景有 39–59% 不在请求路径上**（写路径只有 8%）——create 1000 的 daemon CPU 228.9 ms vs `answer()` 内计时 131.2 ms（差 97.7 ms，43%），rm 39%、git 46%、find tree 59%。所以只改 `change.rs`/`changing.rs` 最多拿到元数据场景的一半，剩下的在 Save 完成与发布/WAL checkpoint 的时机上。
> 6. **64 MiB 真读路径（客户端页缓存已清）。** 写 64 MiB 并 commit → unmount + remount（新 export、客户端新 vnode）→ 读：**512 次 READ × 131072 B = 64.0 MiB**，偏移连续；墙钟 **52.0 / 61.4 / 59.6 ms**（3 样本），daemon 进程 CPU 27.5 / 38.3 / 38.7 ms（≈ 0.43–0.60 ms/MiB，单次 READ 约 54–76 µs CPU），剩下 22–31 ms 在客户端（readahead、vnode 页入、512 次往返）；同一文件紧接着再读 = **0 RPC**（27.5–30.5 ms 全是 shell + `cat`）。所以 `pure read 64 MiB 1.05×` 这个“假零”到此解释完：冷读真实代价 52–61 ms，而冻结脚本的 `read 64 MiB` 形状永远读自己刚写的文件。
>
> **AppleDouble 抑制：客户端无解，服务端三选一（1000 个用户文件，各 3–4 次）**
>
> | 服务端策略 | 工作区 inode | create 墙钟 | daemon CPU | NFSv3 RPC | rm 墙钟 |
> |---|---:|---:|---:|---:|---:|
> | 现行：`._*` 只在 export 内存（`refuse_apple_double`） | 1002 | 641.5 ms | 228.6 ms | 10,873 | 440.1 ms |
> | 改成直接回 `NFS3ERR_ACCES` | 1002 | **453.8 ms** | 211.9 ms | **8,915** | **376.4 ms** |
> | 关掉抑制（`._*` 落成真 inode） | 2003 | 779.5 ms | 327.7 ms | 11,613 | 544.2 ms |
>
> 客户端选项一条都没有：`mount_nfs(8)`、`mount(8)`、`nfs.conf(5)` 全文没有 AppleDouble/xattr 开关；`-o noappledouble`、`-o noapplexattr`、`-o appledouble=off`、`-o applexattr=off` 与 `-o entirelynonsense`（对照）全部“挂载成功”——因为 **mount_nfs 静默忽略不认识的选项**，20 个新文件仍是 40 CREATE + 40 WRITE（一个都没变）。唯一改变 `._` 生命周期的是 `locallocks`：去掉它变成每文件 3 CREATE + 2 REMOVE、RPC +36%。服务端回 ACCES 时客户端**没有重试风暴**：`CREATE ._f1 → ACCES`、`LOOKUP ._f1 → NOENT`、`CREATE ._f1 → ACCES`，然后正常写文件数据；每文件 2 次被拒，shell 无报错。
>
> **挂载选项对照**（用同一 export 的手工二次挂载，`nfsstat -m` 双行验证生效）：`actimeo=0` → create RPC 62,925（5.7×）、墙钟 2013 ms（2.8×）；`actimeo=3600` 相对 60 **零收益**；去掉 `locallocks` → 每文件 3 CREATE + 2 REMOVE、RPC +36%、墙钟 2.4×（**默认串里的 `locallocks` 是承重的，别删**）；`nfc` 无影响。
>
> **另一个副产品**：`LAYERFS_NFS_MOUNT` 等钩子在本构建**不可达**——`filesystem.rs:52-66` 读变量，但 daemon 由 CLI 以 `env_clear()` 派生（`layerfs-sandbox/src/local/create.rs:217`）。实测把钩子设成 `/usr/bin/false {port} {dir}` 挂载仍成功、`nfsstat -m` 仍是默认串。所以"免重编改挂载参数"这条路目前不存在（本报告的选项实验改用对同一 export 的手工二次挂载完成）。
>
> **FAST 基线（供 #75–#79 回归）**：FAST-A 6 行 5307.4 ms / 74,756 RPC；FAST-B 8 行 5653.9 ms / 76,130 RPC（host 对应 2218.1 / 2269.4 ms）。定义与 PREP §7 一致。
>
> 数据与脚本：`~/LayerFS/tmp/lp74-run/`（第一轮）、`~/LayerFS/tmp/lp74-run2/`（第二轮：`proc12/` 逐过程快照与汇总表、`cold2/` 冷读窗口、`adarms*/` 三条服务端策略、`proxy3/` 代理日志、`appledouble/` 选项矩阵、`DIAGNOSTIC.patch`）。未改产品代码（临时诊断构建已复原），未提交。

---

## 17. 逐过程 daemon 耗时（LP74-SUPP 补齐 #74 第 3 项）

### 17.1 方法：窗口标记 + `Server::counters()` 落盘

第一轮 §11 的结论是 `Server::counters()` 只在进程内、daemon 只把 calls 求和。第二轮用一个**临时诊断构建**把它取出来（补丁见 §20）：`Server::start` 里起一个 10 ms 轮询线程，读 `/tmp/lp74-marker`；内容一变，就把当前 export 的 `counters().snapshot()`（22 个 NFS 过程 + 6 个 MOUNT 过程的 `calls` 与 `nanoseconds`，单位 ns，计时范围是 `answer()` 从解码到编码的一圈）追加一行到 `/tmp/lp74-proc-counters.jsonl`。

一个 export 一套计数器（每次 `workspace mount` 从 0 开始），所以一个窗口 = 写 `<stem>.start` 标记 → 跑命令 → 静置 0.4 s → 写 `<stem>.end` 标记，再把两次快照逐过程相减。窗口切法与第一轮 replica 轮一致（prep / timed / teardown），全部窗口属于同一次挂载。12 个场景共 27 个窗口（12 timed + 12 teardown + 3 prep）→ 54 个标记；原始快照在 `lp74-run2/proc12/proc-counters.jsonl`（本轮累计 156 行，含冷读与三条策略的标记）。

**两侧自校验**：daemon 侧 calls 合计与客户端 `nfsstat -c` 合计在 12 个 timed 窗口里 6 个完全相等，其余 6 个差 3–6 次（≤0.06%：create +3、rm +6、mkdir tree +3、copy +4、read +5、git +4，均为客户端多于 daemon）。daemon 只计它真正服务过的调用，所以这几下最可能是客户端自己答复的（名字/属性/statfs 缓存，属推断，未单独取证），不影响结论。

### 17.2 十二场景（timed 窗口）

`daemon 内计时` = 该窗口所有过程 nanoseconds 之和；`覆盖墙钟` = 它 / 墙钟。

| 场景 | 墙钟 ms | daemon CPU ms | daemon 内计时 ms | 覆盖墙钟 | client RPC | daemon calls |
|---|---:|---:|---:|---:|---:|---:|
| create 1000 files | 646.7 | 228.9 | 131.2 | 20% | 11,006 | 11,003 |
| stat 1000 files | 4905.6 | 245.0 | 135.9 | 3% | 11,007 | 11,007 |
| rm 1000 files | 1077.0 | 454.0 | 276.0 | 26% | 19,989 | 19,983 |
| mkdir tree (10x10x10) | 3411.4 | 231.0 | 94.9 | 3% | 10,222 | 10,219 |
| find tree | 3451.6 | 230.9 | 94.2 | 3% | 10,556 | 10,556 |
| write 64 MiB | 155.2 | 139.1 | 128.2 | **83%** | 530 | 530 |
| copy 64 MiB | 274.9 | 251.1 | 230.3 | **84%** | 1,083 | 1,079 |
| read 64 MiB | 151.2 | 125.7 | 115.2 | **76%** | 531 | 526 |
| pure read 64 MiB | 33.3 | 0.5 | 0.1 | 0% | 2 | 2 |
| pure copy 64 MiB | 158.6 | 138.8 | 126.8 | **80%** | 555 | 555 |
| overwrite 64 MiB | 109.5 | 93.6 | 83.0 | **76%** | 515 | 515 |
| git init + commit 100 files | 544.7 | 121.4 | 65.1 | 12% | 5,759 | 5,755 |

（本表墙钟与第一轮 replica 轮差 −1% 到 +48%（git +48%：368.7 → 544.7 ms；overwrite +32%；write +22%），说明这一批落在更忙的负载段。所以本节的结论只建立在**逐过程结构与单价**上，不靠跨轮墙钟比较。）

### 17.3 关键场景逐过程

**create 1000 files**（11,003 calls，daemon 内 131.2 ms）

| procedure | calls | total ms | avg µs | 占 daemon 时间 |
|---|---:|---:|---:|---:|
| CREATE | 2000 | 54.5 | 27.2 | 42% |
| WRITE | 2000 | 42.8 | 21.4 | 33% |
| LOOKUP | 2000 | 16.0 | 8.0 | 12% |
| GETATTR | 4001 | 9.8 | 2.4 | 7% |
| SETATTR | 1000 | 8.2 | 8.2 | 6% |

**rm 1000 files**（19,983 calls，daemon 内 276.0 ms）

| procedure | calls | total ms | avg µs | 占 daemon 时间 |
|---|---:|---:|---:|---:|
| REMOVE | 2000 | 90.9 | 45.4 | 33% |
| LOOKUP | 6974 | 56.9 | 8.2 | 21% |
| CREATE | 2000 | 55.8 | 27.9 | 20% |
| WRITE | 2000 | 44.3 | 22.2 | 16% |
| GETATTR | 5004 | 14.4 | 2.9 | 5% |
| SETATTR | 1000 | 8.4 | 8.4 | 3% |
| ACCESS | 1002 | 4.5 | 4.5 | 2% |
| READDIRPLUS | 2 | 0.8 | 402.4 | 0% |

**find tree**（10,556 calls，daemon 内 94.2 ms）

| procedure | calls | total ms | avg µs | 占 daemon 时间 |
|---|---:|---:|---:|---:|
| CREATE | 2110 | 56.0 | 26.5 | 59% |
| LOOKUP | 2222 | 15.0 | 6.8 | 16% |
| SETATTR | 1110 | 7.9 | 7.1 | 8% |
| GETATTR | 3449 | 5.3 | 1.5 | 6% |
| MKDIR | 110 | 4.2 | 38.2 | 4% |
| READDIRPLUS | 222 | 3.1 | 14.1 | 3% |
| WRITE | 1110 | 1.4 | 1.2 | 1% |
| ACCESS | 222 | 1.3 | 5.9 | 1% |

**git init + commit 100 files**（5,755 calls，daemon 内 65.1 ms）

| procedure | calls | total ms | avg µs | 占 daemon 时间 |
|---|---:|---:|---:|---:|
| LOOKUP | 1797 | 15.3 | 8.5 | 23% |
| CREATE | 569 | 14.5 | 25.5 | 22% |
| WRITE | 563 | 9.0 | 16.0 | 14% |
| SETATTR | 478 | 5.6 | 11.8 | 9% |
| REMOVE | 218 | 5.3 | 24.1 | 8% |
| MKDIR | 96 | 3.9 | 40.2 | 6% |
| GETATTR | 1487 | 3.8 | 2.6 | 6% |
| LINK | 102 | 3.4 | 33.8 | 5% |
| ACCESS | 413 | 2.0 | 4.8 | 3% |
| RENAME | 19 | 1.9 | **97.7** | 3% |

**64 MiB 五场景**（daemon 内计时 76–84% 都落在 WRITE 上）

| 场景 | WRITE calls | WRITE total ms | WRITE avg µs | READ calls | READ avg µs |
|---|---:|---:|---:|---:|---:|
| write 64 MiB | 513 | 127.8 | 249.1 | 0 | — |
| copy 64 MiB | 1029 | 229.4 | 222.9 | 0 | — |
| read 64 MiB | 513 | 114.7 | 223.6 | **0** | — |
| pure copy 64 MiB | 516 | 126.1 | 244.3 | 0 | — |
| overwrite 64 MiB | 512 | 82.9 | **161.9** | 0 | — |

`read 64 MiB` 的 READ=0 不是丢数据，是客户端读自己刚写的 vnode（页缓存），真读路径见 §18。

### 17.4 三个结论

1. **元数据类的单价**：CREATE 27.4 µs/次、REMOVE 43.3 µs/次、LOOKUP 7.9 µs/次、SETATTR 8.3 µs/次、MKDIR 39.3 µs/次、ACCESS 5.2 µs/次、RENAME **97.7 µs/次**（单次最贵，一条 RENAME 要做 from/to 各 before+after 四次 `attributes`，见 §12）。这组数字是 #75/#78 能做到的“单 op 上限”：这组数字给出了 #75/#78 单 op 优化的天花板：把每个 op 的单价砍一半，1000 文件 create 的内计时从 131.2 降到 65.6 ms，而门外那 97.7 ms 后台 CPU 不变，所以进程 CPU 只从 228.9 降到 163.0 ms（−29%）。
2. **数据路径**：WRITE 单价 161.9–249.1 µs，新建比覆写贵 35%（249.1 vs 161.9 µs；按 §12 的代码对照，新建那次 WRITE 前还要走 CREATE 链上的 `attributes`/`existing()`，这是推断，本轮没有把 CREATE 与 WRITE 的归因拆开）；128 KiB 一个 RPC 下，64 MiB 写就是 512 次 × ~249 µs ≈ 128 ms。
3. **daemon CPU 有一半在请求路径之外**（本次最有价值的新事实）：

| 场景 | daemon CPU ms | `answer()` 内计时 ms | 差额（后台线程）ms | 后台占比 |
|---|---:|---:|---:|---:|
| create 1000 files | 228.9 | 131.2 | **97.7** | **43%** |
| rm 1000 files | 454.0 | 276.0 | **178.0** | **39%** |
| git init + commit 100 | 121.4 | 65.1 | **56.3** | **46%** |
| write 64 MiB | 139.1 | 128.2 | 10.9 | 8% |
| find tree | 230.9 | 94.2 | 136.7 | 59% |

（差额 = 进程 CPU 减去被计时的调用时间。它包含 Save 完成、发布、WAL checkpoint 等后台线程，也包含未被计时覆盖的进程内开销；不是“纯等待”。因此它是“不在 `answer()` 里花的 CPU”的上界，方向明确，拆分到具体线程仍需 `StatementWork`/`OwnerWork`，那仍是 NOT_RUN。）

全 12 个 timed 窗口合计 1481.0 ms daemon 内计时，分布为 **WRITE 55.6% · CREATE 20.0% · LOOKUP 9.2% · REMOVE 6.5% · GETATTR 3.3% · SETATTR 3.2% · 其余 2.2%**；只看 7 个元数据场景则是 **CREATE 37.0% · WRITE 18.0% · LOOKUP 17.0% · REMOVE 12.1% · GETATTR 6.1% · SETATTR 5.9%**。

### 17.5 WRITE 的 stable 标志与每调用字节数（#77 明确要求）

daemon 计数器只记 calls/ns，不区分 stable。这一项用用户态代理逐条解 XDR 的 WRITE 参数（`offset`、`count`、`stable`）得到，窗口是一次手工二次挂载上的 `dd 64 MiB` + 100 个文件 + `rm`（`lp74-run2/proxy3/rpcW.jsonl`，2567 次调用，`TCP_NODELAY` 已开）：

| stable | calls | 字节数 | 典型 size | 含义 |
|---|---:|---:|---:|---|
| `UNSTABLE` | **714（100%）** | 67,526,948 | 512×131072 + 102×4096 + 99×2–4 B | 先写不落盘，靠 COMMIT 才稳 |
| `DATA_SYNC` | **0** | 0 | — | — |
| `FILE_SYNC` | **0** | 0 | — | — |
| `COMMIT`（过程计数） | **0** | — | — | 客户端从未要过 COMMIT，冷读窗口也是 0 |

逐档拆分：

- **512 次 × 131,072 B**（= 64 MiB 的 `dd`）——每调用正好是 wsize（= FSINFO 的 `wtmax`，§8）；
- **102 次 × 4,096 B**——`._` AppleDouble 伴生文件（§19）；
- **99 次 × 2–4 B**——100 个文件的 `echo` 内容。

结论（#77 直接可用）：

1. **这台客户端在原生挂载上一律发 `UNSTABLE` 写，从不发 `FILE_SYNC`/`DATA_SYNC`，也从不发 `COMMIT`**。所以“服务端被迫 fsync”不是成本项；disposable 档下的写路径没有稳定写开销。
2. **每调用字节数完全由 wsize/`wtmax` 决定**（128 KiB），客户端不会自己变大——再次印证 §8：#77 必须改 FSINFO + 窗口常量，否则 WRITE 次数固定为 512/64 MiB。
3. 反过来，如果 #77 以后考虑“让客户端发 FILE_SYNC 以便简化实现”，以上数据说明那是**新增**成本，不是现状。

### 17.6 局限

- timed 窗口单样本（第一轮已标定噪声带 ±10%/create ±20%）；逐过程 calls 是确定量，ns 有噪声，故只对 ≥2× 的差异和“单价量级”下结论。
- `nanoseconds` 是 `Instant::elapsed()` 的墙钟差，不是 CPU 时间；在 16 线程客户端的渲染下，高并发场景的单价包含排队。
- 计数器在 `answer()` 返回后累加，所以“回包已发出但客户端还没收到”的时间不在里面。

---

## 18. 64 MiB 真读路径（冷读，LP74-SUPP 补齐 #74 第 2 项）

### 18.1 为什么第一轮读不到

冻结脚本的 `read 64 MiB` 是 `dd 64 MiB` + `cat` 同一个文件；`cat` 命中的是客户端刚写完的 vnode 页缓存，所以 READ RPC = 0（第一轮 §4.3 的观察）。`pure read 64 MiB` 的 prep 也在同一个挂载里写文件，同样命中。要真读，必须让客户端丢掉那个 vnode。

### 18.2 方法：写入 → commit → unmount + remount → 读

1. 在挂载里的 `cold/` 写 64 MiB，`workspace commit`（数据进 Store，之后不再由任何客户端 vnode 持有）；
2. `workspace unmount` + `workspace mount`：daemon 起一个新 export（计数器也归零），客户端拿到新 vnode；
3. 立刻读：`pure read 64 MiB` = `cat big > /dev/null`；`read 64 MiB（冷目标）` = `dd if=/dev/zero of=big2 bs=1M count=64` + `cat big`（保持冻结脚本“写一个 + 读一个”的计时形状，但读的是冷文件）；
4. 每个新挂载只做一个冷窗口，紧接着做一次同命令的热窗口作对照；每个形态 2 个样本（`pure read` 共 3 个样本，含一次预跑）。

样本：`lp74-run2/cold2/windows.jsonl`（+ `cold1/`）、`cold2/remounts.json`（每次 unmount/mount 的返回）。

### 18.3 结果

| 窗口 | 墙钟 ms | daemon CPU ms | NFSv3 RPC | Read | Write | daemon READ ms | READ avg µs |
|---|---:|---:|---:|---:|---:|---:|---:|
| pure read 64 MiB（冷，样本 1） | 52.0 | 27.5 | 514 | **512** | 0 | 11.1 | 21.7 |
| pure read 64 MiB（冷，样本 2） | 61.4 | 38.7 | 517 | **512** | 0 | 14.3 | 27.9 |
| pure read 64 MiB（冷，样本 3） | 59.6 | 38.3 | 517 | **512** | 0 | 14.7 | 28.8 |
| pure read 64 MiB（随即再读，热） | 30.5 / 27.5 | 0.2 | **0** | 0 | 0 | 0 | — |
| read 64 MiB（冷目标） | 175.5 / 176.4 | 152.3 / 151.0 | 1040 | **512** | 513 | 10.8 / 11.0 | 21.1 / 21.5 |
| read 64 MiB（同形状，热目标） | 178.6 / 155.0 | 143.3 / 128.8 | 524 | 0 | 513 | 0 | — |

代理逐条核对（`lp74-run2/proxy3/rpcR.jsonl`，手工二次挂载 + 用户态代理）：**READ 512 次，每次 count = 131072 字节，偏移连续，合计 67,108,864 = 64.0 MiB**，与 512 × 128 KiB 完全对应；整个读窗口没有一次 COMMIT。

### 18.4 结论

1. **真读路径已经量化：64 MiB 冷读 = 512 次 128 KiB READ，墙钟 52.0 / 61.4 / 59.6 ms，daemon 进程 CPU 27.5 / 38.3 / 38.7 ms（≈ 0.43–0.60 ms/MiB）。**
2. **服务端侧净 CPU 占冷读墙钟的 53–65%，但不是“READ 过程慢”。** daemon 内 READ 计时合计只 11.1–14.7 ms（2.4–2.9 ms per MiB）——它是**墙钟口径且 16 路 readahead 并发重叠**，所以按 512 次摊平得到 21.7–28.8 µs/次不可当 CPU 用；用进程 CPU 除，单次 READ 约 54–76 µs。剩下 22–31 ms 在客户端（readahead、vnode 页入、512 次往返）。所以 #77 若只想“让读更快”，改服务端 READ 的天花板很低；收益更可能在 rsize/窗口（减少 RPC 次数）与客户端 readahead 的配合上。
3. **冷热差 = 21.5–34 ms**（52.0–61.4 vs 27.5–30.5 ms 的“0 RPC”基线，两边都含同样的 shell + `cat` 开销），即 64 MiB 真读的净成本约 **0.35–0.53 ms/MiB**。host APFS 的对应数字（§3 `pure read 64 MiB` 10.8 ms）是热缓存读，可比性有限；APFS 冷读需要 root 丢页缓存，本报告未做（NOT_RUN，原因：无 root）。
4. 代理日志里每次 READ 的**服务端服务时间**约 2.4 ms（p50），远高于 daemon 计数器的 21.7–28.8 µs —— 这是“Python 代理单线程转发 + 16 深度 readahead 串行化”的产物，不能当服务端耗时用；本轮代理只用于形状（stable 标志、字节数、偏移连续性）。同一原因，代理路径上的 WRITE 单价也是失真的（`nfsproxy2.py` 未设 `TCP_NODELAY` 前每调用 12 ms，设置后回落到正常量级）。

---

## 19. AppleDouble（`._`）抑制实验（LP74-SUPP 补齐 #74 第 1 项的前置问题）

### 19.1 客户端：没有任何可用开关

| 检查 | 结果 |
|---|---|
| `man mount_nfs`（macOS 27.2） | 全文无 apple/xattr/AppleDouble 相关选项（`grep -i "apple\|xattr\|extattr"` 0 命中） |
| `man mount` / `man nfs.conf` | 无；`nfs.conf(5)` 只有 `nfs.client.*` / `nfs.lockd.*` / `nfs.server.*`，与 `._` 无关 |
| 未知选项怎么处理 | **静默忽略**：`-o entirelynonsense` 也挂载成功、无警告、`nfsstat -m` 里也看不到它 |
| 7 个变体各 20 个新文件（同一天、同一 export，`lp74-run2/appledouble/variants.json`） | base / `+noappledouble` / `+noapplexattr` / `+appledouble=off` / `+applexattr=off` / `+entirelynonsense` / `+soft`：**全部 222 RPC（对照 223）、CREATE 40、WRITE 40、REMOVE 0、目录里可见 20 个** |

**结论：客户端没有抑制 AppleDouble 的开关，任何“加个挂载参数”的方案都不成立。** 只有 `locallocks` 会改变 `._` 的生命周期（不是抑制，是换形）：

| 变体 | RPC/20 文件 | CREATE | WRITE | REMOVE | SETATTR | 说明 |
|---|---:|---:|---:|---:|---:|---|
| 带 `locallocks`（默认串） | 222 | 40 | 40 | 0 | 20 | `._` 写完保留 |
| 去掉 `locallocks` | 302 | 60 | 20 | 40 | 0 | `._` 建了删两次，写完即弃；RPC +36% |
| 只加 `actimeo=60`、不加 `locallocks` | 302 | 60 | 20 | 40 | 0 | 同上，说明开关是 `locallocks`，不是 `actimeo` |
| 去掉 `noatime`（保留 `locallocks`） | 222 | 40 | 40 | 0 | 20 | 无影响 |

（`lp74-run2/appledouble/opt-isolation.txt`；这也回头解释了 §9 表格里“去掉 locallocks → 3 CREATE + 2 REMOVE、RPC +36%”的机制：那条差异就是 `._` 生命周期变了。）

### 19.2 服务端：三条策略实测（各 3–4 次，同一 export，1000 个用户文件）

| 策略 | 工作区 inode | create 墙钟 | daemon CPU | NFSv3 RPC | CREATE calls | rm 墙钟 | rm RPC |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A 现行**：`._*` 只在 export 内存（`refuse_apple_double=true`） | 1002 | 641.5（623.1–652.3） | 228.6 | 10,873 | 2000 | 440.1 | 8,910 |
| **B**：对 `._*` 直接回 `NFS3ERR_ACCES` | 1002 | **453.8（447.9–460.1）** | 211.9 | **8,915** | 3000 | **376.4** | 7,666 |
| **C 对照**：关掉抑制（`._*` 落成真 inode） | 2003 | 779.5（726.3–897.5） | 327.7 | 11,613 | 2000 | 544.2 | 9,621 |

原始：`lp74-run2/adarms*/{suppress,deny,real}.json`（4/3/4 次）。

客户端对 ACCES 的反应（代理逐条，`proxy3/rpcD.jsonl`）：

```
LOOKUP  f1     NOENT
CREATE  f1     OK
LOOKUP  ._f1   NOENT
GETATTR        OK
CREATE  ._f1   ACCES      ← 服务端拒绝
LOOKUP  ._f1   NOENT
CREATE  ._f1   ACCES      ← 重试一次，再被拒
WRITE   f1     OK         ← 文件本身正常写入
```

每文件 2 次被拒、**没有重试风暴**，shell 没有任何报错（xattr 写失败对用户不可见），10 个文件 + 1 个目录共 21 次 ACCES。

### 19.3 结论与边界

1. **客户端侧无解，服务端有三种策略**，成本差得很实在：B 比 A 快 29%（create）、RPC 少 18%、rm 快 14%；C（不抑制）比 A 再贵 21%（create）/24%（rm），且工作区 inode 翻倍、每个 `._` 占 4096 字节。
2. **“每个用户文件 2 个 inode”只在策略 C 下成立**；A/B 下工作区永远是 1000 个 inode。第一轮 §5 的那句话按 A 的实际情况应改为“协议动作翻倍、存储不翻倍”。
3. **B 的代价**：`._` 里的 FinderInfo / resource fork 立刻丢（A 至少在本 export 生命周期内还能读回）。若 #75 选择 B，需要在文档里写明“xattr 写入会失败，但文件数据不受影响”。
4. **A 有一个未被本轮测到的边界（源码事实，未实测）**：`apple_double.rs` 的 `HELD = 4096` 个伴生文件 / `TOTAL_BYTES = 64 MiB`；一个 export 内超过 4096 个 `._` 时，CREATE 会转成 `NFS3ERR_ACCES`，即自动退化成 B。1000 文件的测试在阈值内，所以 A 的“留内存”路径被完整走到；10000 文件的工作负载会看到 A→B 的混合行为。这是读源码得到的事实，本轮没有实测，写在这里是为了不让下一个人踩到。
5. **每文件 4096 字节**：代理日志里 `._` 的 WRITE 一律是 `count=4096`（`proxy3/rpcW.jsonl`：102 次 4096 B 的 UNSTABLE 写，对应 100 个文件与 1 个目录）；C 策略下这些字节会真的进 Store。

---

## 20. 临时诊断构建与复现

### 20.1 补丁（3 个文件，107 行，`lp74-run2/DIAGNOSTIC.patch`，sha256 `087f7d70…b9726`）

| 文件 | 改动 | 用途 |
|---|---|---|
| `engine/crates/layerfs-nfs/src/server.rs` | `Server::start` 里起 `lp74-counters` 线程，10 ms 轮询 `/tmp/lp74-marker`，变化即把 `counters().snapshot()` 追加到 `/tmp/lp74-proc-counters.jsonl`（含 port、epoch_ms） | §17、§18 |
| `engine/crates/layerfs-daemon/src/control/export.rs` | `refuse_apple_double` 在读 `ExportConfig` 时再与“`/tmp/lp74-appledouble-real` 不存在”相与 | §19 策略 C |
| `engine/crates/layerfs-nfs/src/change.rs` | `/tmp/lp74-appledouble-deny` 存在时，`._*` 的 CREATE 直接回 `Status::Access` | §19 策略 B |

三处都带 `TEMPORARY (LP74-SUPP measurement only)` 注释，测完 `git checkout --` 复原（`git status --short` 为空，HEAD 仍 `b1802332b`）。**没有进入任何分支，也没有 commit。**

### 20.2 构建与还原

```bash
cd ~/LayerFS/wt/lp74
touch ~/LayerFS/layerfs/QUIET            # 暂停 linux bundle 的一方
. ~/.cargo/env
CARGO_TARGET_DIR=$HOME/LayerFS/tmp/lp74-target CARGO_PROFILE_RELEASE_STRIP=none \
  cargo +1.85.1 build --release --locked -j 2 -p layerfs-daemon    # 首次 33 s，第二次 7 s
rm -f ~/LayerFS/layerfs/QUIET
```

daemon sha256：诊断版 `6ab53d02…7800`（计数器）/ `33b6f02b…045c`（+deny）；`layerfs` CLI 全程未重编（`3d640147…7407`）。收尾把两个二进制从备份换回，`sha256` 与 §1 完全一致（`f54b1d41…03c9`），备份目录已删。

### 20.3 复现命令

```bash
RUN=~/LayerFS/tmp/lp74-run2   # 本轮脚本：setup.sh procwin.py coldread.py
                              #             appledouble-arms.py appledouble-options.py
                              #             nfsproxy2.py summarize/summ2
L=~/LayerFS/tmp/lp74-target/release/layerfs
$RUN/setup.sh                                     # home + store + project + sandbox
$L workspace mount tests agent --name w1          # → path（记下 daemon pid 与 export 端口）
python3 $RUN/procwin.py     --mount "$M" --out proc12 --daemon-pid $PID --port $PORT --scenarios "..."
python3 $RUN/coldread.py    --home $HOME --cli $L --mount "$M" --workspace tests:w1 --out cold2 --samples 2
python3 $RUN/appledouble-arms.py    --arm {suppress|deny|real} --home … --cli $L --daemon-pid $PID --out adarms
python3 $RUN/appledouble-options.py <export-port>
```

汇总表由 `python3 summ2.py proc12/windows.jsonl > proc12/tables.md` 生成（本报告 §17 的表格出自它）。
