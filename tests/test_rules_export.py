"""ai/scripts/rules-export.py: public/private split, stable output, git commit of just the export."""
import importlib.machinery
import contextlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
import unittest.mock

SCRIPT = Path(__file__).resolve().parents[1] / 'ai' / 'scripts' / 'rules-export.py'
loader = importlib.machinery.SourceFileLoader('rules_export', str(SCRIPT))
spec = importlib.util.spec_from_loader('rules_export', loader)
re_ = importlib.util.module_from_spec(spec)
loader.exec_module(re_)

BODY = 'Rule: do the thing.\nSecond line.\nTrigger: x\nCheck: y\nSource: z'


def fake(down=False):
    tasks = {'tasks': [
        {'id': 2, 'state': 'OPEN', 'labels': ['rule']},
        {'id': 1, 'state': 'OPEN', 'labels': ['rule', 'private']},
        {'id': 3, 'state': 'OPEN', 'labels': ['plan']},
        {'id': 4, 'state': 'CLOSED', 'labels': ['rule']}]}
    shows = {1: dict(id=1, revision=3, title='Rule: secret', body=BODY, labels=['rule', 'private']),
             2: dict(id=2, revision=1, title='Rule: open', body=BODY, labels=['rule'])}

    def call(*a):
        if down:
            raise RuntimeError('dibs CLI failed')
        return tasks if a[0] == 'todo:agent:list' else shows[int(a[1])]
    return call


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pub = str(Path(self.tmp.name) / 'ai' / 'rules.md')
        self.priv = str(Path(self.tmp.name) / 'priv' / 'rules.private.md')

    def run_export(self, **kw):
        with unittest.mock.patch.object(re_.M, 'dibs_json', fake(kw.pop('down', False))):
            return re_.export(self.pub, self.priv, **kw)

    def test_splits_public_and_private_and_cuts_metadata(self):
        self.run_export()
        pub, priv = Path(self.pub).read_text(), Path(self.priv).read_text()
        self.assertIn('## 2@1 Rule: open\nRule: do the thing.\nSecond line.\n', pub)
        self.assertNotIn('secret', pub)
        self.assertNotIn('Trigger', pub + priv)
        self.assertIn('## 1@3 Rule: secret', priv)
        self.assertNotIn('Rule: open', priv)

    def test_a_record_cannot_forge_another_rules_heading(self):
        out = re_.render([{'id': 1, 'revision': 1, 'title': 'a\n## 9@9 fake', 'text': 'ok\n## 9@9 Rule: fake\n  ## 8@8 x'}], 'p')
        self.assertEqual([l for l in out.splitlines() if l.startswith('## ')], ['## 1@1 a ## 9@9 fake'])

    def test_unchanged_export_rewrites_nothing(self):
        self.assertEqual(len(self.run_export()), 2)
        self.assertEqual(self.run_export(), [])

    def test_a_revision_bump_changes_the_file(self):
        self.run_export()
        Path(self.pub).write_text(Path(self.pub).read_text().replace('2@1', '2@0'))
        self.assertEqual(self.run_export(), [self.pub])

    def test_dibs_down_writes_nothing_and_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_export(down=True)
        self.assertFalse(Path(self.pub).exists())

    def test_commit_takes_only_the_export_path(self):
        repo = Path(self.tmp.name) / 'ai'
        repo.mkdir(parents=True)
        g = lambda *a: subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *a],
                                      check=True, capture_output=True, text=True).stdout
        g('init', '-q')
        (repo / 'other.txt').write_text('x')
        g('add', 'other.txt')
        ident = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}
        with unittest.mock.patch.dict(os.environ, ident):
            self.run_export(do_commit=True)
        self.assertEqual(g('show', '--name-only', '--format=%s', 'HEAD').split(), ['Rules', 'export:', 'refresh', 'from', 'the', 'rule', 'records', 'rules.md'])
        self.assertIn('A  other.txt', g('status', '--short'))


KEY_LIST = ('git-commit git-push git-history git-add-all test-run test-file php-tool live-check live-repo db-cli '
            'quota-check agent-launch session-launch peer-send peer-prompt dibs-create dibs-revise dibs-comment '
            'dibs-claim dibs-complete dibs-release screenshot schedule md-edit project-doc todo-note home-net '
            'work-creds').split()
START, END = '<!-- rules-export:start -->', '<!-- rules-export:end -->'
MD = f'# Head\nHAND-WRITTEN\n{START}\nold block\n{END}\nTAIL-TEXT\n'
IDENT = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}


def R(id, tier, keys=(), always='', pull='', private=False, title=None, rev=1):
    return dict(id=id, revision=rev, title=title or f'Title {id}', text=f'text {id}', private=private,
                tiers=[tier] if tier else [], keys=list(keys), always=always, pull=pull)


def good_rules():
    return [R(10, 'always', always='Do ten always.'),
            R(20, 'trigger', ['git-commit', 'test-run'], title='Tests  never\n touch it'),
            R(30, 'pull', pull='writing a trailer'),
            R(8888, 'trigger', ['home-net'], private=True, title='SECRET-TITLE-XYZ'),
            R(8889, 'always', always='SECRET-ALWAYS-LINE', private=True)]


def dibs_with(recs):
    """recs: [(id, labels, body)] -> fake dibs_json."""
    tasks = {'tasks': [{'id': i, 'state': 'OPEN', 'labels': l} for i, l, _ in recs]}
    shows = {i: dict(id=i, revision=2, title=f'T{i}', body=b, labels=l) for i, l, b in recs}
    return lambda *a: tasks if a[0] == 'todo:agent:list' else shows[int(a[1])]


class TierParsingTest(unittest.TestCase):
    def gather(self, recs):
        with unittest.mock.patch.object(re_.M, 'dibs_json', dibs_with(recs)):
            return {r['id']: r for r in re_.gather()}

    def test_keys_constant_is_the_28_known_keys(self):
        self.assertEqual(re_.KEYS, frozenset(KEY_LIST))
        self.assertEqual(len(re_.KEYS), 28)
        self.assertIsInstance(re_.KEYS, frozenset)

    def test_gather_parses_tier_keys_always_and_pull(self):
        g = self.gather([
            (1, ['rule', 'tier always'], 'Text one.\nAlways: Do one.\nSource: s'),
            (2, ['rule', 'tier trigger'], 'Text two.\nKeys: git-commit, test-run\nCheck: c'),
            (3, ['rule', 'tier pull', 'private'], 'Text three.\nPull when: writing a trailer')])
        self.assertEqual((g[1]['tiers'], g[1]['always'], g[1]['keys'], g[1]['pull']), (['always'], 'Do one.', [], ''))
        self.assertEqual((g[2]['tiers'], g[2]['keys'], g[2]['always'], g[2]['pull']),
                         (['trigger'], ['git-commit', 'test-run'], '', ''))
        self.assertEqual((g[3]['tiers'], g[3]['pull'], g[3]['private']), (['pull'], 'writing a trailer', True))

    def test_new_metadata_never_reaches_the_exported_text(self):
        g = self.gather([(1, ['rule', 'tier always'], 'Text one.\nSecond.\nAlways: Do one.\nKeys: git-push\nPull when: x')])
        self.assertEqual(g[1]['text'], 'Text one.\nSecond.')
        out = re_.render([g[1]], 'p')
        for word in ('Always:', 'Keys:', 'Pull when:'):
            self.assertNotIn(word, out)

    def test_no_tier_label_gives_empty_tiers_and_two_labels_give_two(self):
        g = self.gather([(1, ['rule'], 'x'), (2, ['rule', 'tier always', 'tier pull'], 'x')])
        self.assertEqual(g[1]['tiers'], [])
        self.assertEqual(sorted(g[2]['tiers']), ['always', 'pull'])


class ValidateTest(unittest.TestCase):
    def test_all_three_valid_tiers_pass(self):
        self.assertEqual(re_.validate(good_rules()), {})
        self.assertEqual(re_.validate([]), {})

    def errors(self, rule):
        return re_.validate([R(1, 'always', always='ok'), rule]).get(rule['id'])

    def test_each_failure_is_reported_under_its_id_and_only_its_id(self):
        bad = [R(2, None),
               dict(R(3, 'always', always='a'), tiers=['always', 'trigger'], keys=['git-push']),
               R(4, 'always', always=''),
               R(5, 'trigger', []),
               R(6, 'trigger', ['not-a-key']),
               R(7, 'trigger', ['git-push', 'not-a-key']),
               R(8, 'pull', pull=''),
               R(9, 'always', ['bogus'], always='ok'),
               R(11, 'pull', ['bogus'], pull='when')]
        got = re_.validate([R(1, 'always', always='ok')] + bad)
        self.assertEqual(sorted(got), [2, 3, 4, 5, 6, 7, 8, 9, 11])
        for errs in got.values():
            self.assertTrue(errs and all(isinstance(e, str) and e for e in errs))

    def test_two_tier_labels_even_if_each_is_satisfied_fail(self):
        self.assertTrue(self.errors(dict(R(3, 'always', ['git-push'], always='a'), tiers=['always', 'trigger'])))

    def test_one_rule_can_collect_several_errors(self):
        self.assertGreaterEqual(len(self.errors(dict(R(3, None, ['bogus']), tiers=[]))), 2)

    def test_trigger_with_one_good_and_one_unknown_key_fails(self):
        self.assertTrue(self.errors(R(7, 'trigger', ['git-push', 'nope'])))

    def test_private_rules_are_validated_too(self):
        self.assertIn(5, re_.validate([R(5, 'trigger', [], private=True)]))


class RenderTest(unittest.TestCase):
    def test_render_always_sorted_by_id_and_only_always_tier(self):
        rules = [R(30, 'always', always='Third.'), R(5, 'always', always='First.'), R(7, 'trigger', ['git-push']),
                 R(9, 'pull', pull='w')]
        self.assertEqual(re_.render_always(rules), '- First.\n- Third.')

    def test_pull_line_is_exact_and_has_no_literal_dibs_reference(self):
        self.assertEqual(re_.PULL_LINE,
                         "Pull: when an index line below applies and its text isn't in your context, run "
                         "`grep -h -A3 '^## <id>@' ~/dotfiles/ai/rules.md`, or `todo_show <id>` with `fullBody`.")
        self.assertIsNone(re.search(r'todo_show\s+\d', re_.PULL_LINE))

    def test_render_index_lines_sorted_without_revisions_or_always_rules(self):
        rules = [R(30, 'pull', pull='writing a trailer', rev=7), R(20, 'trigger', ['git-commit', 'test-run'], title='Tests  never\n touch it', rev=9),
                 R(10, 'always', always='x'), R(5, 'trigger', ['db-cli'], title='Stale data')]
        self.assertEqual(re_.render_index(rules),
                         '- 5 [db-cli] Stale data\n- 20 [git-commit, test-run] Tests never touch it\n'
                         '- 30 [pull: writing a trailer] Title 30')

    def test_render_index_of_nothing_is_empty(self):
        self.assertEqual(re_.render_index([R(1, 'always', always='a')]).strip(), '')

    def test_render_block_layout(self):
        rules = good_rules()[:3]
        block = re_.render_block(rules)
        self.assertTrue(block.startswith('### Always-on rules\n- Do ten always.\n'))
        self.assertTrue(block.endswith('\n'))
        self.assertLess(block.index('### Always-on rules'), block.index('### Rule index'))
        self.assertLess(block.index('### Rule index'), block.index(re_.PULL_LINE))
        self.assertLess(block.index(re_.PULL_LINE), block.index('- 20 [git-commit, test-run]'))
        self.assertIn('- 30 [pull: writing a trailer] Title 30', block)
        self.assertNotIn('- 10 [', block)

    def test_render_triggers_is_sorted_json_indent_one_with_trailing_newline(self):
        rules = [R(20, 'trigger', ['test-run', 'git-commit']), R(5, 'trigger', ['git-commit']),
                 R(9, 'always', ['git-push'], always='a'), R(30, 'pull', ['test-run'], pull='w')]
        out = re_.render_triggers(rules)
        want = {'git-commit': [5, 20], 'git-push': [9], 'test-run': [20, 30]}
        self.assertEqual(json.loads(out), want)
        self.assertEqual(out, json.dumps(want, indent=1, sort_keys=True) + '\n')


class ReplaceBlockTest(unittest.TestCase):
    def test_replaces_only_between_markers_and_keeps_them(self):
        out = re_.replace_block(MD, 'NEW\nBLOCK\n')
        self.assertTrue(out.startswith(f'# Head\nHAND-WRITTEN\n{START}'))
        self.assertTrue(out.endswith(f'{END}\nTAIL-TEXT\n'))
        self.assertIn('NEW\nBLOCK', out)
        self.assertNotIn('old block', out)
        self.assertEqual(out.count(START), 1)
        self.assertEqual(out.count(END), 1)

    def test_is_idempotent(self):
        once = re_.replace_block(MD, 'NEW\n')
        self.assertEqual(re_.replace_block(once, 'NEW\n'), once)

    def test_missing_or_repeated_markers_raise_value_error(self):
        for text in ('no markers\n', f'{START}\nonly start\n', f'only end\n{END}\n',
                     MD + f'{START}\nx\n{END}\n', MD + f'{END}\n', MD + f'{START}\n', ''):
            with self.subTest(text=text), self.assertRaises(ValueError):
                re_.replace_block(text, 'x')


class TierExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.pub, self.priv = str(t / 'ai' / 'rules.md'), str(t / 'priv' / 'rules.private.md')
        self.rmd, self.pmd = t / 'RULES.md', t / 'priv' / 'CLAUDE.private.md'
        self.trig, self.ptrig = t / 'rules-triggers.json', t / 'priv' / 'rules-triggers.private.json'
        self.rmd.write_text(MD)
        self.pmd.parent.mkdir(parents=True, exist_ok=True)
        self.pmd.write_text(MD.replace('HAND-WRITTEN', 'PRIVATE-HAND'))
        self.problems = []

    def kw(self, **over):
        kw = dict(rules_md=str(self.rmd), private_md=str(self.pmd), triggers=str(self.trig),
                  private_triggers=str(self.ptrig), problems=self.problems)
        kw.update(over)
        return kw

    def export(self, rules=None, **over):
        return re_.export(self.pub, self.priv, rules=good_rules() if rules is None else rules, **self.kw(**over))

    def all_paths(self):
        return {self.pub, self.priv, str(self.rmd), str(self.pmd), str(self.trig), str(self.ptrig)}

    def test_first_export_writes_all_six_then_second_writes_nothing(self):
        self.assertEqual(set(self.export()), self.all_paths())
        self.assertEqual(self.problems, [])
        self.assertEqual(self.export(), [])
        self.assertEqual(self.problems, [])

    def test_public_outputs_get_public_rules_only(self):
        self.export()
        md, trig = self.rmd.read_text(), json.loads(self.trig.read_text())
        self.assertIn('HAND-WRITTEN', md)
        self.assertIn('TAIL-TEXT', md)
        self.assertIn('- Do ten always.', md)
        self.assertIn('- 20 [git-commit, test-run] Tests never touch it', md)
        self.assertIn('- 30 [pull: writing a trailer] Title 30', md)
        self.assertEqual(trig, {'git-commit': [20], 'test-run': [20]})

    def test_private_rules_never_appear_in_public_outputs(self):
        self.export()
        for path in (self.pub, str(self.rmd), str(self.trig)):
            text = Path(path).read_text()
            for needle in ('SECRET', '8888', '8889', 'home-net', 'text 8888'):
                self.assertNotIn(needle, text, path)

    def test_private_outputs_hold_the_private_rules(self):
        self.export()
        md, trig = self.pmd.read_text(), json.loads(self.ptrig.read_text())
        self.assertIn('PRIVATE-HAND', md)
        self.assertIn('- SECRET-ALWAYS-LINE', md)
        self.assertIn('- 8888 [home-net] SECRET-TITLE-XYZ', md)
        self.assertEqual(trig, {'home-net': [8888]})
        self.assertNotIn('Do ten always', md)
        self.assertIn('## 8888@1 SECRET-TITLE-XYZ', Path(self.priv).read_text())

    def test_none_means_skip(self):
        out = self.export(rules_md=None, private_md=None, triggers=None, private_triggers=None)
        self.assertEqual(set(out), {self.pub, self.priv})
        self.assertEqual(self.rmd.read_text(), MD)
        self.assertFalse(self.trig.exists())

    def test_a_revision_bump_alone_rewrites_only_rules_md(self):
        self.export()
        rules = good_rules()
        rules[1]['revision'] = 5
        self.assertEqual(self.export(rules), [self.pub])

    def test_a_changed_always_line_rewrites_only_the_blocks(self):
        self.export()
        rules = good_rules()
        rules[0]['always'] = 'Changed.'
        self.assertEqual(self.export(rules), [str(self.rmd)])

    def test_validation_failure_still_exports_rules_md_but_writes_none_of_the_four(self):
        rules = good_rules() + [R(742, 'trigger', [])]
        out = self.export(rules)
        self.assertEqual(set(out), {self.pub, self.priv})
        self.assertIn('## 742@1 Title 742', Path(self.pub).read_text())
        self.assertEqual(self.rmd.read_text(), MD)
        self.assertEqual(self.pmd.read_text(), MD.replace('HAND-WRITTEN', 'PRIVATE-HAND'))
        self.assertFalse(self.trig.exists() or self.ptrig.exists())
        self.assertEqual(len(self.problems), 1)
        self.assertTrue(self.problems[0].startswith('742:'), self.problems)

    def test_every_failing_rule_is_reported(self):
        self.export(good_rules() + [R(1, None), R(2, 'pull', pull=''), R(3, 'trigger', ['bogus'])])
        self.assertEqual(sorted(p.split(':')[0] for p in self.problems), ['1', '2', '3'])

    def test_a_private_rule_failing_blocks_the_public_outputs_too(self):
        out = self.export(good_rules() + [R(9000, 'always', always='', private=True)])
        self.assertEqual(set(out), {self.pub, self.priv})
        self.assertEqual(self.rmd.read_text(), MD)
        self.assertFalse(self.trig.exists())
        self.assertTrue(any(p.startswith('9000:') for p in self.problems))

    def test_failure_without_a_problems_list_does_not_raise(self):
        out = re_.export(self.pub, self.priv, rules=good_rules() + [R(1, None)], rules_md=str(self.rmd))
        self.assertEqual(set(out), {self.pub, self.priv})

    def test_missing_marker_writes_none_of_the_four_and_reports(self):
        self.rmd.write_text('# no markers here\n')
        out = self.export()
        self.assertEqual(set(out), {self.pub, self.priv})
        self.assertEqual(self.rmd.read_text(), '# no markers here\n')
        self.assertFalse(self.trig.exists() or self.ptrig.exists())
        self.assertEqual(self.pmd.read_text(), MD.replace('HAND-WRITTEN', 'PRIVATE-HAND'))
        self.assertTrue(self.problems)

    def test_missing_marker_in_the_private_file_blocks_the_public_ones_too(self):
        self.pmd.write_text('nothing\n')
        self.export()
        self.assertEqual(self.rmd.read_text(), MD)
        self.assertFalse(self.trig.exists())
        self.assertTrue(self.problems)

    def test_an_empty_group_still_renders_valid_files(self):
        self.export([r for r in good_rules() if not r['private']])
        self.assertEqual(json.loads(self.ptrig.read_text()) if self.ptrig.exists() else {}, {})


class DirtyFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.rmd, self.trig, self.pub = self.repo / 'RULES.md', self.repo / 'triggers.json', self.repo / 'rules.md'
        self.priv = str(Path(self.tmp.name) / 'outside' / 'rules.private.md')
        patcher = unittest.mock.patch.dict(os.environ, IDENT)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.g('init', '-q')
        self.rmd.write_text(MD)
        self.g('add', 'RULES.md')
        self.g('commit', '-qm', 'base')

    def g(self, *a):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *a],
                              check=True, capture_output=True, text=True).stdout

    def export(self, **kw):
        return re_.export(str(self.pub), self.priv, rules=[r for r in good_rules() if not r['private']],
                          rules_md=str(self.rmd), triggers=str(self.trig), **kw)

    def test_clean_tracked_file_is_written_and_committed_with_the_others(self):
        out = self.export(do_commit=True)
        self.assertIn(str(self.rmd), out)
        self.assertIn(str(self.trig), out)
        self.assertEqual(self.g('status', '--porcelain').strip(), '')
        self.assertEqual(self.g('log', '--name-only', '--format=', '--', 'RULES.md').split(), ['RULES.md', 'RULES.md'])
        self.assertIn('triggers.json', self.g('ls-files'))

    def test_dirty_file_is_neither_written_nor_committed(self):
        dirty = MD + 'WIP by another session\n'
        self.rmd.write_text(dirty)
        out = self.export(do_commit=True)
        self.assertNotIn(str(self.rmd), out)
        self.assertEqual(self.rmd.read_text(), dirty)
        self.assertIn(' M RULES.md', self.g('status', '--porcelain'))
        self.assertNotIn('WIP', self.g('log', '-p', '--format=%s'))
        self.assertEqual(self.g('log', '--name-only', '--format=', '--', 'RULES.md').split(), ['RULES.md'])

    def test_other_generated_files_are_still_written_and_committed_when_the_md_is_dirty(self):
        self.rmd.write_text(MD + 'WIP\n')
        out = self.export(do_commit=True)
        self.assertIn(str(self.trig), out)
        self.assertIn(str(self.pub), out)
        self.assertIn('triggers.json', self.g('ls-files'))
        self.assertEqual(self.g('status', '--porcelain'), ' M RULES.md\n')

    def test_once_clean_again_the_next_run_writes_it(self):
        self.rmd.write_text(MD + 'WIP\n')
        self.export(do_commit=True)
        self.g('add', 'RULES.md')
        self.g('commit', '-qm', 'wip done')
        out = self.export(do_commit=True)
        self.assertIn(str(self.rmd), out)
        self.assertIn('- Do ten always.', self.rmd.read_text())

    def test_without_do_commit_a_dirty_file_is_written(self):
        self.rmd.write_text(MD + 'WIP\n')
        self.assertIn(str(self.rmd), self.export())
        self.assertIn('- Do ten always.', self.rmd.read_text())


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.paths = dict(public=str(t / 'rules.md'), private=str(t / 'rules.private.md'),
                          rules_md=str(t / 'RULES.md'), private_md=str(t / 'PRIV.md'),
                          triggers=str(t / 'trig.json'), private_triggers=str(t / 'trig.private.json'))
        Path(self.paths['rules_md']).write_text(MD)
        Path(self.paths['private_md']).write_text(MD)

    def check(self, rules=None):
        return re_.check(rules=good_rules() if rules is None else rules, **self.paths)

    def export(self):
        a = self.paths
        return re_.export(a['public'], a['private'], rules=good_rules(), rules_md=a['rules_md'],
                          private_md=a['private_md'], triggers=a['triggers'], private_triggers=a['private_triggers'])

    def test_before_any_export_everything_drifts_and_nothing_is_written(self):
        mtimes = {p: os.stat(p).st_mtime_ns for p in (self.paths['rules_md'], self.paths['private_md'])}
        self.assertEqual(set(self.check()), set(self.paths.values()))
        for key in ('public', 'private', 'triggers', 'private_triggers'):
            self.assertFalse(Path(self.paths[key]).exists(), key)
        self.assertEqual(Path(self.paths['rules_md']).read_text(), MD)
        self.assertEqual(mtimes, {p: os.stat(p).st_mtime_ns for p in mtimes})

    def test_after_export_there_is_no_drift(self):
        self.export()
        self.assertEqual(self.check(), [])

    def test_a_hand_edit_of_one_file_is_the_only_drift(self):
        self.export()
        p = Path(self.paths['triggers'])
        p.write_text(p.read_text().replace('20', '21'))
        before = p.read_text()
        self.assertEqual(self.check(), [self.paths['triggers']])
        self.assertEqual(p.read_text(), before)

    def test_a_changed_rule_drifts_the_generated_and_block_files(self):
        self.export()
        rules = good_rules()
        rules[0]['always'] = 'Changed.'
        self.assertEqual(self.check(rules), [self.paths['rules_md']])


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.p = dict(public=t / 'rules.md', private=t / 'priv.md', rules_md=t / 'RULES.md', private_md=t / 'PRIV.md',
                      triggers=t / 'trig.json', private_triggers=t / 'trigp.json')
        self.p['rules_md'].write_text(MD)
        self.p['private_md'].write_text(MD)
        self.good = [(10, ['rule', 'tier always'], 'Ten.\nAlways: Do ten.'),
                     (20, ['rule', 'tier trigger'], 'Twenty.\nKeys: git-commit'),
                     (8888, ['rule', 'private', 'tier trigger'], 'Secret.\nKeys: home-net')]

    def main(self, recs, *extra, down=False):
        argv = ['x', '--public', str(self.p['public']), '--private', str(self.p['private']),
                '--rules-md', str(self.p['rules_md']), '--private-md', str(self.p['private_md']),
                '--triggers', str(self.p['triggers']), '--private-triggers', str(self.p['private_triggers']), *extra]
        fake = dibs_with(recs)
        if down:
            def fake(*a):
                raise RuntimeError('dibs CLI failed')
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.object(re_.M, 'dibs_json', fake), unittest.mock.patch('sys.argv', argv), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = re_.main()
        return code, out.getvalue(), err.getvalue()

    def test_export_exits_0_and_writes_everything(self):
        code, out, err = self.main(self.good)
        self.assertEqual((code, err), (0, ''))
        for k in ('public', 'private', 'triggers', 'private_triggers'):
            self.assertTrue(self.p[k].exists(), k)
        self.assertIn('- Do ten.', self.p['rules_md'].read_text())

    def test_check_exits_1_on_drift_and_writes_nothing(self):
        code, out, err = self.main(self.good, '--check')
        self.assertEqual(code, 1)
        self.assertFalse(self.p['public'].exists() or self.p['triggers'].exists())
        self.assertEqual(self.p['rules_md'].read_text(), MD)

    def test_check_exits_0_when_in_sync(self):
        self.main(self.good)
        self.assertEqual(self.main(self.good, '--check')[0], 0)

    def test_dibs_unreachable_exits_2_and_writes_nothing(self):
        code, out, err = self.main(self.good, down=True)
        self.assertEqual(code, 2)
        self.assertFalse(self.p['public'].exists())

    def test_validation_failure_exits_3_prints_each_problem_and_still_exports_rules_md(self):
        recs = self.good + [(742, ['rule', 'tier trigger'], 'Bad.'), (743, ['rule'], 'No tier.')]
        code, out, err = self.main(recs)
        self.assertEqual(code, 3)
        self.assertTrue(self.p['public'].exists())
        self.assertIn('742', err)
        self.assertIn('743', err)
        self.assertEqual(self.p['rules_md'].read_text(), MD)
        self.assertFalse(self.p['triggers'].exists())

    def test_missing_marker_exits_3(self):
        self.p['rules_md'].write_text('no markers\n')
        code, out, err = self.main(self.good)
        self.assertEqual(code, 3)
        self.assertTrue(self.p['public'].exists())
        self.assertFalse(self.p['triggers'].exists())


if __name__ == '__main__':
    unittest.main()
