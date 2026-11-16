"""Synthetic transport tests; these do not invoke a model."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class AdapterFailures(unittest.TestCase):
    def invoke(self, behavior):
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary) / "codex"
            fake.write_text("#!" + sys.executable + "\nimport pathlib,sys\n" + behavior)
            fake.chmod(0o755)
            environment = dict(os.environ, PATH=temporary + os.pathsep + os.environ.get("PATH", ""))
            return subprocess.run([sys.executable, str(Path(__file__).with_name("codex_adapter.py"))],
                                  input=b"Example prompt", capture_output=True, env=environment)

    def test_diagnostics_cannot_pollute_answer(self):
        result = self.invoke("p=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1])\np.write_bytes(b'Exact answer\\n')\nprint('transport log')\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"Exact answer\n")

    def test_success_without_response_is_a_failure(self):
        result = self.invoke("print('connected but no answer')\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")

    def test_transport_failure_cannot_pass(self):
        result = self.invoke("print('authentication failed',file=sys.stderr)\nsys.exit(3)\n")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, b"")

    def test_default_workspace_does_not_expose_answer_keys(self):
        result = self.invoke("work=pathlib.Path(sys.argv[sys.argv.index('--cd')+1])\nassert work.is_dir() and not list(work.iterdir())\np=pathlib.Path(sys.argv[sys.argv.index('--output-last-message')+1])\np.write_bytes(b'isolated workspace')\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"isolated workspace")


if __name__ == "__main__":
    unittest.main()
