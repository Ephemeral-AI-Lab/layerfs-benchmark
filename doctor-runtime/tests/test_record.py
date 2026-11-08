import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('record',Path(__file__).parents[1]/'src/record.py')
record=importlib.util.module_from_spec(spec);spec.loader.exec_module(record)

class RecordTests(unittest.TestCase):
    def fixture(self,root):
        cli=root/'layerfs';cli.write_bytes(b'fixture executable')
        return {'cli':str(cli),'source':str(root),'home':str(root/'home'),'environment':{'LAYERFS_X_SECRET_KEY':'private-value'}}
    def test_existing_receipt_prevents_invocation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=self.fixture(root);out=root/'out';out.mkdir();(out/'same.json').write_text('{}')
            with patch.object(record.subprocess,'run') as run:
                with self.assertRaises(FileExistsError):record.invoke(config,['doctor','host'],out,'same')
                run.assert_not_called()
    def test_secret_output_fails_and_is_redacted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=self.fixture(root)
            result=subprocess.CompletedProcess([],0,'private-value','')
            with patch.object(record.subprocess,'run',return_value=result) as run,patch.object(record.subprocess,'check_output',side_effect=['source\n',b'']):
                receipt=record.invoke(config,['doctor','host'],root/'out','redacted')
                self.assertEqual(receipt['verdict'],'FAIL');self.assertNotIn('private-value',(root/'out/redacted.json').read_text());self.assertEqual(run.call_count,1)
    def test_timeout_retains_partial_output_without_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=self.fixture(root)
            error=subprocess.TimeoutExpired([],1,output=b'partial evidence',stderr=b'partial error')
            with patch.object(record.subprocess,'run',side_effect=error) as run,patch.object(record.subprocess,'check_output',side_effect=['source\n',b'']):
                receipt=record.invoke(config,['doctor','host'],root/'out','timeout',timeout=1)
                self.assertTrue(receipt['timed_out']);self.assertEqual(receipt['stdout'],'partial evidence');self.assertIn('partial error',receipt['stderr']);self.assertEqual(run.call_count,1)
    def test_unknown_family_or_doctor_over_budget_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=self.fixture(root)
            for command,timeout in [(['worker'],1),(['doctor','host'],101)]:
                with self.assertRaises(ValueError):record.invoke(config,command,root/'out','bad',timeout=timeout)
    def test_snapshot_never_visits_runtime_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);record_path=root/'machine/native/record.json';record_path.parent.mkdir(parents=True);record_path.write_text('{}')
            runtime=root/'machine/native/run';runtime.mkdir();(runtime/'payload.json').write_text('payload')
            original=Path.iterdir
            def guarded(path):
                if path==runtime:raise AssertionError('runtime traversal')
                return original(path)
            with patch.object(Path,'iterdir',guarded):snapshot=record.logical_snapshot(root)
            self.assertEqual(set(snapshot),{'machine/native/record.json'})
    def test_unexpected_confirmed_failure_and_incomplete_coverage_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=self.fixture(root)
            output={'complete':False,'checks':[{'id':'host.records','outcome':'fail','severity':'error'}]}
            with patch.object(record.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps(output),'')),patch.object(record.subprocess,'check_output',side_effect=['source\n',b'']):
                receipt=record.invoke(config,['doctor','host'],root/'out','coverage',complete=True)
            self.assertEqual(receipt['verdict'],'FAIL');self.assertEqual(len(receipt['failures']),2)

if __name__=='__main__':unittest.main()
