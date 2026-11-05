"""Focused proof regression tests; these are local oracle tests, not samples."""

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("quick_cases", Path(__file__).resolve().parents[1] / "src" / "cases.py")
cases = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cases)


class NumberedProofTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        # Independent fixture construction; do not execute the measured body.
        for number in range(1, 1001):
            (self.root / f"f{number}").write_bytes(f"{number}\n".encode())

    def proof(self, case_id="C01"):
        return subprocess.run(
            [
                "/bin/bash",
                "-o",
                "pipefail",
                "-c",
                cases.get_case(case_id, verify=True)["verifier"],
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def test_exact_result_passes(self):
        result = self.proof()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "VERIFY OK\n")

    def test_missing_trailing_newline_fails(self):
        (self.root / "f500").write_bytes(b"500")
        self.assertNotEqual(self.proof().returncode, 0)

    def test_same_size_wrong_contents_fail(self):
        (self.root / "f500").write_bytes(b"501\n")
        self.assertNotEqual(self.proof().returncode, 0)

    def test_unexpected_hidden_entry_fails(self):
        (self.root / ".unexpected").touch()
        self.assertNotEqual(self.proof().returncode, 0)

    def test_symlink_substitution_fails(self):
        (self.root / "f500").unlink()
        (self.root / "f500").symlink_to("f501")
        self.assertNotEqual(self.proof().returncode, 0)

    def test_verification_is_opt_in(self):
        case = cases.get_case("C01")
        self.assertIsNone(case["verifier"])
        self.assertNotIn("verification", case["provenance"])

    def test_c02_keeps_pinned_source_and_shared_proof(self):
        case = cases.get_case("C02", verify=True)
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "76883ee8358e23ebea7af1931db3d7201684d1da240bc0fefec72781ff569cf6",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "f1708450d58b34975627f5a620fa69cb9df17a0437235feaf302843f81dece18",
        )
        self.assertEqual(case["setup"], "")
        self.assertIsNone(cases.get_case("C02")["verifier"])
        self.assertEqual(case["verifier"], cases.get_case("C01", verify=True)["verifier"])
        result = self.proof("C02")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class EmptyProofTests(unittest.TestCase):
    def test_empty_result_passes_and_hidden_entry_fails(self):
        case = cases.get_case("C03", verify=True)
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "520773ceacd8c44d633ffd1a40727ceb5d990d63a23259f28af8dd4b96fa204d",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "f5b32c4a764970421c6d7a7363759df0b5dcce3bfdb63a92ebbb1e1f0872f6e2",
        )
        self.assertIsNone(cases.get_case("C03")["verifier"])
        with tempfile.TemporaryDirectory() as directory:

            def proof():
                return subprocess.run(
                    ["/bin/bash", "-o", "pipefail", "-c", case["verifier"]],
                    cwd=directory,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )

            self.assertEqual(proof().returncode, 0)
            (Path(directory) / ".hidden").touch()
            self.assertNotEqual(proof().returncode, 0)


class TreeProofTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for a in range(1, 11):
            for b in range(1, 11):
                parent = self.root / str(a) / str(b)
                parent.mkdir(parents=True)
                for c in range(1, 11):
                    (parent / str(c)).touch()

    def proof(self):
        return subprocess.run(
            ["/bin/bash", "-o", "pipefail", "-c", cases.get_case("C04", verify=True)["verifier"]],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def test_exact_tree_and_source_pin(self):
        case = cases.get_case("C04")
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "bc6078a63239e725c8fb10ee5287616745bcf231705a26dabc9f93c43c66d4f9",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "fe4b426dbf768ac606bb1d197278d66e441846bb00425c1f5979386745a0612e",
        )
        result = self.proof()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_counts_wrong_directory_fails(self):
        (self.root / "10" / "10").rename(self.root / "10" / "11")
        self.assertNotEqual(self.proof().returncode, 0)

    def test_nonempty_file_fails(self):
        (self.root / "10" / "10" / "10").write_bytes(b"x")
        self.assertNotEqual(self.proof().returncode, 0)

    def test_hidden_nested_entry_fails(self):
        (self.root / "10" / "10" / ".hidden").touch()
        self.assertNotEqual(self.proof().returncode, 0)


class FindTreeDefinitionTests(unittest.TestCase):
    def test_c05_source_and_shared_oracle(self):
        case = cases.get_case("C05")
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "4306a767d8d5316887f0543abef12d01676bbdfdaff121fd039e56cad5742c8d",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "cf432b9ee6dce623884758b85bd3fca7dd972828a668661c815313c8b402199d",
        )
        self.assertEqual(case["body"], cases.get_case("C04")["body"] + "; find . -type f | wc -l")
        self.assertEqual(case["exec_argv"][:3], ["/bin/bash", "-o", "pipefail"])
        self.assertIsNone(case["verifier"])
        self.assertEqual(cases.get_case("C05", verify=True)["verifier"], cases.get_case("C04", verify=True)["verifier"])


class BigProofTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def proof(self):
        return subprocess.run(
            ["/bin/bash", "-o", "pipefail", "-c", cases.get_case("C06", verify=True)["verifier"]],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def test_source_pin(self):
        case = cases.get_case("C06")
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "68c36eedeb7daf07516db93ca0ac0263bf3859d42549f7d490b1f074475ffc9d",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "d6b326be0d11aa8b375a561c8bbad779165d5b0e0b1e9df26d6b782c3459bc73",
        )
        self.assertIsNone(case["verifier"])

    def test_small_wrong_file_fails(self):
        (self.root / "big").write_bytes(b"\0")
        self.assertNotEqual(self.proof().returncode, 0)

    def test_complete_zero_file_passes_and_last_byte_corruption_fails(self):
        # Sparse zero fixture exercises the full read without a large allocation.
        with (self.root / "big").open("wb") as stream:
            stream.truncate(67108864)
        result = self.proof()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with (self.root / "big").open("r+b") as stream:
            stream.seek(67108863)
            stream.write(b"x")
        self.assertNotEqual(self.proof().returncode, 0)


class BigCopyDefinitionTests(unittest.TestCase):
    def test_source_and_required_second_file(self):
        case = cases.get_case("C07", verify=True)
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "4d50a741653d9e90efba6eece312ea5a57b13be6142c3bfc09b57f643088e723",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "429f5a14d6ed51762e2ee2453ad2081d320b49371e35edd533bfc34840a582a4",
        )
        self.assertIsNone(cases.get_case("C07")["verifier"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / "big").open("wb") as stream:
                stream.truncate(67108864)
            (root / "wrong-name").touch()
            result = subprocess.run(
                ["/bin/bash", "-o", "pipefail", "-c", case["verifier"]],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("regular file big2", result.stdout)
            (root / ".extra").touch()
            result = subprocess.run(
                ["/bin/bash", "-o", "pipefail", "-c", case["verifier"]],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("root entry count", result.stdout)


class BigReadDefinitionTests(unittest.TestCase):
    def test_c08_source_and_shared_oracle(self):
        case = cases.get_case("C08")
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "af994b2385d66c015921c49f44fce0cdb247cb42cbe64710ad36556b418a865d",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "d039d9afc57fd431e702c0b4a3f6eb23675d6baf61d92a2b2f1ece3a677d9882",
        )
        self.assertEqual(case["body"], cases.get_case("C06")["body"] + "; cat big > /dev/null")
        self.assertIsNone(case["verifier"])
        self.assertEqual(cases.get_case("C08", verify=True)["verifier"], cases.get_case("C06", verify=True)["verifier"])


class CommittedReadDefinitionTests(unittest.TestCase):
    def test_c09_reads_committed_setup_as_distinct_phase(self):
        case = cases.get_case("C09")
        self.assertEqual(case["body"], "cat big > /dev/null")
        self.assertEqual(case["starting_view"], "committed-base")
        self.assertEqual(case["setup"], cases.get_case("C06")["body"])
        self.assertEqual(case["setup_command"], cases.get_case("C06")["command"])
        self.assertEqual(case["setup_argv"], cases.get_case("C06")["exec_argv"])
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "37eb10ecfa439aa69bc9e430d39ce029099fa2bb52a44a67ffef8a31ecdac9e5",
        )
        self.assertEqual(
            case["provenance"]["setup_sha256"],
            "68c36eedeb7daf07516db93ca0ac0263bf3859d42549f7d490b1f074475ffc9d",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "1017cbd4cd0a42bc4cd14f23c24adf54e47518ad58d7564b0eecf8badb1c6dae",
        )
        self.assertIsNone(case["verifier"])
        self.assertEqual(cases.get_case("C09", verify=True)["verifier"], cases.get_case("C06", verify=True)["verifier"])


class CommittedCopyDefinitionTests(unittest.TestCase):
    def test_c10_copies_committed_setup_as_distinct_phase(self):
        case = cases.get_case("C10")
        base = cases.get_case("C09")
        self.assertEqual(case["body"], "cp big big2")
        self.assertEqual(case["starting_view"], "committed-base")
        self.assertEqual(case["setup"], base["setup"])
        self.assertEqual(case["setup_argv"], base["setup_argv"])
        self.assertEqual(case["provenance"]["setup_sha256"], base["provenance"]["setup_sha256"])
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "60f896e83f6fa71e1713ddd4ffd7e8c14d1ecf17bddb5f191f0ea4f2bdebabed",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "a4c2ff11f48eb28acd3cb6c1881a5376261e34f1e74c73887008a8885d5ed84f",
        )
        self.assertIsNone(case["verifier"])
        self.assertEqual(cases.get_case("C10", verify=True)["verifier"], cases.get_case("C07", verify=True)["verifier"])


class CommittedOverwriteDefinitionTests(unittest.TestCase):
    def test_c11_preserves_zero_over_zero_notrunc(self):
        case = cases.get_case("C11")
        base = cases.get_case("C09")
        self.assertEqual(case["body"], base["setup"] + " conv=notrunc")
        self.assertEqual(case["starting_view"], "committed-base")
        self.assertEqual(case["setup_argv"], base["setup_argv"])
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "b057769c09c98bda3d759364d4857cd2e1eaf64855296d2bf7a7d225a37d2b40",
        )
        self.assertEqual(
            case["provenance"]["setup_sha256"],
            "68c36eedeb7daf07516db93ca0ac0263bf3859d42549f7d490b1f074475ffc9d",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "53077030326a1386f2cf2523f5a850b35feaba2d8fcb1b36e9f40a742be40a0d",
        )
        self.assertIsNone(case["verifier"])
        self.assertEqual(cases.get_case("C11", verify=True)["verifier"], cases.get_case("C06", verify=True)["verifier"])


class GitProofTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.environment = {**os.environ, **cases.ENVIRONMENT}
        self.git("init", "-q")
        self.git("config", "core.filemode", "true")
        for number in range(1, 101):
            (self.root / f"f{number}").write_bytes(f"{number}\n".encode())
        self.git("add", "--all")
        self.git("commit", "-qm", "init")

    def git(self, *arguments):
        return subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "user.email=a@b", "-c", "user.name=a", *arguments],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

    def proof(self):
        return subprocess.run(
            ["/bin/bash", "-o", "pipefail", "-c", cases.get_case("C12", verify=True)["verifier"]],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def test_valid_repository_and_source_hashes(self):
        case = cases.get_case("C12")
        self.assertEqual(case["setup"], "")
        self.assertIsNone(case["verifier"])
        self.assertEqual(
            case["provenance"]["body_sha256"],
            "36c5a7aed5e5a44b18dc0a5de3aa3da3eea3ecac9b8affb81eb8f1c85e021fb0",
        )
        self.assertEqual(
            case["provenance"]["command_sha256"],
            "837c1465ba0066de602ad01f51efe880f08ab2ae4cbbbb65901bdbae9a48559b",
        )
        result = self.proof()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "VERIFY OK\n")

    def test_changed_tracked_content_fails(self):
        (self.root / "f50").write_bytes(b"51\n")
        self.assertNotEqual(self.proof().returncode, 0)

    def test_extra_untracked_file_fails(self):
        (self.root / ".untracked").touch()
        self.assertNotEqual(self.proof().returncode, 0)

    def test_extra_history_fails(self):
        self.git("commit", "--allow-empty", "-qm", "extra")
        result = self.proof()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("commit count", result.stdout)

    def test_changed_executable_metadata_fails(self):
        (self.root / "f50").chmod(0o755)
        result = self.proof()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Git status is not clean", result.stdout)


if __name__ == "__main__":
    unittest.main()
