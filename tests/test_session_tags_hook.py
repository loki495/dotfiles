"""ai/hooks/session-tags.py: adds the project tag and nags for a role tag, in two hook events.

SessionStart (startup/resume) starts a detached worker and prints nothing; the worker (run inline
here via SESSION_TAGS_FOREGROUND=1) writes its message to <dir>/<safe session_id>.msg, and the
UserPromptSubmit event delivers and deletes that file. Tests set SESSION_TAGS_DIR to a temp dir.

Intent of the groups:
- Gate: acts only on SessionStart with source startup/resume; every other shape (junk stdin, no
  target, untracked session, failing/hanging/missing binary) is silent and exits 0.
- Ready: the worker retries the first read until it succeeds or SESSION_TAGS_READY passes.
- MsgFile: location, sanitised name, stale cleanup. Prompt: delivery once, never calls sessioneer.
- Detached: without FOREGROUND SessionStart returns at once even when sessioneer hangs.
- Race: on startup an empty tag list is re-read for up to $SESSION_TAGS_WAIT seconds; resume never waits.
- Project: derived from the main repo (worktrees resolve to it), normalized, never duplicated.
- Role and add: worker is inferred from the title; the add call has one exact argv; a failed add and
  a missing role are reported in one JSON object; a known role with a good add prints nothing.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'ai' / 'hooks' / 'session-tags.py'

ROLE_TAIL = ('No role tag: add one with `sessioneer --tag-add <role>`: worker, orchestrator, curator, '
             'handoff receiver, a persona name, or interactive when Andres drives this session (rule 2302).')

STUB = '''#!/usr/bin/env python3
import json, os, sys, time
CFG, CALLS, COUNT = {cfg!r}, {calls!r}, {count!r}
argv = sys.argv[1:]
with open(CALLS, 'a') as f:
    f.write(json.dumps(argv) + '\\n')
cfg = json.load(open(CFG))
kind = 'show' if '--show' in argv else 'add' if '--tag-add' in argv else 'other'
spec = cfg.get(kind) or {{}}
if isinstance(spec, list):
    n = int(open(COUNT).read()) if os.path.exists(COUNT) else 0
    open(COUNT, 'w').write(str(n + 1))
    spec = spec[min(n, len(spec) - 1)]
if spec.get('sleep'):
    time.sleep(spec['sleep'])
out = spec.get('out', '')
sys.stdout.write(out if isinstance(out, str) else json.dumps(out))
sys.stderr.write(spec.get('err', ''))
sys.exit(spec.get('rc', 0))
'''


def role_msg(tags):
    return f"Session tags: {', '.join(tags) or 'none'}. " + ROLE_TAIL


def fail_msg(tags, error):
    return f'Session tags: could not add {tags}: {error}. Add them with sessioneer --tag-add (rule 2302).'


def rec(tags, title='some title', workdir=None, **extra):
    r = {'ok': True, 'name': 'claude-headless-x', 'title': title, 'workdir': workdir or '/nonexistent', 'tags': tags}
    r.update(extra)
    return r


class SessionTagsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(self.tmp)]))
        self.calls_file = self.tmp / 'calls'
        self.cfg = self.tmp / 'cfg.json'
        self.bin = self.tmp / 'sessioneer'
        self.bin.write_text(STUB.format(cfg=str(self.cfg), calls=str(self.calls_file),
                                        count=str(self.tmp / 'count')))
        os.chmod(self.bin, 0o755)
        self.genv = {'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
                     'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
                     'GIT_COMMITTER_EMAIL': 't@t'}
        self.msgdir = self.tmp / 'msgs'
        self.plain = self.tmp / 'plain'
        self.plain.mkdir()
        self.repo = self.make_repo('proj')
        self.configure(show=rec([]), add={'out': {'ok': True, 'tags': []}})

    def git(self, *args, cwd=None):
        env = {**os.environ, **self.genv}
        subprocess.run(['git', *args], cwd=cwd, env=env, check=True, capture_output=True)

    def make_repo(self, name):
        path = self.tmp / 'repos' / name
        path.mkdir(parents=True)
        self.git('init', '-q', cwd=path)
        self.git('commit', '-q', '--allow-empty', '-m', 'x', cwd=path)
        return path

    def configure(self, show=None, add=None):
        def norm(spec):
            if isinstance(spec, list):
                return [norm(s) for s in spec]
            return spec if 'out' in spec or 'rc' in spec else {'out': spec}
        cfg = {}
        if show is not None:
            cfg['show'] = norm(show)
        if add is not None:
            cfg['add'] = norm(add)
        self.cfg.write_text(json.dumps(cfg))

    def env(self, self_id='sess-1', bin_path=None, wait='0', path=None, foreground=True, ready='0', edit=None):
        env = {k: v for k, v in os.environ.items()
               if k not in ('SESSIONEER_SELF', 'SESSIONEER_BIN', 'SESSION_TAGS_DIR', 'SESSION_TAGS_FOREGROUND',
                            'SESSION_TAGS_READY', 'SESSION_TAGS_WAIT')}
        env['SESSION_TAGS_WAIT'] = wait
        env['SESSION_TAGS_READY'] = ready
        env['SESSION_TAGS_DIR'] = str(self.msgdir)
        if foreground:
            env['SESSION_TAGS_FOREGROUND'] = '1'
        if edit:
            edit(env)
        env['SESSIONEER_BIN'] = str(bin_path or self.bin)
        if bin_path is False:
            del env['SESSIONEER_BIN']
            env['PATH'] = path
        if self_id is not None:
            env['SESSIONEER_SELF'] = self_id
        return env

    def msg_path(self, sid='sid-9'):
        return self.msgdir / f'{sid}.msg'

    def msg_files(self):
        return sorted(self.msgdir.glob('*.msg')) if self.msgdir.exists() else []

    def payload(self, **over):
        p = {'hook_event_name': 'SessionStart', 'source': 'startup', 'session_id': 'sid-9', 'cwd': str(self.repo)}
        p.update(over)
        return {k: v for k, v in p.items() if v is not None}

    def run_hook(self, payload=None, timeout=25, **kw):
        raw = payload if isinstance(payload, str) else json.dumps(self.payload() if payload is None else payload)
        started = time.monotonic()
        proc = subprocess.run([sys.executable, str(HOOK)], input=raw, capture_output=True, text=True,
                              env=self.env(**kw), timeout=timeout, cwd=str(self.plain))
        return proc, time.monotonic() - started

    def calls(self):
        if not self.calls_file.exists():
            return []
        return [json.loads(line) for line in self.calls_file.read_text().splitlines() if line.strip()]

    def shows(self):
        return [c for c in self.calls() if '--show' in c]

    def adds(self):
        return [c for c in self.calls() if '--tag-add' in c]

    def assert_silent(self, proc):
        """No stdout and no message file written."""
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, '')
        self.assertEqual(self.msg_files(), [])

    def context(self, proc, sid='sid-9'):
        """The message the worker wrote; stdout stays empty on SessionStart."""
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, '')
        self.assertTrue(self.msg_path(sid).exists(), f'no message file; found {self.msg_files()}')
        return self.msg_path(sid).read_text()


class GateTest(SessionTagsTest):
    def test_the_hook_is_executable_python3_with_a_shebang(self):
        self.assertTrue(HOOK.exists(), 'ai/hooks/session-tags.py is missing')
        self.assertTrue(os.access(HOOK, os.X_OK))
        self.assertEqual(HOOK.read_text().splitlines()[0], '#!/usr/bin/env python3')

    def test_startup_and_resume_both_act(self):
        for source in ('startup', 'resume'):
            with self.subTest(source=source):
                if self.calls_file.exists():
                    self.calls_file.unlink()
                proc, _ = self.run_hook(self.payload(source=source))
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(len(self.shows()), 1)

    def test_other_events_and_sources_do_nothing(self):
        for over in ({'hook_event_name': 'Stop'},
                     {'hook_event_name': None}, {'source': 'clear'}, {'source': 'compact'},
                     {'source': None}, {'source': 'Startup'}, {'hook_event_name': 'UserPromptSubmit'}):
            with self.subTest(over=over):
                proc, _ = self.run_hook(self.payload(**over))
                self.assert_silent(proc)
                self.assertEqual(self.calls(), [])

    def test_junk_stdin_is_silent_and_exits_zero(self):
        for raw in ('not json at all', '', '[]', 'null', '"SessionStart"', '{"hook_event_name":'):
            with self.subTest(raw=raw):
                proc, _ = self.run_hook(raw)
                self.assert_silent(proc)
                self.assertEqual(self.calls(), [])

    def test_no_target_exits_silently(self):
        for sid in (None, ''):
            with self.subTest(session_id=sid):
                proc, _ = self.run_hook(self.payload(session_id=sid), self_id=None)
                self.assert_silent(proc)
                self.assertEqual(self.calls(), [])

    def test_an_empty_sessioneer_self_falls_back_to_the_payload_session_id(self):
        proc, _ = self.run_hook(self.payload(), self_id='')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.shows(), [['--show', 'sid-9', '--json']])

    def test_sessioneer_self_wins_over_the_payload_session_id(self):
        self.run_hook(self.payload(), self_id='self-7')
        self.assertEqual(self.shows(), [['--show', 'self-7', '--json']])

    def test_the_payload_session_id_is_the_target_without_sessioneer_self(self):
        self.run_hook(self.payload(), self_id=None)
        self.assertEqual(self.shows(), [['--show', 'sid-9', '--json']])

    def test_the_bin_falls_back_to_sessioneer_on_the_path(self):
        bindir = self.tmp / 'bin'
        bindir.mkdir()
        (bindir / 'sessioneer').write_text(self.bin.read_text())
        os.chmod(bindir / 'sessioneer', 0o755)
        proc, _ = self.run_hook(self.payload(), bin_path=False, path=f'{bindir}:{os.environ["PATH"]}')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.shows(), [['--show', 'sess-1', '--json']])


class UntrackedTest(SessionTagsTest):
    def assert_untracked(self, proc):
        self.assert_silent(proc)
        self.assertEqual(self.adds(), [])

    def test_ok_false_is_untracked(self):
        self.configure(show={'ok': False, 'error': 'no such session'})
        proc, _ = self.run_hook()
        self.assert_untracked(proc)
        self.assertEqual(len(self.shows()), 1)

    def test_ok_missing_or_not_true_is_untracked(self):
        for out in ({'tags': []}, {'ok': 'yes', 'tags': []}, {'ok': 1, 'tags': []}):
            with self.subTest(out=out):
                self.configure(show=out)
                proc, _ = self.run_hook()
                self.assert_untracked(proc)

    def test_nonzero_exit_is_untracked_even_with_an_ok_body(self):
        self.configure(show={'out': rec([]), 'rc': 1})
        proc, _ = self.run_hook()
        self.assert_untracked(proc)

    def test_unparseable_output_is_untracked(self):
        for out in ('not json', '', '[1,2]'):
            with self.subTest(out=out):
                self.configure(show={'out': out})
                proc, _ = self.run_hook()
                self.assert_untracked(proc)

    def test_a_missing_binary_is_untracked(self):
        proc, _ = self.run_hook(bin_path=self.tmp / 'does-not-exist')
        self.assert_untracked(proc)

    def test_a_hanging_binary_is_bounded_by_the_timeout(self):
        self.configure(show={'sleep': 30, 'out': rec([])})
        proc, elapsed = self.run_hook()
        self.assert_untracked(proc)
        self.assertLess(elapsed, 12, 'every sessioneer call needs a timeout of at most 5 s')

    def test_odd_but_ok_records_never_crash_the_hook(self):
        for out in ({'ok': True, 'tags': 'oops'}, {'ok': True, 'tags': None}, {'ok': True}):
            with self.subTest(out=out):
                self.configure(show=out)
                proc, _ = self.run_hook()
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout, '')


class RaceTest(SessionTagsTest):
    def test_startup_rereads_until_tags_appear(self):
        self.configure(show=[rec([]), rec(['project proj', 'interactive'])])
        proc, elapsed = self.run_hook(self.payload(), wait='3')
        self.assert_silent(proc)
        self.assertGreaterEqual(len(self.shows()), 2)
        self.assertEqual(self.adds(), [])
        self.assertLess(elapsed, 4.5)

    def test_the_reread_tags_drive_the_decisions(self):
        self.configure(show=[rec([]), rec(['interactive'])])
        self.run_hook(self.payload(), wait='3')
        self.assertEqual(self.adds(), [['--tag-add', 'project proj', '--session', 'sess-1', '--json']])

    def test_startup_with_tags_reads_once(self):
        self.configure(show=rec(['interactive']))
        self.run_hook(self.payload(), wait='3')
        self.assertEqual(len(self.shows()), 1)

    def test_wait_zero_reads_once(self):
        self.run_hook(self.payload(), wait='0')
        self.assertEqual(len(self.shows()), 1)

    def test_resume_never_rereads(self):
        started = time.monotonic()
        self.run_hook(self.payload(source='resume'), wait='3')
        self.assertEqual(len(self.shows()), 1)
        self.assertLess(time.monotonic() - started, 3)

    def test_it_gives_up_after_the_wait_and_still_adds_the_project(self):
        self.configure(show=rec([]), add={'ok': True, 'tags': ['project proj']})
        proc, elapsed = self.run_hook(self.payload(), wait='1')
        self.assertGreaterEqual(len(self.shows()), 2)
        self.assertLess(elapsed, 4)
        self.assertEqual(self.context(proc), role_msg(['project proj']))

    def test_a_float_wait_is_accepted(self):
        proc, _ = self.run_hook(self.payload(), wait='0.2')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertGreaterEqual(len(self.shows()), 1)


class ProjectTest(SessionTagsTest):
    def added(self):
        adds = self.adds()
        return adds[0][1] if adds else None

    def project_for(self, cwd, tags=()):
        if self.calls_file.exists():
            self.calls_file.unlink()
        self.configure(show=rec(list(tags) + ['interactive']), add={'ok': True, 'tags': []})
        proc, _ = self.run_hook(self.payload(cwd=str(cwd)))
        self.assert_silent(proc)
        return self.added()

    def test_the_project_tag_comes_from_the_repo_name(self):
        self.assertEqual(self.project_for(self.repo), 'project proj')

    def test_a_subdirectory_resolves_to_the_repo(self):
        sub = self.repo / 'a' / 'b'
        sub.mkdir(parents=True)
        self.assertEqual(self.project_for(sub), 'project proj')

    def test_a_worktree_resolves_to_the_main_repo_name(self):
        wt = self.tmp / 'wt-feature-branch'
        self.git('worktree', 'add', '-q', '-b', 'feature', str(wt), cwd=self.repo)
        self.assertEqual(self.project_for(wt), 'project proj')

    def test_a_bare_repo_drops_the_dot_git_suffix(self):
        bare = self.tmp / 'repos' / 'Bare.Thing.git'
        self.git('init', '-q', '--bare', str(bare))
        self.assertEqual(self.project_for(bare), 'project bare thing')

    def test_names_are_lowercased_and_runs_of_other_characters_collapse(self):
        for name, expected in (('My.Repo_Name', 'project my repo name'), ('A--B..C', 'project a b c'),
                               ('Shop.Retrorooms.NET', 'project shop retrorooms net'),
                               ('-lead-trail-', 'project lead trail'), ('x9', 'project x9')):
            with self.subTest(name=name):
                self.assertEqual(self.project_for(self.make_repo(name)), expected)

    def test_long_names_are_cut_to_24_characters(self):
        self.assertEqual(self.project_for(self.make_repo('a' * 30)), 'project ' + 'a' * 24)

    def test_the_cut_is_stripped_when_it_lands_on_a_separator(self):
        repo = self.make_repo('abcdefghijklmnopqrstuvw-xyz')
        self.assertEqual(self.project_for(repo), 'project abcdefghijklmnopqrstuvw')

    def test_a_name_that_normalizes_to_nothing_adds_no_project(self):
        self.assertIsNone(self.project_for(self.make_repo('___')))

    def test_a_non_git_directory_adds_no_project(self):
        self.assertIsNone(self.project_for(self.plain))

    def test_a_missing_directory_adds_no_project(self):
        self.assertIsNone(self.project_for(self.tmp / 'gone'))

    def test_an_existing_project_tag_is_left_alone(self):
        for tags in (['project other'], ['project'], ['project other', 'x']):
            with self.subTest(tags=tags):
                self.assertIsNone(self.project_for(self.repo, tags))

    def test_a_tag_that_merely_contains_project_does_not_count(self):
        self.assertEqual(self.project_for(self.repo, ['myproject x']), 'project proj')

    def test_the_payload_cwd_wins_over_the_record_workdir(self):
        other = self.make_repo('other')
        self.configure(show=rec(['interactive'], workdir=str(other)), add={'ok': True, 'tags': []})
        self.run_hook(self.payload(cwd=str(self.repo)))
        self.assertEqual(self.added(), 'project proj')

    def test_the_record_workdir_is_used_without_a_payload_cwd(self):
        other = self.make_repo('other')
        self.configure(show=rec(['interactive'], workdir=str(other)), add={'ok': True, 'tags': []})
        self.run_hook(self.payload(cwd=None))
        self.assertEqual(self.added(), 'project other')

    def test_no_directory_at_all_adds_no_project(self):
        self.configure(show={'ok': True, 'tags': ['interactive']})
        proc, _ = self.run_hook(self.payload(cwd=None))
        self.assert_silent(proc)
        self.assertEqual(self.adds(), [])


class RoleAndAddTest(SessionTagsTest):
    ADD_ARGV = ['--tag-add', 'project proj', '--session', 'sess-1', '--json']

    def test_every_role_tag_counts_as_a_role(self):
        for role in ('worker', 'orchestrator', 'curator', 'handoff receiver', 'designer', 'test builder',
                     'implementer', 'runner', 'interpreter', 'reviewer', 'closer', 'interactive'):
            with self.subTest(role=role):
                self.configure(show=rec(['project proj', role]))
                proc, _ = self.run_hook()
                self.assert_silent(proc)
                self.assertEqual(self.adds(), [])

    def test_known_role_and_project_means_no_add_and_no_output(self):
        self.configure(show=rec(['project proj', 'worker']))
        proc, _ = self.run_hook()
        self.assert_silent(proc)
        self.assertEqual(self.adds(), [])

    def test_known_role_with_a_good_add_is_silent(self):
        self.configure(show=rec(['interactive']), add={'ok': True, 'tags': ['interactive', 'project proj']})
        proc, _ = self.run_hook()
        self.assert_silent(proc)
        self.assertEqual(self.adds(), [self.ADD_ARGV])

    def test_the_add_argv_is_exact(self):
        self.configure(show=rec(['interactive']))
        self.run_hook()
        self.assertEqual(self.adds(), [['--tag-add', 'project proj', '--session', 'sess-1', '--json']])

    def test_the_show_argv_is_exact(self):
        self.run_hook()
        self.assertEqual(self.shows(), [['--show', 'sess-1', '--json']])

    def test_worker_is_inferred_from_the_title(self):
        for title in ('[worker] fix the thing', 'Session name: [worker] fix the thing', '[WORKER] x',
                      'Session name: [Worker]x', '[worker]'):
            with self.subTest(title=title):
                if self.calls_file.exists():
                    self.calls_file.unlink()
                self.configure(show=rec([], title=title), add={'ok': True, 'tags': ['project proj', 'worker']})
                proc, _ = self.run_hook()
                self.assert_silent(proc)
                self.assertEqual(self.adds(), [['--tag-add', 'project proj,worker', '--session', 'sess-1', '--json']])

    def test_worker_alone_is_added_without_a_git_project(self):
        self.configure(show=rec([], title='[worker] x'), add={'ok': True, 'tags': ['worker']})
        proc, _ = self.run_hook(self.payload(cwd=str(self.plain)))
        self.assert_silent(proc)
        self.assertEqual(self.adds(), [['--tag-add', 'worker', '--session', 'sess-1', '--json']])

    def test_worker_is_added_when_the_project_tag_exists(self):
        self.configure(show=rec(['project proj'], title='[worker] x'), add={'ok': True, 'tags': []})
        proc, _ = self.run_hook()
        self.assert_silent(proc)
        self.assertEqual(self.adds(), [['--tag-add', 'worker', '--session', 'sess-1', '--json']])

    def test_titles_that_do_not_start_with_the_worker_marker_stay_unknown(self):
        for title in ('my [worker] thing', '[workers] x', 'worker', 'Session name:[worker]', '', 'x [worker]'):
            with self.subTest(title=title):
                self.configure(show=rec(['project proj'], title=title))
                proc, _ = self.run_hook()
                self.assertEqual(self.context(proc), role_msg(['project proj']))
                self.assertEqual(self.adds(), [])
                self.calls_file.unlink()

    def test_an_existing_role_beats_the_worker_title(self):
        self.configure(show=rec(['project proj', 'reviewer'], title='[worker] x'))
        proc, _ = self.run_hook()
        self.assert_silent(proc)
        self.assertEqual(self.adds(), [])

    def test_an_existing_role_means_silent_even_when_the_title_is_blank(self):
        self.configure(show=rec(['project proj', 'interactive'], title=''))
        proc, _ = self.run_hook()
        self.assert_silent(proc)

    def test_a_missing_title_does_not_crash(self):
        self.configure(show={'ok': True, 'tags': ['project proj']})
        proc, _ = self.run_hook()
        self.assertEqual(self.context(proc), role_msg(['project proj']))


class OutputTest(SessionTagsTest):
    def test_missing_role_reports_the_tags_read_when_nothing_was_added(self):
        self.configure(show=rec(['project proj', 'alpha']))
        proc, _ = self.run_hook()
        self.assertEqual(self.context(proc), role_msg(['project proj', 'alpha']))

    def test_missing_role_without_any_tags_says_none(self):
        self.configure(show=rec([]), add={'ok': True, 'tags': []})
        proc, _ = self.run_hook(self.payload(cwd=str(self.plain)))
        self.assertEqual(self.context(proc), role_msg([]))
        self.assertEqual(self.adds(), [])

    def test_missing_role_reports_the_add_reply_tags_after_a_good_add(self):
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha', 'project proj']})
        proc, _ = self.run_hook()
        self.assertEqual(self.context(proc), role_msg(['alpha', 'project proj']))

    def test_session_start_prints_nothing_and_the_file_holds_only_the_message(self):
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha']})
        proc, _ = self.run_hook()
        self.assertEqual(proc.stdout, '')
        self.assertEqual(self.msg_files(), [self.msg_path()])
        self.assertEqual(self.msg_path().read_text(), role_msg(['alpha']))


class AddFailureTest(SessionTagsTest):
    def failing(self, add, show=None):
        self.configure(show=show or rec(['interactive']), add=add)
        proc, _ = self.run_hook()
        return proc

    def test_the_error_field_is_reported(self):
        proc = self.failing({'out': {'ok': False, 'error': 'boom'}, 'rc': 1})
        self.assertEqual(self.context(proc), fail_msg('project proj', 'boom'))

    def test_the_message_field_is_the_second_choice(self):
        proc = self.failing({'out': {'ok': False, 'message': 'some message'}, 'rc': 1})
        self.assertEqual(self.context(proc), fail_msg('project proj', 'some message'))

    def test_error_wins_over_message(self):
        proc = self.failing({'out': {'ok': False, 'error': 'e1', 'message': 'm1'}, 'rc': 1})
        self.assertEqual(self.context(proc), fail_msg('project proj', 'e1'))

    def test_stderr_is_the_third_choice(self):
        proc = self.failing({'out': '', 'err': 'bad stderr', 'rc': 2})
        self.assertEqual(self.context(proc), fail_msg('project proj', 'bad stderr'))

    def test_the_exit_code_is_the_last_resort(self):
        proc = self.failing({'out': '', 'rc': 3})
        self.assertEqual(self.context(proc), fail_msg('project proj', 'exit 3'))

    def test_ok_false_with_exit_zero_is_a_failure(self):
        proc = self.failing({'out': {'ok': False, 'error': 'soft fail'}, 'rc': 0})
        self.assertEqual(self.context(proc), fail_msg('project proj', 'soft fail'))

    def test_a_nonzero_exit_with_an_ok_body_is_a_failure(self):
        proc = self.failing({'out': {'ok': True, 'tags': ['x']}, 'rc': 1})
        self.assertIn('could not add project proj', self.context(proc))

    def test_the_failure_lists_every_tag_comma_joined(self):
        proc = self.failing({'out': {'ok': False, 'error': 'boom'}, 'rc': 1}, show=rec([], title='[worker] x'))
        self.assertEqual(self.context(proc), fail_msg('project proj,worker', 'boom'))

    def test_a_failed_add_with_a_known_role_prints_only_the_failure(self):
        proc = self.failing({'out': {'ok': False, 'error': 'boom'}, 'rc': 1}, show=rec([], title='[worker] x'))
        self.assertNotIn('No role tag', self.context(proc))

    def test_a_failed_add_and_a_missing_role_share_one_message_failure_first(self):
        proc = self.failing({'out': {'ok': False, 'error': 'boom'}, 'rc': 1}, show=rec(['alpha']))
        ctx = self.context(proc)
        self.assertTrue(ctx.startswith(fail_msg('project proj', 'boom')), ctx)
        self.assertIn(role_msg(['alpha']), ctx, 'the tags are the ones read, since the add failed')
        self.assertTrue(ctx.endswith(ROLE_TAIL))
        self.assertEqual(len(self.msg_files()), 1)

    def test_a_hanging_add_is_bounded_and_reported(self):
        proc = self.failing({'sleep': 30, 'out': {'ok': True, 'tags': []}}, show=rec(['alpha']))
        self.assertIn('could not add project proj', self.context(proc))

    def test_a_hanging_add_stays_within_the_overall_bound(self):
        self.configure(show=rec(['alpha']), add={'sleep': 30, 'out': {'ok': True, 'tags': []}})
        proc, elapsed = self.run_hook()
        self.assertEqual(proc.returncode, 0)
        self.assertLess(elapsed, 12)


class ExitCodeTest(SessionTagsTest):
    def test_exit_is_zero_for_every_shape(self):
        shapes = [self.payload(), self.payload(source='resume'), self.payload(source='clear'), 'junk', '']
        for shape in shapes:
            with self.subTest(shape=shape):
                proc, _ = self.run_hook(shape)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout, '')


class ReadyTest(SessionTagsTest):
    FAIL = {'out': {'ok': False, 'error': 'launching'}, 'rc': 1}

    def test_the_first_read_is_retried_until_it_succeeds(self):
        self.configure(show=[self.FAIL, self.FAIL, rec(['interactive'])])
        proc, elapsed = self.run_hook(self.payload(), ready='8')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.shows()), 3)
        self.assertEqual(self.adds(), [['--tag-add', 'project proj', '--session', 'sess-1', '--json']])
        self.assertLess(elapsed, 6)

    def test_a_session_that_never_answers_is_untracked_after_the_ready_window(self):
        self.configure(show=self.FAIL)
        proc, elapsed = self.run_hook(self.payload(), ready='1')
        self.assert_silent(proc)
        self.assertGreaterEqual(len(self.shows()), 2)
        self.assertEqual(self.adds(), [])
        self.assertLess(elapsed, 8)

    def test_ready_zero_means_one_attempt(self):
        self.configure(show=self.FAIL)
        proc, _ = self.run_hook(self.payload(), ready='0')
        self.assert_silent(proc)
        self.assertEqual(len(self.shows()), 1)


class MsgFileTest(SessionTagsTest):
    def test_the_directory_is_created_when_missing(self):
        self.msgdir = self.tmp / 'not' / 'yet'
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha']})
        proc, _ = self.run_hook(self.payload())
        self.assertEqual(self.context(proc), role_msg(['alpha']))

    def test_no_message_means_no_file(self):
        self.configure(show=rec(['project proj', 'interactive']))
        proc, _ = self.run_hook(self.payload())
        self.assert_silent(proc)

    def test_the_session_id_is_sanitised_in_the_file_name(self):
        for sid, name in (('a/b c.d:e', 'a_b_c_d_e'), ('../../evil', '______evil'), ('ok-ID_9', 'ok-ID_9'),
                          ('uni\u00e9', 'uni_')):
            with self.subTest(sid=sid):
                for f in self.msg_files():
                    f.unlink()
                self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha']})
                proc, _ = self.run_hook(self.payload(session_id=sid))
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(self.msg_files(), [self.msgdir / f'{name}.msg'])
                self.assertFalse((self.tmp / 'evil.msg').exists())

    def test_without_a_payload_session_id_no_file_is_written(self):
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha']})
        proc, _ = self.run_hook(self.payload(session_id=None))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, '')
        self.assertEqual(self.msg_files(), [])

    def test_the_xdg_runtime_dir_is_the_second_choice(self):
        xdg = self.tmp / 'xdg'
        xdg.mkdir()
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha']})

        def edit(env):
            del env['SESSION_TAGS_DIR']
            env['XDG_RUNTIME_DIR'] = str(xdg)
        proc, _ = self.run_hook(self.payload(), edit=edit)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((xdg / 'session-tags' / 'sid-9.msg').read_text(), role_msg(['alpha']))

    def test_tmp_is_the_last_choice(self):
        sid = f'tagstest-{os.getpid()}-{time.monotonic_ns()}'
        target = Path(f'/tmp/session-tags-{os.getuid()}') / f'{sid}.msg'
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha']})

        def edit(env):
            del env['SESSION_TAGS_DIR']
            env.pop('XDG_RUNTIME_DIR', None)
        proc, _ = self.run_hook(self.payload(session_id=sid), edit=edit)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(target.read_text(), role_msg(['alpha']))

    def test_the_worker_deletes_message_files_older_than_a_day(self):
        self.msgdir.mkdir()
        old, fresh, other = self.msgdir / 'old.msg', self.msgdir / 'fresh.msg', self.msgdir / 'old.txt'
        for f in (old, fresh, other):
            f.write_text('x')
        now = time.time()
        os.utime(old, (now - 25 * 3600, now - 25 * 3600))
        os.utime(other, (now - 25 * 3600, now - 25 * 3600))
        os.utime(fresh, (now - 3600, now - 3600))
        self.configure(show=rec(['project proj', 'interactive']))
        proc, _ = self.run_hook(self.payload())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())
        self.assertTrue(other.exists(), 'only .msg files are cleaned')


class PromptSubmitTest(SessionTagsTest):
    def prompt(self, **over):
        return self.payload(hook_event_name='UserPromptSubmit', source=None, **over)

    def put(self, name='sid-9', text='Session tags: none. msg'):
        self.msgdir.mkdir(exist_ok=True)
        (self.msgdir / f'{name}.msg').write_text(text)

    def test_the_file_is_delivered_as_additional_context_and_deleted(self):
        text = 'Session tags: a, b. line one\nsecond "q" \u00e9'
        self.put(text=text)
        proc, _ = self.run_hook(self.prompt())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit', 'additionalContext': text}})
        self.assertFalse(self.msg_path().exists())

    def test_it_is_delivered_once(self):
        self.put()
        self.run_hook(self.prompt())
        proc, _ = self.run_hook(self.prompt())
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))

    def test_without_a_file_nothing_is_printed(self):
        proc, _ = self.run_hook(self.prompt())
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))

    def test_it_never_calls_sessioneer(self):
        self.put()
        self.run_hook(self.prompt())
        self.run_hook(self.prompt())
        self.assertEqual(self.calls(), [])

    def test_it_looks_up_the_sanitised_name(self):
        self.put('a_b_c', 'hello')
        proc, _ = self.run_hook(self.prompt(session_id='a/b c'))
        self.assertEqual(json.loads(proc.stdout)['hookSpecificOutput']['additionalContext'], 'hello')
        self.assertFalse((self.msgdir / 'a_b_c.msg').exists())

    def test_another_sessions_file_is_untouched(self):
        self.put('other')
        proc, _ = self.run_hook(self.prompt())
        self.assertEqual(proc.stdout, '')
        self.assertTrue((self.msgdir / 'other.msg').exists())

    def test_without_a_session_id_nothing_is_printed(self):
        self.put()
        proc, _ = self.run_hook(self.prompt(session_id=None))
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertTrue(self.msg_path().exists())

    def test_session_start_does_not_deliver_a_waiting_file(self):
        self.put()
        self.configure(show=rec(['project proj', 'interactive']))
        proc, _ = self.run_hook(self.payload())
        self.assertEqual(proc.stdout, '')


class DetachedTest(SessionTagsTest):
    def wait_for_file(self, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.msg_path().exists():
                return True
            time.sleep(0.2)
        return False

    def test_session_start_returns_at_once_even_when_sessioneer_hangs(self):
        self.configure(show={'sleep': 4, 'out': rec(['alpha'])})
        proc, elapsed = self.run_hook(self.payload(), foreground=False, timeout=15)
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertLess(elapsed, 1, 'SessionStart must not wait for sessioneer (nor hold its stdout pipe)')

    def test_the_detached_worker_eventually_writes_the_message(self):
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha', 'project proj']})
        proc, elapsed = self.run_hook(self.payload(), foreground=False)
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertTrue(self.wait_for_file(), 'the detached worker never wrote the message file')
        self.assertEqual(self.msg_path().read_text(), role_msg(['alpha', 'project proj']))

    def test_resume_is_detached_too(self):
        self.configure(show=rec(['alpha']), add={'ok': True, 'tags': ['alpha']})
        proc, _ = self.run_hook(self.payload(source='resume'), foreground=False)
        self.assertEqual((proc.returncode, proc.stdout), (0, ''))
        self.assertTrue(self.wait_for_file())

    def test_other_sources_start_no_worker(self):
        self.configure(show=rec(['alpha']))
        self.run_hook(self.payload(source='clear'), foreground=False)
        time.sleep(1)
        self.assertEqual(self.calls(), [])


if __name__ == '__main__':
    unittest.main()
