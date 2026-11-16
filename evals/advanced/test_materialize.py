import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ADVANCED = Path(__file__).resolve().parent
sys.path.insert(0, str(ADVANCED))
import materialize as replay


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(root, bundled=True, archived_entry=True):
    entry = 'INSTRUCTIONS.md' if archived_entry else 'SKILL.md'
    raw = b'\xef\xbb\xbfSynthetic entry\r\nUnicode: caf\xc3\xa9\r\n'
    files = {f'versions/demo/{entry}': raw}
    resources = {'SKILL.md': raw}
    if bundled:
        guide = b'Synthetic reference\r\nno final newline'
        files['versions/demo/references/guide.md'] = guide
        resources['references/guide.md'] = guide
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = [{'resource_path': name, 'sha256': digest(content), 'bytes': len(content)}
                for name, content in sorted(resources.items())]
    bundle = digest(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
    version = {'directory': 'versions/demo', 'entry_file': entry, 'skill_sha256': digest(raw),
               'guidance_mode': 'bundled_guide_injection' if bundled else 'single_file',
               'bundle_sha256': bundle if bundled else None}
    evidence = {'recorded_files_sha256': {name: digest(content) for name, content in files.items()},
                'variants': {'demo': version}}
    (root / 'evidence.json').write_text(json.dumps(evidence), encoding='utf-8')
    return resources


class ReplayHelperChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='replay-helper-audit-')
        self.base = Path(self.temporary.name)
        self.archive = self.base / 'archive'
        self.archive.mkdir()
        self.expected = fixture(self.archive)
        self.original_root = replay.ROOT
        replay.ROOT = self.archive

    def tearDown(self):
        replay.ROOT = self.original_root
        self.temporary.cleanup()

    def reject(self, output, variant='demo', pattern=None):
        with self.assertRaisesRegex(ValueError, pattern or '.'):
            replay.materialize(variant, output)

    def test_01_bundle_preserves_bytes_and_restores_entry_filename(self):
        output = self.base / 'missing-parent' / 'runtime'
        names = replay.materialize('demo', output)
        self.assertEqual(set(names), set(self.expected))
        self.assertEqual({p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}, set(self.expected))
        for name, raw in self.expected.items():
            self.assertEqual((output / name).read_bytes(), raw)
        self.assertFalse((output / 'INSTRUCTIONS.md').exists())

    def test_02_single_file_canonical_entry(self):
        separate = self.base / 'single'
        separate.mkdir()
        expected = fixture(separate, bundled=False, archived_entry=False)
        replay.ROOT = separate
        output = self.base / 'single-output'
        self.assertEqual(replay.materialize('demo', output), ['SKILL.md'])
        self.assertEqual((output / 'SKILL.md').read_bytes(), expected['SKILL.md'])

    def test_03_existing_file_is_not_overwritten(self):
        output = self.base / 'occupied'
        output.write_bytes(b'keep this exact content')
        self.reject(output, pattern='existing paths')
        self.assertEqual(output.read_bytes(), b'keep this exact content')

    def test_04_existing_directory_is_not_modified(self):
        output = self.base / 'occupied-directory'
        output.mkdir()
        (output / 'sentinel').write_bytes(b'unchanged')
        self.reject(output, pattern='existing paths')
        self.assertEqual([p.name for p in output.iterdir()], ['sentinel'])
        self.assertEqual((output / 'sentinel').read_bytes(), b'unchanged')

    def test_05_existing_and_dangling_output_symlinks_are_rejected(self):
        for exists in (True, False):
            target = self.base / f'target-{exists}'
            if exists:
                target.mkdir()
            output = self.base / f'output-link-{exists}'
            output.symlink_to(target, target_is_directory=True)
            self.reject(output, pattern='existing paths')
            self.assertTrue(output.is_symlink())
            self.assertEqual(target.exists(), exists)
            if exists:
                self.assertEqual(list(target.iterdir()), [])

    def test_06_existing_and_dangling_parent_symlinks_are_rejected(self):
        for exists in (True, False):
            target = self.base / f'parent-target-{exists}'
            if exists:
                target.mkdir()
            parent = self.base / f'parent-link-{exists}'
            parent.symlink_to(target, target_is_directory=True)
            output = parent / 'runtime'
            self.reject(output, pattern='parent paths must not be symlinks')
            self.assertEqual(target.exists(), exists)
            self.assertFalse(output.exists())

    def test_07_unknown_variant_fails_without_creating_output(self):
        output = self.base / 'unknown-output'
        self.reject(output, variant='unknown', pattern='Unknown archived variant')
        self.assertFalse(output.exists())

    def test_08_changed_archived_bytes_are_rejected_before_writes(self):
        (self.archive / 'versions/demo/INSTRUCTIONS.md').write_bytes(b'changed')
        output = self.base / 'tampered-output'
        self.reject(output, pattern='Recorded file changed')
        self.assertFalse(output.exists())

    def test_09_source_file_symlink_is_rejected_before_writes(self):
        source = self.archive / 'versions/demo/INSTRUCTIONS.md'
        other = self.archive / 'same-content.txt'
        other.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(other)
        output = self.base / 'source-symlink-output'
        self.reject(output, pattern='traverses a symlink')
        self.assertFalse(output.exists())

    def test_10_source_reference_directory_symlink_is_rejected(self):
        directory = self.archive / 'versions/demo/references'
        moved = self.archive / 'moved-references'
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        output = self.base / 'references-symlink-output'
        self.reject(output, pattern='traverses a symlink')
        self.assertFalse(output.exists())

    def test_11_unrecorded_runtime_reference_is_rejected(self):
        (self.archive / 'versions/demo/references/extra.md').write_bytes(b'extra')
        output = self.base / 'unrecorded-output'
        self.reject(output, pattern='missing from hash inventory')
        self.assertFalse(output.exists())

    def test_12_cli_status_and_messages(self):
        output = self.base / 'cli-output'
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = replay.main(['--variant', 'demo', '--out', str(output)])
        self.assertEqual(code, 0)
        self.assertIn('Copied 2 verified runtime files', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = replay.main(['--variant', 'unknown', '--out', str(self.base / 'invalid-cli')])
        self.assertEqual(code, 1)
        self.assertIn('Unknown archived variant', stderr.getvalue())
        self.assertEqual(stdout.getvalue(), '')
        self.assertFalse((self.base / 'invalid-cli').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
