#!/usr/bin/env python3
"""One arm of the committed #327 counter screen; no resampling or orchestration."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

mode, arm, source, output = sys.argv[1:]
assert mode in ('run', 'verify') and arm in ('off', 'on')
source, output = Path(source).resolve(), Path(output).resolve()
binary = source / 'core/target/release/examples/issue327_counters_v3'
def git(*args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name, value):
    with (output / name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
if mode == 'run':
    output.mkdir(parents=True, exist_ok=False)
    assert not git('status', '--porcelain', '--untracked-files=no')
    save('identity.json', dict(source=git('rev-parse', 'HEAD'), tree=git('rev-parse', 'HEAD^{tree}'), binary=digest(binary), harness=digest(__file__), example=digest(source/'core/crates/layerfs-persistence/examples/issue327_counters_v3.rs'), lock=digest(source/'core/Cargo.lock'), config=(source/'.cargo/config.toml').read_text(), rust=subprocess.check_output(['rustc','+1.85.1','-Vv'],text=True), cargo=subprocess.check_output(['cargo','+1.85.1','-V'],text=True), host=subprocess.check_output(['uname','-a'],text=True), cache='created-in-sample Store; fixed warm in-memory fixture', setup='fresh', arm=arm, samples=1, interference='No concurrent owned build/test/measurement; other host activity uncontrolled'))
    (output/'source.patch').write_text(git('diff','HEAD^','HEAD'))
    (output/'dependency-seal.txt').write_text(subprocess.check_output(['cargo','+1.85.1','metadata','--manifest-path',str(source/'core/Cargo.toml'),'--locked','--offline','--format-version','1'],cwd=source,text=True))
started = time.monotonic_ns()
env = {**os.environ, 'SCREEN_SCENARIO':'issue327-publication-totals-v3','SCREEN_COUNTERS':arm,'LAYERFS_CONSTRUCTION_WORKERS':'1'}
command = [str(binary), mode, str(output/'store.db'), str(output/('measurement.json' if mode=='run' else 'verification.json'))]
with (output/(mode+'.stdout')).open('x') as stdout, (output/(mode+'.stderr')).open('x') as stderr:
    try:
        result = subprocess.run(command, env=env, stdout=stdout, stderr=stderr, timeout=14 if mode=='run' else 8, check=False)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
save(mode+'-command.json',dict(command=command,wall_ns=time.monotonic_ns()-started,exit=code,limit_s=15 if mode=='run' else 10))
assert code == 0, code
if mode == 'verify':
    c=sqlite3.connect(f'file:{output}/store.db?mode=ro&immutable=1',uri=True)
    # Connection-local OFF is selected explicitly; stored WAL mode is verified separately.
    c.execute('PRAGMA synchronous=OFF')
    one=lambda sql: c.execute(sql).fetchone()[0]
    logical=one('SELECT sum(logical) FROM (SELECT logical FROM "commit" UNION ALL SELECT logical FROM layer)')
    canonical=one('SELECT sum(canonical_length) FROM object_location')
    stored=one('SELECT sum(length) FROM pack')
    meta=one('SELECT coalesce(sum(length),0) FROM pack WHERE domain=0')
    totals=c.execute('SELECT logical,canonical,stored,metadata FROM store_totals').fetchone()
    assert totals == ((logical,canonical,stored,meta) if arm=='on' else (0,0,0,0)), (totals,logical,canonical,stored,meta)
    assert one('SELECT count(*) FROM "commit"')==128
    assert one('SELECT count(*) FROM "commit" WHERE message="Counter screen" AND logical=32768')==128
    assert one('SELECT count(*) FROM layer')==1
    assert one('SELECT identity_format FROM history_meta')==3
    assert one('PRAGMA user_version')==16
    assert (output/'store.db').read_bytes()[18:20]==bytes([2,2]) and one('PRAGMA synchronous')==0
    assert one('PRAGMA integrity_check')=='ok'
    pages,free,size=(one('PRAGMA '+v) for v in ('page_count','freelist_count','page_size'))
    stat=(output/'store.db').stat()
    assert stat.st_size==pages*size
    measurement=json.loads((output/'measurement.json').read_text())
    assert measurement['file_bytes']==stat.st_size and measurement['allocated_bytes']==stat.st_blocks*512
    save('sql-verification.json',dict(status='PASS',sqlite=sqlite3.sqlite_version,totals=totals,independent_sums=dict(logical=logical,canonical=canonical,stored=stored,metadata=meta),metadata_with_sql_overhead=meta+(pages-free)*size-stored,page_count=pages,freelist_count=free,page_size=size,file=stat.st_size,allocated=stat.st_blocks*512,identity=3,version=16,profile='Disposable/WAL/OFF',wall_ns=time.monotonic_ns()-started))
print(f'{mode} {arm}: PASS; {output}')
