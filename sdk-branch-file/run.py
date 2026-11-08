"""Bounded CLI-only branch/file route qualification; no SDK imports or Store SQL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.parse import parse_qsl, urlsplit


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--route', choices=['native', 'postgresql', 'worker'], required=True)
    parser.add_argument('--pg-url')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--image', default='layerfs-352-runtime:node24-https-apt-20261024')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.cli.is_absolute() and args.cli.is_file()
    head = subprocess.check_output(['git', '-C', str(args.source_dir), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == args.source and len(head) == 40
    args.output.mkdir(parents=True, exist_ok=False)
    home = Path(tempfile.mkdtemp(prefix='layerfs-134-cli-home-'))
    home.chmod(0o700)
    folder = Path(tempfile.mkdtemp(prefix='layerfs-134-cli-input-'))
    (folder / 'base.txt').write_text('base\nkept\n')
    env = dict(os.environ, LAYERFS_HOME=str(home), LAYERFS_CONSTRUCTION_WORKERS='1')
    receipt = dict(source=head, cli=str(args.cli), cli_sha256=digest(args.cli), route=args.route,
                   home=str(home), folder=str(folder), outcome='FAIL', steps=[],
                   cache='unspecified/warm correctness only; no performance claim', cleanup='not attempted')
    if args.bundle:
        env['LAYERFS_BUNDLE'] = str(args.bundle.resolve())
        receipt['bundle_manifest'] = json.loads((args.bundle / 'bundle.json').read_text())
    started = time.monotonic()

    def call(label, words, data=None, error=None):
        remaining = 110 - (time.monotonic() - started)
        assert remaining > 0, '110 second qualification ceiling'
        run = subprocess.run([str(args.cli), *words], input=data, text=True, capture_output=True,
                             env=env, timeout=min(20, remaining))
        record = dict(label=label, command=words, exit=run.returncode, stdout=run.stdout, stderr=run.stderr)
        with (args.output / 'steps.jsonl').open('a') as out:
            out.write(json.dumps(record) + '\n')
        receipt['steps'].append(dict(label=label, exit=run.returncode))
        if error:
            assert run.returncode == 125, (label, run.returncode, run.stderr)
            value = json.loads(run.stderr.strip().splitlines()[-1])
            assert value['code'] == error, (label, value)
            return value
        assert run.returncode == 0, (label, run.returncode, run.stderr)
        return json.loads(run.stdout)

    p = 'sdk/api'
    try:
        if args.route == 'postgresql':
            assert args.pg_url
            url = urlsplit(args.pg_url)
            assert url.scheme in ['postgresql', 'postgres'] and url.password is None
            assert not any('password' in key.lower() for key, _ in parse_qsl(url.query))
            made = call('connect disposable-equivalent PostgreSQL', ['store', 'connect', 'sdk', args.pg_url, '--synchronous-commit=off'])
            assert made['synchronous_commit'] == 'off'
        else:
            assert call('create Disposable Store', ['store', 'create', 'sdk'])['profile'] == 'disposable'
        init = call('Init', ['project', 'init', p, str(folder)])['layer']
        foreign = call('other project Init', ['project', 'init', 'sdk/other', str(folder)])['layer']
        call('fork left', ['branch', 'fork', p, 'left', 'main'])
        call('fork right', ['branch', 'fork', p, 'right', 'main'])
        left = call('left independently changes line', ['file', 'write', p, 'left', '/base.txt'], 'alpha\nkept\n')['head']
        right = call('right independently changes line', ['file', 'write', p, 'right', '/base.txt'], 'alpha\nkept\n')['head']
        publication = call('publish left', ['branch', 'publish', p, 'left'])['published_layer']['id']
        head = call('add file', ['file', 'write', p, 'left', '/new.txt'], 'new\n')['head']
        if args.route == 'worker':
            assert args.bundle
            call('select worker runtime', ['machine', 'update', 'docker', '--image', args.image])
            call('start worker', ['machine', 'start', 'docker'])
            home_id = json.loads((home / 'layerfs.json').read_text())['id']
            worker_name = 'lfs-' + home_id[:8] + '-docker'
            worker = json.loads(subprocess.check_output(['docker', 'inspect', worker_name], text=True, timeout=10))[0]
            receipt['worker'] = dict(id=worker['Id'], name=worker_name, image=worker['Image'],
                                     bundle=worker['Config']['Labels']['layerfs.bundle'],
                                     volumes=[m['Name'] for m in worker['Mounts'] if m['Type'] == 'volume'])
            call('push Store to worker', ['store', 'push', 'sdk', 'docker'])
            assert call('check placement', ['store', 'get', 'sdk'])['machine'] == 'docker'
        main = call('main saved head', ['branch', 'get', p, 'main'])
        assert main['saved_head']['id'] == publication and main['saved_head']['kind'] == 'Layer'
        rows = call('main publications', ['branch', 'commits', p, 'main', '--page=1', '--page-size=1'])
        assert rows['items'][0]['source_commit'] == left
        detail = call('publication details', ['branch', 'get-commit', p, 'main', publication])
        assert detail['parent_ref']['id'] == init and detail['source_commit_ref']['id'] == left
        assert detail['time'] is None and detail['time_status'] == 'unavailable'
        call('pinned page 1', ['branch', 'commits', p, 'left', '--page=1', '--page-size=1', f'--at-commit={head}'])
        call('move branch head', ['file', 'write', p, 'left', '/later.txt'], 'later\n')
        rows = call('stable pinned page 2', ['branch', 'commits', p, 'left', '--page=2', '--page-size=1', f'--at-commit={head}'])
        assert rows['items'][0]['id'] == left
        for a, b, ab, bb in [(init, left, 'main', 'left'), (left, publication, 'left', 'main'),
                              (init, publication, 'main', 'main'), (left, right, 'left', 'right')]:
            answer = call('mixed saved comparison', ['branch', 'diff', p, ab, bb, f'--from-commit={a}', f'--to-commit={b}', '--page=1'])
            assert answer['from']['id'] == a and answer['to']['id'] == b
        diff = call('discover ownership-only content', ['branch', 'diff', p, 'main', 'right', f'--from-commit={publication}', f'--to-commit={right}', '--include-attribution', '--page=1'])
        changed = next(x for x in diff['items'] if x['path'] == '/base.txt')
        assert changed['content'] is False and changed['attribution'] is True
        diff = call('aligned ownership', ['file', 'diff', p, 'main', '/base.txt', 'right', '/base.txt',
                    f'--left-commit={publication}', f'--right-commit={right}', '--include-attribution', '--page=1'])
        owner = [r for r in diff['rows'] if r['owner_changed'] is True]
        assert len(owner) == 1 and owner[0]['before_owner']['ref']['id'] == left and owner[0]['after_owner']['ref']['id'] == right
        blame = call('published provenance', ['file', 'blame', p, 'main', '/base.txt', publication])
        assert blame['lines'][0]['owner']['ref']['id'] == left and blame['lines'][1]['owner']['ref']['id'] == init
        revision = call('file revision', ['file', 'revision', p, 'left', '/base.txt', f'--at-commit={head}', '--page=1'])
        assert any(r['ref']['id'] == left for r in revision['items'])
        call('legacy missing path', ['file', 'diff', p, 'main', '/new.txt', 'left', '/new.txt'], error='NoSuchPath')
        added = call('opted missing side', ['file', 'diff', p, 'main', '/new.txt', 'left', '/new.txt', '--allow-missing', '--page=1'])
        assert added['before'] is None and added['after'] is not None
        call('invalid page', ['branch', 'commits', p, 'left', '--page=0'], error='InvalidInput')
        call('foreign valid Layer', ['branch', 'get-commit', p, 'main', foreign], error='InvalidInput')
        call('folder history refusal', ['file', 'revision', p, 'left', '/inside/a', '--scope=/inside', f'--scope-project={p}', '--scope-branch=agent'], error='InvalidInput')
        for verb, extra in [('list', []), ('glob', ['**/*.txt']), ('grep', ['alpha'])]:
            answer = call('pinned ' + verb, ['file', verb, p, 'left', '/', *extra, head, '--page=1', '--page-size=2'])
            assert answer['at']['id'] == head
        call('remove private Store via CLI', ['store', 'disconnect' if args.route == 'postgresql' else 'remove', 'sdk'])
        if args.route == 'worker':
            call('stop private worker via CLI', ['machine', 'stop', 'docker'])
        receipt['outcome'] = 'PASS'
        receipt['cleanup'] = 'Store removed/disconnected through CLI; worker stopped when used; private home and stopped infrastructure retained for explicit owner cleanup'
    except Exception as error:
        receipt['error'] = repr(error)
    receipt['elapsed_seconds'] = time.monotonic() - started
    with (args.output / 'receipt.json').open('x') as out:
        json.dump(receipt, out, indent=2)
    print(json.dumps({'outcome': receipt['outcome'], 'route': args.route, 'steps': len(receipt['steps']), 'receipt': str(args.output / 'receipt.json')}))
    return 0 if receipt['outcome'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
