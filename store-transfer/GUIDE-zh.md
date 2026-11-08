# SQLite Store 跨机器 push / pull 设置与操作指南（LayerFS 2.0.0）

> 适用：一个 LayerFS home 里用 sqlite Store 的项目，把整个 Store（文件 + 历史）在
> `native` 与另一台机器（Docker / Lima / Apple Container）之间搬来搬去。
> 依据：pin `8f0ff7b2b`（bundle `2e98e17e…`）的源码与 LP08-S3 本机实测
> （2026-11-07，macOS 27.2 / Mac14,2 / M2 / 16 GiB；Docker 29.9.3 + colima 0.10.3；
> `limactl` 2.2.1；`container` 1.6.1）。
>
> 记号：**加粗的字段值**在本次复现中逐字核对；`<…>` 是随环境变化的值
> （端口、pid、时间戳、剩余空间、sha256）。

---

## 1. 这套操作做什么、不做什么

- 做：`store push` 把 **native 上的一个 sqlite Store 文件**（连同它的 `-wal`/`-shm`
  状态）搬到一台机器上；`store pull` 把它搬回 native。搬的是整个 Store 文件，
  所以项目、分支、提交历史、`.git` 之类“项目内的东西”都跟着走。
- 做：`store remove` 删 Store（两侧副本、两块记录）。
- 不做：PostgreSQL Store 不搬（`InvalidInput: … is a PostgreSQL database; it does not move`）。
- 不做：两台非 native 机器之间没有直连。要 `docker → lima`，先 `pull` 回 native 再 `push`。
- 不做：`firecracker`、`ssh`、`microsandbox` 平台已在 LayerFS 2.0 移除（owner 2026-11-08），
  `machine create` 会 `Unsupported`（``platform `<name>` was removed in LayerFS 2.0``），不需要试。

一次 push / pull 固定七阶段，顺序不变：

```text
check → snapshot → send → verify → install → record → retire
```

`check` 之前不写任何状态；`install` 之后到 `record` 之间是“两份副本都在”的窗口，
被记为 uncertain；`record` 成功即所有权切到目标机；`retire` 删源副本。

---

## 2. 前置条件

| 项 | 要求 | 核对命令 |
| --- | --- | --- |
| LayerFS CLI | 2.0.0 release（`layerfs --version`） | `layerfs --version` |
| home | 一个私有目录（0700），可空可新建；`LAYERFS_HOME` 指过去 | `ls -ld "$LAYERFS_HOME"` |
| native daemon | 要在 native 上开 Sandbox/挂载才需要：`machine update native --daemon <…>/layerfs-daemon` | `layerfs machine list` |
| Docker | `colima start`（或 Docker Desktop）后 socket 可写 | `docker ps` |
| Lima | `limactl` 在 PATH；首次 `machine create` 会准备 Ubuntu 镜像（约 617 MB） | `limactl --version` |
| Apple Container | `container` CLI 1.6.1，apiserver 在跑 | `container system status` |
| 磁盘 | 目标机剩余 ≥ Store 字节 + `max(1 GiB, 10%)`；native 侧同理（pull 时） | `df -h /` / `layerfs machine status <m>` |

机器/Store 记录都在 `LAYERFS_HOME` 里，**换 home 等于换一整套机器**（VM 名带 home id）。

---

## 3. 复现用的固定环境

下面每一块的命令就是本指南的“实跑命令”，`LP08-S3` 的复现脚本
（`store-transfer/guide_repro.py`）把本文件里所有 ```bash 代码块
**按顺序、逐字**执行一次。所以请不要把多行拆开、不要改顺序。

```bash
export LAYERFS_HOME="${LAYERFS_HOME:-$HOME/LayerFS/tmp/lp08-s3/guide-home}"
export FIXTURE="${FIXTURE:-$HOME/LayerFS/tmp/lp08-s3/fixture/p1}"
export PATH="${LAYERFS_BIN_DIR:-$HOME/.local/bin}:$PATH"
mkdir -p "$LAYERFS_HOME"
chmod 700 "$LAYERFS_HOME"
echo "home=$LAYERFS_HOME fixture=$FIXTURE"
```

**预期**：`home=…/guide-home fixture=…/fixture/p1`，exit 0。

```bash
# 步骤 1：确认 CLI 与平台
layerfs --version
layerfs machine platforms
```

**预期**：版本行含 **`layerfs 2.0.0`**；`machine platforms` 是 JSON，
`native`、`docker`、`apple-container` 的 `ready` 为 **true**；
已移除的 `firecracker`、`ssh`、`microsandbox` 不在列表里。

```bash
# 步骤 2：登记内置机器与 native daemon
CLI_DIR="$(cd "$(dirname "$(command -v layerfs)")" && pwd)"
layerfs machine update native --daemon "$CLI_DIR/layerfs-daemon"
# colima: $HOME/.colima/default/docker.sock；Docker Desktop: $HOME/.docker/run/docker.sock
layerfs machine update docker --docker "${DOCKER_SOCK:-$HOME/.colima/default/docker.sock}"
```

**预期**：两条都 exit 0，各打印一条机器记录，`native` 与 `docker` 的 `state`
都是 **`ready`**（`ready` 是“这台机器现在可用”；worker 是否已起看
`machine status`，此时 docker 还没起 worker）。

```bash
# 步骤 3：启动 Docker 机器（先 `colima start` 或打开 Docker Desktop）
docker info >/dev/null
layerfs machine start docker
layerfs machine status docker
```

**预期**：`machine start` 返回 `"state":"running"`；`machine status` 返回
`"state":"running"` 和 `"free_disk":<…>`（本次 **21 GB 量级**；`free_disk` 必须大于
Store 字节 + 1 GiB，否则 push 会 `Capacity`）。

---

## 4. 建 Store、放项目、看状态

```bash
# 步骤 4：建一个 sqlite Store，并把一个目录导入成它的项目
layerfs store create shop
layerfs project init shop/web "$FIXTURE"
layerfs store status shop
```

**预期**：`store create` 返回 `"name":"shop"`、`"kind":"sqlite"`、
**`"machine":"native"`**、`"projects":[]`；`project init` 返回
`"project":"shop/web"` 与 `"layer"`/`"root"` 两个 64 位十六进制摘要；
`store status` 返回 **`"state":"idle"`**、**`"holders":[]`**、**`"op":null`**、
`"file":{"exists":true,…, "incoming_bytes":0}`（本次 Store
**68,046,848** 字节）。

> `store status` 是只读的：它不建锁、不清陈旧租约、不启动机器。

---

## 5. 正常 push（native → 机器）

```bash
# 步骤 5：推到达 docker，并看七阶段进度
layerfs store push shop docker --progress
layerfs store get shop
```

**预期**：`--progress` 的事件逐行写 **stderr**，每行一个 JSON，
`phase` 依次出现 **`check`、`snapshot`、`send`、`verify`、`install`、`record`、`retire`**；
`snapshot`/`send`/`verify` 的 `done`/`total` 是字节数（`send` 按 **8 MiB** 一片递增，
末条 `done==total`），其余阶段为 `null`。stdout 是最后一行结果 JSON：

```json
{"store":"shop","from":"native","to":"docker","bytes":68046848,"heads":"<64 hex>"}
```

`store get shop` 之后应看到 **`"machine":"docker"`**，`last_transfer` 为
`{"call":"store.push","from":"native","to":"docker","at":<ms>,"bytes":68046848,
"sha256":"<64 hex>","heads":"<64 hex>","retired":true}`。

native 侧 `store/shop/store.sqlite*` 已经不在了（`retire` 删掉），
`store/shop/record.json` 保留 —— 这就是“源副本退役”。

```bash
# 步骤 6：确认退役与状态
ls -la "$LAYERFS_HOME/store/shop"
layerfs store status shop
```

**预期**：目录里只有 **`record.json`**（以及 `project/`、`open/` 之类的记录目录），
没有 `store.sqlite`/`-wal`/`-shm`/`.incoming`；`store status` 是
**`"machine":"docker"`**、**`"state":"idle"`**、`"file":{"exists":true,…}`。

---

## 6. 在目标机上用它（Sandbox + Workspace）

```bash
# 步骤 7：在 docker 上开一个 Sandbox，挂一个分支读文件
layerfs sandbox create shop/web sb-shop docker
layerfs branch fork shop/web review main
ws="$(layerfs workspace mount sb-shop review | sed -n 's/.*"ws":"\([^"]*\)".*/\1/p')"
echo "ws=$ws"
layerfs workspace exec "$ws" "ls -la; head -c 64 docs/readme.md" --stream
layerfs workspace unmount "$ws"
layerfs sandbox close sb-shop
```

**预期**：`sandbox create` 返回 `"machine":"docker"`；`workspace mount` 返回
`"ws":"<sandbox>:<path>"` 与客机上的 `"path"`；`workspace exec` 的**第一个位置参数就是这个
`<sandbox>:<path>`（不是“Sandbox 名 + 分支名”）**，命令是第二个位置参数；它打印项目内容
（夹具里 `docs/readme.md` 以 `# lp08 s3 fixture` 开头）并 exit 0。
`workspace unmount` 也必须给它同一个 `<sandbox>:<path>`；有 Workspace 还挂着时
`sandbox close` 会以 `MountsActive` 拒绝。

> 挂载期间**不要** push/pull 同一个 Store：Store 被挂载占用，调用会 `InUse`
> （`detail.related` 列出 `{"kind":"sandbox","name":"sb-shop"}`）。

---

## 7. 正常 pull（机器 → native）

```bash
# 步骤 8：拉回 native
layerfs store pull shop --progress
layerfs store get shop
layerfs store status shop
```

**预期**：七阶段同上；stdout 为
`{"store":"shop","from":"docker","to":"native","bytes":…,"heads":"<同一个 heads>"}`
—— 没有改动时 `heads` 与 push 那次**完全相同**，`store.sqlite` 的 sha256
也和 push 前**逐字节相同**。`store get` 的 `machine` 回到 **`native`**，
`last_transfer` 的 `from`/`to` 互换、`retired:true`。`status` 的
`state` 为 **`idle`**、`op` 为 **null**、`file.incoming_bytes` 为 **0**。

---

## 8. Lima：正常往返

```bash
# 步骤 9：建一台 Lima 机器并往返
layerfs machine create lm lima --cpus 2 --memory 2G --disk 8G
layerfs machine start lm
layerfs machine status lm
layerfs store push shop lm --progress
layerfs store pull shop
```

**预期**：`machine create` 直接返回 `"state":"running"`（它内部已 boot 并拉起
worker；随后 `machine start` 是幂等确认）；`machine status` 的 `free_disk` 是
ext4 数据盘（8 GiB 盘，本次 **7.7 GB 量级**）。push/pull 都 exit 0；两次传输的
`heads` 相同，也等于步骤 8 那次 pull 记录的 `heads`（步骤 7 里 fork 了分支，
所以和步骤 5 的 `heads` 不同，这是内容真的变了，不是传输问题）。

---

## 9. Apple Container：1.6.1 的丢应答、诊断与恢复

Apple Container 1.6.1 的端口转发在“机器 → 宿主的大块应答”上会丢连接：
`store pull` 在 `send` 阶段报 `Unknown`。**它不是数据损坏，也不是 bundle 旧**；
正确反应是**同一条命令再跑一次**（先删不可信的那半份，再重来），不要手工删文件、
不要改用 `push`。这一段同时演示 `Unresolved` 状态的诊断、异向拒绝和恢复。

```bash
# 步骤 10：建 Apple Container 机器，把另一个 Store 推上去
layerfs machine create ac apple-container --cpus 2 --memory 2G --disk 8G
layerfs machine start ac
layerfs store create acshop
layerfs project init acshop/web "$FIXTURE"
layerfs store push acshop ac --progress
```

**预期**：`machine create` 返回 `"state":"running"`；**push 方向稳定**（LP08-S1 的
7/7 与 LP08-S3 全部 push 都成功），exit 0。

```bash
# 步骤 11：反复 pull，直到遇到一次丢应答（本机的 1.6.1 转发经常一次就丢）
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if layerfs store pull acshop; then
    echo "attempt $attempt: pull ok, pushing again to retry"
    layerfs store push acshop ac >/dev/null || break
  else
    echo "attempt $attempt: lost the worker's answer"
    break
  fi
done
layerfs store status acshop
layerfs doctor
```

**预期**：某一次 `store pull` exit **125**，stderr 是

```text
{"code":"Unknown","message":"store pull, send: store.file: the worker's answer was lost (worker connection: failed to fill whole buffer); it may have run, and was not resent","detail":{"phase":"send"}}
```

随后 `store status` 是 **`"state":"unresolved"`**、`op` 为
**`{"name":"store.pull","phase":"send","uncertain":true}`**、`machine` 仍是
**`ac`**；`doctor` 是 **error**：
`store acshop has an unresolved store.pull (…, phase send): its outcome is not known`，
fix 为 **`` `layerfs store status acshop` shows it; `layerfs store pull acshop` clears it ``**。
机器上的副本完好（`store status` 的 `file.bytes` 仍是 68,046,848），native 侧没有权威副本。

> 如果 10 次都没丢（转发这次健康），这一段就演示不出 `Unresolved`：可以把项目目录
> 做大一点再试，或直接跳到步骤 15（那里演示“确定失败”的中断）。**不要**为了制造失败
> 去手工改 `LAYERFS_HOME` 里的记录。
>
> 反过来，如果连续多次都丢（本机 1.6.1 在负载高时会这样），只做一件环境动作：
> `layerfs machine stop ac` + `layerfs machine start ac`，转发重新建立后再跑同一条
> `store pull`（步骤 13 的循环就是这么写的）。**不要**手工删 `.incoming`、
> 不要改 `store push`：数据面没问题，坏的是转发层。

```bash
# 步骤 12：异向命令必须拒绝，且不删任何副本
layerfs store push acshop docker
```

**预期**：exit **125**，
`{"code":"Unresolved","message":"store push, check: Store acshop has an unresolved store.pull (op-…, phase send): its outcome is not known; see `layerfs store status acshop`, then clear it with `layerfs store pull acshop`","detail":{"entity":{"kind":"store","name":"acshop"},"phase":"check","op":"op-…"}}`。
**两侧副本与 home 逐字节不变**（LP08-S3 `REVERSE` 实测：home 树、目标目录、文件 sha256 全同）。

```bash
# 步骤 13：同一条命令恢复；连续丢应答就把机器重启一次（转发层重新建立）
for attempt in 1 2 3; do
  if layerfs store pull acshop; then echo "recovered on attempt $attempt"; break; fi
  layerfs store status acshop
  layerfs machine stop ac
  layerfs machine start ac
done
layerfs store status acshop
```

**预期**：`recovered on attempt <n>`，pull exit 0，
`{"store":"acshop","from":"ac","to":"native",…}`；
`store status` 是 **`"state":"idle"`**、**`"machine":"native"`**、**`op:null`**；
`last_transfer.retired` 为 **true**；native 的 `store.sqlite` 的 sha256 等于
`last_transfer.sha256`；机器上的副本已删（`file` 为 unavailable 或不存在）。

```bash
# 步骤 14：删掉这个 Store（两侧副本 + 记录）
layerfs store remove acshop
layerfs store list
```

**预期**：`{"removed":"acshop"}`；`store list` 里没有 `acshop`；
`$LAYERFS_HOME/store/acshop` 与机器上的 `/layerfs/data/store/acshop` 都不在了；
**机器还在**（`machine status ac` 仍是 running）。

---

## 10. 确定失败的中断：诊断 + 同命令恢复

```bash
# 步骤 15：第一个 send 分片一出现就 SIGKILL，然后只读诊断
err="${TMPDIR:-/tmp}/lp08-push-send.err"
: > "$err"
layerfs store push shop docker --progress >/dev/null 2>"$err" &
pid=$!
for i in $(seq 1 5000); do
  grep -q '"phase":"send","done":[1-9]' "$err" 2>/dev/null && break
  kill -0 "$pid" 2>/dev/null || break
  sleep 0.001
done
kill -9 "$pid" 2>/dev/null
wait "$pid" 2>/dev/null
echo "progress events seen: $(grep -c progress "$err")"
layerfs store status shop
layerfs store get shop
layerfs store list
layerfs doctor
```

**预期**：`store status` 里出现 `op`（进程被 `SIGKILL`，它自己不会清），
`phase` 是 **`send`**，`uncertain` 为 **false**，`machine` 仍是 **`native`**，
`file.incoming_bytes` 为 **0**（残片在机器上）。`doctor` 给两条 warning：

1. `store shop still records store.push (op-…, phase send), whose process ended after a
   certain outcome; it holds nothing`，fix **`nothing to do: the next operation on store shop replaces it`**；
2. `machine docker holds a <N>-byte partial copy (store.sqlite.incoming) of Store shop left by
   an interrupted transfer; nothing reads it`，fix **`` `layerfs store push shop docker` replaces it ``**。

`store status`/`store get`/`store list`/`doctor` 都是只读的：前后 `LAYERFS_HOME` 的
路径、权限、大小、mtime、内容 sha256 **完全不变**（LP08-S3 `READONLY` 实测 20 条断言通过，
含 `layerfs.lock` 未被触碰）。若 `op` 是 `null`，说明这一枪打空了（push 已经跑完）：
`layerfs store pull shop` 拉回来再跑本块。

```bash
# 步骤 16：同一条命令恢复（先删它不认的那份，再重来）
layerfs store push shop docker
layerfs store get shop
layerfs store status shop
```

**预期**：exit 0；`store get` 的 `machine` 为 **`docker`**，`last_transfer.retired`
为 **true**，`sha256`/`heads` 与步骤 5/8 的同一份内容一致；`store status` 回到
**`idle`**、`op:null`、`incoming_bytes` 为 **0**（残片已被替换掉）。
再跑一次同一条命令会以
`InvalidInput: Store shop is on machine docker; layerfs store pull shop brings it to native first`
拒绝，且不会产生第二份副本 —— 恢复是幂等的。

---

## 11. 确定性失败：retire 无法删源副本

```bash
# 步骤 17：先把源文件设成不可删，再 push —— retire 必然失败
layerfs store create locked
layerfs project init locked/web "$FIXTURE"
chflags uchg "$LAYERFS_HOME/store/locked/store.sqlite"
err2="${TMPDIR:-/tmp}/lp08-push-retire.err"
: > "$err2"
layerfs store push locked docker --progress >/dev/null 2>"$err2"
echo "push exit=$?"
tail -1 "$err2"
chflags nouchg "$LAYERFS_HOME/store/locked/store.sqlite"
layerfs store get locked
layerfs doctor
```

**预期**：`push exit=125`，最后一行是

```json
{"code":"Failed","message":"store push, retire: Store locked is now on docker (authority switched to docker; source copy on native was not retired: Os { code: 1, kind: PermissionDenied, message: \"Operation not permitted\" })","detail":{"authority":"docker","source":"native","retired":false,"phase":"retire"}}
```

`store get`：**`"machine":"docker"`**、`last_transfer.retired` 为 **false**；
`doctor`：warning **`Store locked's store.push from native to docker did not retire the copy on
native; the record names docker, and nothing reads that copy`**，fix
**`` the next `layerfs store pull locked` deletes it first ``**。
Store 在 docker 上可用（`store status` 是 `idle`）。

```bash
# 步骤 18：下一次 pull 先删残留再成功
layerfs store pull locked
layerfs store status locked
```

**预期**：exit 0；`machine` 回到 **`native`**，`state` 为 **`idle`**，
`last_transfer.retired` 为 **true**，`heads` 不变，docker 上的副本消失。

```bash
# 步骤 19：删掉它，并确认 doctor 干净
layerfs store remove locked
layerfs store list
layerfs doctor
```

**预期**：`{"removed":"locked"}`；`store list` 里没有 `locked`；`doctor` 只剩机器层面的
正常输出，没有 `locked` 的 finding。

> 两个已知缺口（LP08-S3 实测，与用法无关）：
> 1. 一次 **certain** 的中断（例如 verify 摘要不符被拒）会清掉 `op`，
>    此后 `doctor` **看不到**目标机上那份残 `.incoming`（没有记录可依）。
> 2. 同一种 certain 中断之后 `store remove` **只清本机**，机器上的
>    `store.sqlite.incoming` 会留下（不阻塞下次 push，但占磁盘）。
>    有记录可依的中断（uncertain / `retired:false`）不受影响，remove 会清两侧。

---

## 12. 资源与容量上限（实测 + 源码常量）

| 项 | 值 | 来源 |
| --- | --- | --- |
| 单次读取分片 | **8 MiB**（`CHUNK`） | `control/crates/layerfs-store/src/sqlite/transfer/steps.rs` |
| 目标磁盘前置检查 | `needed = bytes + max(1 GiB, bytes/10)`，用**目标侧** `statvfs` | `sqlite/transfer/phases.rs` `HEADROOM`、`reach` |
| 不足时 | `Capacity`，`detail:{needed, free}`，不写 `op`、不建文件 | 同上（本次未构造，未复现） |
| 传输中的临时文件 | 目标侧 `<store>/store.sqlite.incoming`，峰值 = Store 字节 | `steps.rs` `Write`/`Install` |
| worker 帧上限 | **512 MiB**（`MAX_FRAME`） | `control/crates/layerfs-machine/src/worker/frame.rs` |
| 内存 | 调用方按 8 MiB 分片搬运，不随 Store 线性增长 | `phases.rs` `send` 循环 |
| 两跳（机器 A → native → 机器 B） | native 同时需要 `bytes + max(1 GiB, 10%)` 余量；两段各记一次 `last_transfer` | `pull` 后 `push` |
| 进度节奏 | `snapshot`/`verify` 每 250 ms 一条，`send` 每片一条 | `pieces::sha256_file_observed`、`phases.rs` |
| 本次 Store | 68,046,848 B；docker push **0.35 s**、pull **0.12 s**（warm，仅诊断） | LP08-S3 回执 |

---

## 13. 收尾

```bash
# 步骤 20：删 Store、删机器、停 Docker
layerfs store remove shop
layerfs machine remove lm
layerfs machine remove ac
layerfs machine stop docker
layerfs machine list
layerfs doctor
```

**预期**：`store remove shop` 返回 `{"removed":"shop"}`；`machine remove` 两条都
exit 0（`lm`/`ac` 的 VM 与数据盘一起删除）；
`machine stop docker` 后 docker 的 `state` 是 **`stopped`**；
`machine list` 只剩 **`native`** 与 **`docker`**；`doctor` 是 **`{"ok":true,"findings":[]}`**。

---

## 14. 常见拒绝与处理（速查）

| 现象 | 含义 | 处理 |
| --- | --- | --- |
| `InvalidInput: Store X is on machine M; layerfs store pull X brings it to native first` | 只有 native 能 push | 先 `store pull` |
| `InvalidInput: Store X is already on native` | pull 的目标就是 native | 用 `store push` |
| `InvalidInput: … is a PostgreSQL database; it does not move` | PG Store 不搬 | 不要搬 |
| `NotFound: no Store named X` / `no machine named M` | 名字错/没建 | `store list` / `machine list` |
| `Exists: machine M already holds a Store file named X` | 目标已有同名文件（`check` 阶段） | 先在该机清掉或换名 |
| `Capacity, detail.needed/free` | 目标盘不够 `bytes + max(1 GiB,10%)` | 加盘或换机 |
| `Unavailable: machine M is not running; start it with layerfs machine start M` | 机器没起（**不会**自动起） | `machine start M` |
| `InUse` + `detail.related:[{kind:"sandbox"}]` | 该项目有 Sandbox | `sandbox close` |
| `InUse` + `{kind:"lease",name:<pid>}` | 另一个活进程占着 Store | 等它结束 |
| `Busy: … runs in process <pid>` | 同一 Store 有操作在跑 | 等它结束 |
| `Unresolved` + fix 指向同方向命令 | 上次结果未知 | 跑 fix 里的那条命令 |
| `Unknown: … the worker's answer was lost … was not resent` | 应答丢了（Apple Container 常见） | 同一命令重跑（幂等） |
| ``Unsupported: platform `firecracker` was removed in LayerFS 2.0``（`ssh`、`microsandbox` 同） | 平台已移除 | 换 Docker/Lima/Apple Container；旧记录用 `machine remove` 忘掉 |

---

## 15. 复现记录

- 本文件的每个 ```bash 代码块都由 `guide_repro.py` 在
  `/tmp/lp08-s3/guide-home`（全新 home）里**按顺序逐字**执行。
- 逐块的命令、退出码、stdout、stderr 落在
  `store-transfer/receipts/guide/`（`guide-receipts.json` 与每块 raw 文件）。
- 读数（字节数、耗时、`free_disk`）随机器负载变化；**加粗**字段是断言项。
