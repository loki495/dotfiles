"""ai/scripts/lessons-export.py: Dibs knowledge lessons -> the JSON cache the rule-inject hook reads.

The Dibs CLI is a stub script that prints canned JSON by subcommand and logs its arguments. Nothing touches a
real Dibs, Docker or the real home.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'lessons-export.py'
STUB = '''#!{python}
import json, os, sys
args = sys.argv[1:]
with open(os.environ['STUB_LOG'], 'a') as f:
    f.write(json.dumps(args) + '\\n')
cfg = json.load(open(os.environ['STUB_CFG']))
for name, key in (('todo:agent:list', 'list'), ('todo:agent:show', 'show')):
    if name in args:
        i = args.index(name)
        if key == 'list':
            out, rc = cfg['list'], cfg.get('list_rc', 0)
        else:
            tid = args[i + 1]
            out, rc = cfg['show'].get(tid, ''), 0 if tid in cfg['show'] else 1
        sys.stdout.write(out if isinstance(out, str) else json.dumps(out))
        sys.exit(rc)
sys.exit(2)
'''


def task(id, labels=('lesson', 'trigger git commit'), state='OPEN', title='Personal Projects', group='dotfiles'):
    return {'id': id, 'state': state, 'labels': list(labels), 'title': f'task {id}',
            'memberships': [{'title': title, 'group': group}]}


def body(summary='Run Pint first', hits=None, seen=None, extra=''):
    lines = ['# Lesson', 'Some intro text.']
    if summary is not None:
        lines.append(f'- Summary: {summary}')
    if hits is not None:
        lines.append(f'- Hits: {hits}')
    if seen is not None:
        lines.append(f'- Last seen: {seen}')
    lines.append(extra)
    return {'body': '\n'.join(lines)}


class ExportBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(self.tmp)]))
        (self.tmp / 'out').mkdir()
        self.cache = self.tmp / 'out' / 'lessons.json'
        self.stub = self.tmp / 'dibs-stub'
        self.stub.write_text(STUB.format(python=sys.executable))
        os.chmod(self.stub, 0o755)
        self.log = self.tmp / 'stub.log'
        self.cfg = self.tmp / 'cfg.json'
        self.env = {**os.environ, 'HOME': str(self.tmp), 'DIBS_CLI': f'{self.stub} php artisan',
                    'LESSON_CACHE': str(self.cache), 'STUB_LOG': str(self.log), 'STUB_CFG': str(self.cfg)}

    def run_export(self, tasks=None, show=None, list_raw=None, list_rc=0, env=None):
        cfg = {'list': list_raw if list_raw is not None else {'tasks': tasks or []},
               'list_rc': list_rc, 'show': {str(k): v for k, v in (show or {}).items()}}
        self.cfg.write_text(json.dumps(cfg))
        return subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env or self.env)

    def run_ok(self, *a, **kw):
        proc = self.run_export(*a, **kw)
        self.assertEqual((proc.returncode, proc.stderr), (0, ''))
        return json.loads(self.cache.read_text())

    def by_id(self, data):
        return {entry['id']: entry for entry in data['lessons']}

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []


class SelectionTest(ExportBase):
    """Group: which tasks become lessons."""

    def test_open_lesson_with_trigger_is_exported_with_all_fields(self):
        data = self.run_ok([task(7, labels=['lesson', 'trigger git commit', 'trigger test run', 'other'])],
                           {7: body('Run Pint first', hits=4, seen='2026-10-30')})
        entry = self.by_id(data)[7]
        self.assertEqual({k: entry[k] for k in ('id', 'summary', 'group', 'area', 'hits', 'last_seen')},
                         {'id': 7, 'summary': 'Run Pint first', 'group': 'dotfiles', 'area': 'Personal Projects',
                          'hits': 4, 'last_seen': '2026-10-30'})
        self.assertEqual(sorted(entry['triggers']), ['git commit', 'test run'])
        self.assertLess(abs(data['generated'] - time.time()), 120)

    def test_draft_lessons_are_excluded(self):
        data = self.run_ok([task(1, labels=['lesson', 'draft', 'trigger git commit']), task(2)],
                           {1: body('draft'), 2: body('real')})
        self.assertEqual(list(self.by_id(data)), [2])

    def test_non_open_tasks_are_excluded(self):
        data = self.run_ok([task(1, state='CLOSED'), task(2, state='DONE'), task(3, state='OPEN')],
                           {1: body('a'), 2: body('b'), 3: body('c')})
        self.assertEqual(list(self.by_id(data)), [3])

    def test_lesson_without_a_trigger_label_is_excluded(self):
        data = self.run_ok([task(1, labels=['lesson']), task(2, labels=['lesson', 'triggers x', 'trigger']),
                            task(3)], {1: body('a'), 2: body('b'), 3: body('c')})
        self.assertNotIn(1, self.by_id(data))
        self.assertIn(3, self.by_id(data))

    def test_task_without_the_lesson_label_is_excluded(self):
        data = self.run_ok([task(1, labels=['guide', 'trigger git commit']), task(2)],
                           {1: body('a'), 2: body('b')})
        self.assertEqual(list(self.by_id(data)), [2])

    def test_show_is_only_called_for_kept_tasks(self):
        self.run_ok([task(1, state='CLOSED'), task(2, labels=['lesson']), task(3)], {1: body('a'), 2: body('b'),
                                                                                     3: body('c')})
        shows = [c for c in self.calls() if 'todo:agent:show' in c]
        self.assertEqual([c[c.index('todo:agent:show') + 1] for c in shows], ['3'])

    def test_list_call_asks_for_knowledge_through_the_cli_prefix(self):
        self.run_ok([])
        first = self.calls()[0]
        self.assertEqual(first[:2], ['php', 'artisan'])  # DIBS_CLI is shlex-split into a prefix
        self.assertEqual(first[2], 'todo:agent:list')
        self.assertIn('--knowledge', first)

    def test_no_qualifying_tasks_writes_an_empty_list(self):
        data = self.run_ok([task(1, state='CLOSED')], {})
        self.assertEqual(data['lessons'], [])

    def test_many_lessons_are_all_exported(self):
        ids = list(range(10, 40))
        data = self.run_ok([task(i) for i in ids], {i: body(f's{i}') for i in ids})
        self.assertEqual(sorted(self.by_id(data)), ids)


class BodyParsingTest(ExportBase):
    """Group: reading Summary, Hits and Last seen out of the task body."""

    def export_body(self, text):
        data = self.run_ok([task(1)], {1: {'body': text}})
        return self.by_id(data).get(1)

    def test_separate_lines(self):
        e = self.export_body('Intro\n- Summary: Do the thing\n- Hits: 12\nLast seen: 2026-11-01\n')
        self.assertEqual((e['summary'], e['hits'], e['last_seen']), ('Do the thing', 12, '2026-11-01'))

    def test_guide_format_on_one_line_with_and_and_period(self):
        e = self.export_body('- Summary: Do the thing\n- Hits: 5, and Last seen: 2026-10-02.\n')
        self.assertEqual((e['hits'], e['last_seen']), (5, '2026-10-02'))

    def test_one_line_without_dash_or_and(self):
        e = self.export_body('- Summary: Do the thing\nHits: 3, Last seen: 2026-11-01\n')
        self.assertEqual((e['hits'], e['last_seen']), (3, '2026-11-01'))

    def test_hits_and_last_seen_default_when_absent(self):
        e = self.export_body('- Summary: Only a summary\n')
        self.assertEqual((e['hits'], e['last_seen']), (0, ''))
        self.assertIsInstance(e['hits'], int)

    def test_summary_keeps_its_text_and_is_trimmed(self):
        e = self.export_body('x\n- Summary:   Keep: colons, and "quotes"   \n- Hits: 1\n')
        self.assertEqual(e['summary'], 'Keep: colons, and "quotes"')

    def test_lesson_without_a_summary_line_is_skipped_but_others_stay(self):
        data = self.run_ok([task(1), task(2)], {1: {'body': 'No summary here\n- Hits: 4\n'}, 2: body('ok')})
        self.assertEqual(list(self.by_id(data)), [2])

    def test_empty_or_missing_body_is_skipped(self):
        data = self.run_ok([task(1), task(2), task(3)], {1: {'body': ''}, 2: {}, 3: body('ok')})
        self.assertEqual(list(self.by_id(data)), [3])


class WriteTest(ExportBase):
    """Group: atomic cache write and failure behaviour (a failed export never damages the old cache)."""

    OLD = json.dumps({'generated': 1, 'lessons': [{'id': 99, 'summary': 'old', 'triggers': ['git commit'],
                                                    'group': 'g', 'area': 'a', 'hits': 1, 'last_seen': ''}]})

    def leftovers(self):
        return sorted(p.name for p in (self.tmp / 'out').iterdir() if not p.name.endswith('.lock'))

    def test_cache_is_replaced_and_no_temp_file_is_left_behind(self):
        self.cache.write_text(self.OLD)
        data = self.run_ok([task(1)], {1: body('new')})
        self.assertEqual(list(self.by_id(data)), [1])
        self.assertEqual(self.leftovers(), ['lessons.json'])

    def test_cache_is_created_when_missing(self):
        self.run_ok([task(1)], {1: body('new')})
        self.assertTrue(self.cache.exists())

    def test_failing_list_call_keeps_the_old_cache_and_exits_nonzero(self):
        self.cache.write_text(self.OLD)
        proc = self.run_export(list_raw='{"tasks": []}', list_rc=3)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.cache.read_text(), self.OLD)
        self.assertEqual(self.leftovers(), ['lessons.json'])

    def test_bad_json_from_list_keeps_the_old_cache_and_exits_nonzero(self):
        for raw in ('not json', '', '{"tasks": ', '[1, 2]'):
            self.cache.write_text(self.OLD)
            proc = self.run_export(list_raw=raw)
            self.assertNotEqual(proc.returncode, 0, raw)
            self.assertEqual(self.cache.read_text(), self.OLD, raw)

    def test_failed_first_export_does_not_create_a_cache(self):
        proc = self.run_export(list_raw='nope')
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(self.cache.exists())

    def test_missing_cli_exits_nonzero_and_keeps_the_old_cache(self):
        self.cache.write_text(self.OLD)
        env = {**self.env, 'DIBS_CLI': str(self.tmp / 'no-such-cli') + ' php artisan'}
        proc = self.run_export([], env=env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.cache.read_text(), self.OLD)


if __name__ == '__main__':
    unittest.main()
