"""ai/hooks/rule-inject.py: just-in-time rule injection, once per context lifetime."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'ai' / 'hooks' / 'rule-inject.py'
EXPORT = """<!-- generated -->

## 732@1 Rule: docs and tests
TEXT-732
## 737@1 Rule: no dibs refs
TEXT-737
## 738@1 Rule: no trailer
TEXT-738
## 734@1 Rule: push
TEXT-734
## 735@1 Rule: force
TEXT-735
## 730@1 Rule: done
TEXT-730
## 740@1 Rule: sad paths
TEXT-740
## 928@1 Rule: peer
TEXT-928
## 929@1 Rule: stale
TEXT-929
## 1310@1 Rule: screenshots
TEXT-1310
"""
PRIVATE = "## 745@2 Rule: home\nTEXT-745-PRIVATE\n"
TRIGGERS = {'git-commit': [732, 737, 738], 'git-push': [734, 735, 730], 'git-history': [731, 733, 736],
            'db-cli': [929], 'test-file': [740], 'peer-prompt': [928], 'screenshot': [1310]}
PRIVATE_TRIGGERS = {'live-check': [745]}
STATUS_PHRASES = ('Safe to archive this session.', 'Continue in this session', 'Continue in a different session',
                  'Waiting on Andres', 'Waiting on other work', 'All planned work is done.')
KEYS = ('git-commit git-push git-history git-add-all test-run test-file php-tool live-check live-repo db-cli '
        'quota-check agent-launch session-launch peer-send peer-prompt dibs-create dibs-revise dibs-comment '
        'dibs-claim dibs-complete dibs-release screenshot schedule md-edit project-doc todo-note home-net '
        'work-creds').split()
KEY_ID = {k: 5000 + i for i, k in enumerate(KEYS)}  # one rule per key, text TEXT-<key>
KEY_EXPORT = ''.join(f'## {i}@1 Rule: {k}\nTEXT-{k}\n' for k, i in KEY_ID.items())
QUOTA_JSON = '{"agents":{"claude":{"profiles":{"personal":{"ok":true,"quota":{"session":{"pct":%s},"week_all":{"pct":%s}}},' \
             '"work":{"ok":true,"quota":{"session":{"pct":1},"week_all":{"pct":96}}}}}}}'
QUOTA_MSG = 'Quota at %s%% for profile %s (this session\'s own): rule 728. Start no new steps; park the work with a handoff.'


def make_stub(path, out='', rc=0, counter=None, args=None, next_out=None, next_rc=None, args_log=None):
    lines = ['#!/bin/sh']
    if counter:
        lines.append(f'echo x >> {counter}')
    if args:
        lines.append(f'echo "$@" > {args}')
    if args_log:
        lines.append(f'echo "$@" >> {args_log}')
    if next_out is not None:
        lines += ['for a in "$@"; do', '  if [ "$a" = --next ]; then',
                  f'    printf \'%s\' {shlex.quote(next_out)}',
                  f'    exit {rc if next_rc is None else next_rc}', '  fi', 'done']
    lines += [f"printf '%s' '{out}'", f'exit {rc}']
    Path(path).write_text('\n'.join(lines) + '\n')
    os.chmod(path, 0o755)


class HookBase(unittest.TestCase):
    """Every run gets temp RULE_FILES, RULE_TRIGGERS, RULE_STATE_DIR, RULE_PRIVATE_KEYS, SESSIONEER_BIN and HOME."""
    export = EXPORT
    triggers = TRIGGERS

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(self.tmp)]))
        (self.tmp / 'home').mkdir()
        (self.tmp / 'rules.md').write_text(self.export)
        (self.tmp / 'private.md').write_text(PRIVATE)
        self.write_triggers(self.triggers, PRIVATE_TRIGGERS)
        self.env = {**os.environ, 'HOME': str(self.tmp / 'home'),
                    'RULE_FILES': f"{self.tmp / 'rules.md'}:{self.tmp / 'private.md'}",
                    'RULE_TRIGGERS': f"{self.tmp / 'trig.json'}:{self.tmp / 'trig-private.json'}",
                    'RULE_STATE_DIR': str(self.tmp / 'state'),
                    'RULE_PRIVATE_KEYS': str(self.tmp / 'nokeys.json'),
                    'SESSIONEER_BIN': str(self.tmp / 'no-such-sessioneer')}
        self.env.pop('RULE_QUOTA_PROFILE', None)
        self.env.pop('CLAUDE_CONFIG_DIR', None)

    def write_triggers(self, public, private):
        (self.tmp / 'trig.json').write_text(json.dumps(public))
        (self.tmp / 'trig-private.json').write_text(json.dumps(private))

    def run_hook(self, raw=None, env=None, **event):
        event.setdefault('session_id', 's1')
        proc = subprocess.run([str(HOOK)], input=raw if raw is not None else json.dumps(event),
                              capture_output=True, text=True, env=env or self.env)
        self.assertEqual((proc.returncode, proc.stderr), (0, ''))
        return json.loads(proc.stdout)['hookSpecificOutput'] if proc.stdout.strip() else None

    def bash(self, cmd, **kw):
        return self.run_hook(hook_event_name='PreToolUse', tool_name='Bash', tool_input={'command': cmd}, **kw)

    def prompt(self, text, **kw):
        return self.run_hook(hook_event_name='UserPromptSubmit', prompt=text, **kw)




class RuleInjectTest(HookBase):
    def test_commit_injects_its_rules_once_without_denying(self):
        out = self.bash('git commit -m x')
        self.assertNotIn('permissionDecision', out)
        for i in (732, 737, 738):
            self.assertIn(f'TEXT-{i}', out['additionalContext'])
        self.assertIsNone(self.bash('git commit -m again'))

    def test_push_through_rtk_and_chained_injects_once_without_denying(self):
        out = self.bash('cd x && rtk git push origin master')
        self.assertNotIn('permissionDecision', out)
        self.assertIn('TEXT-734', out['additionalContext'])
        self.assertIsNone(self.bash('git push'))

    def test_non_deny_events_use_additional_context(self):
        out = self.bash('mysql -e "select 1"')
        self.assertEqual((out['hookEventName'], 'TEXT-929' in out['additionalContext']), ('PreToolUse', True))
        self.assertNotIn('permissionDecision', out)

    def test_test_file_edit_injects_test_rule(self):
        out = self.run_hook(hook_event_name='PreToolUse', tool_name='Edit',
                            tool_input={'file_path': '/x/tests/FooTest.php'})
        self.assertIn('TEXT-740', out['additionalContext'])
        self.assertIsNone(self.run_hook(hook_event_name='PreToolUse', tool_name='Edit',
                                        tool_input={'file_path': '/x/src/Foo.php'}, session_id='other'))

    def test_private_export_is_read(self):
        out = self.bash('curl http://x')
        self.assertIn('TEXT-745-PRIVATE', out['additionalContext'])

    def test_the_first_definition_of_an_id_wins_across_files(self):
        (self.tmp / 'private.md').write_text('## 732@1 Rule: override\nTEXT-EVIL\n')
        out = self.bash('git commit -m x')
        self.assertIn('TEXT-732', out['additionalContext'])
        self.assertNotIn('TEXT-EVIL', out['additionalContext'])

    def test_a_revision_bump_resends(self):
        self.assertIsNotNone(self.bash('git commit -m x'))
        self.assertIsNone(self.bash('git commit -m x'))
        (self.tmp / 'rules.md').write_text(EXPORT.replace('732@1', '732@2'))
        out = self.bash('git commit -m x')
        self.assertIn('TEXT-732', out['additionalContext'])
        self.assertNotIn('TEXT-737', out['additionalContext'])

    def test_compact_clear_resume_empty_the_set_and_startup_does_not(self):
        for source in ('compact', 'clear', 'resume'):
            self.bash('git commit -m x')
            out = self.run_hook(hook_event_name='SessionStart', source=source)
            self.assertIn('contextReset: true', out['additionalContext'])
            self.assertIsNotNone(self.bash('git commit -m x'), source)
        self.bash('git commit -m x')
        out = self.run_hook(hook_event_name='SessionStart', source='startup')
        self.assertIn('Claude profile: personal', out['additionalContext'])
        self.assertNotIn('contextReset', out['additionalContext'])
        self.assertIsNone(self.bash('git commit -m x'))

    def test_sets_are_per_session_and_per_subagent(self):
        self.bash('git commit -m x')
        self.assertIsNotNone(self.bash('git commit -m x', agent_id='a1'))
        self.assertIsNone(self.bash('git commit -m x', agent_id='a1'))
        self.assertIsNotNone(self.bash('git commit -m x', session_id='s2'))

    def test_todo_claim_response_marks_rules_delivered(self):
        wo = {'workOrder': {'rules': [{'id': 732, 'revision': 1, 'text': 'x'}, {'id': 737, 'revision': 1}]}}
        for resp in (wo, json.dumps(wo), [{'type': 'text', 'text': json.dumps(wo)}]):
            self.run_hook(hook_event_name='PostToolUse', tool_name='mcp__dibs__todo_claim', tool_response=resp,
                          session_id='c' + str(type(resp)))
        out = self.bash('git commit -m x', session_id="c<class 'dict'>")
        self.assertNotIn('TEXT-732', out['additionalContext'])  # delivered by Dibs
        self.assertIn('TEXT-737', out['additionalContext'])  # sent without text: still ours

    def test_peer_prompt_and_other_tools(self):
        out = self.run_hook(hook_event_name='UserPromptSubmit', prompt='[sessioneer peer: a · /x · master] hi')
        self.assertIn('TEXT-928', out['additionalContext'])
        self.assertIn('1226', out['additionalContext'])
        out = self.run_hook(hook_event_name='UserPromptSubmit', prompt='[sessioneer peer: a · /x · master] again')
        self.assertNotIn('TEXT-928', out['additionalContext'])
        self.assertIn('1226', out['additionalContext'])
        self.assertIsNone(self.run_hook(hook_event_name='PreToolUse', tool_name='Read', tool_input={}))

    def test_every_prompt_gets_the_status_line_reminder(self):
        for prompt in ('hello', 'hello again'):
            out = self.run_hook(hook_event_name='UserPromptSubmit', prompt=prompt)
            self.assertEqual(out['hookEventName'], 'UserPromptSubmit')
            ctx = out['additionalContext']
            self.assertIn('status line', ctx)
            self.assertIn('1226', ctx)
            self.assertLess(len(ctx), 600)
            self.assertNotIn('TEXT-928', ctx)
            for phrase in STATUS_PHRASES:
                self.assertIn(phrase, ctx)

    def test_browser_screenshot_injects_the_screenshot_rule(self):
        out = self.run_hook(hook_event_name='PreToolUse', tool_name='mcp__playwright__browser_take_screenshot', tool_input={})
        self.assertIn('TEXT-1310', out['additionalContext'])

    # sad paths: never a crash, never output
    def test_missing_export_is_silent(self):
        env = {**self.env, 'RULE_FILES': str(self.tmp / 'nope.md')}
        self.assertIsNone(self.run_hook(env=env, hook_event_name='PreToolUse', tool_name='Bash',
                                        tool_input={'command': 'git commit'}))

    def test_malformed_input_and_unknown_event_are_silent(self):
        for raw in ('', 'not json', '[]', '{"session_id": 3}', json.dumps({'session_id': 's', 'hook_event_name': 'Weird'})):
            self.assertIsNone(self.run_hook(raw=raw), raw)

    def test_malformed_export_is_silent(self):
        (self.tmp / 'rules.md').write_text('\x00garbage\n## x@y z\n')
        self.assertIsNone(self.bash('git commit -m x'))

    def test_trigger_map_drives_the_ids_not_a_hardcoded_list(self):
        self.write_triggers({'git-commit': [740]}, {})
        out = self.bash('git commit -m x')
        self.assertIn('TEXT-740', out['additionalContext'])
        for i in (732, 737, 738):
            self.assertNotIn(f'TEXT-{i}', out['additionalContext'])

    def test_maps_merge_by_key_as_a_union(self):
        self.write_triggers({'git-commit': [732]}, {'git-commit': [737, 732]})
        ctx = self.bash('git commit -m x')['additionalContext']
        self.assertIn('TEXT-732', ctx)
        self.assertIn('TEXT-737', ctx)
        self.assertEqual(ctx.count('TEXT-732'), 1)

    def test_an_id_in_the_map_without_a_rule_text_is_skipped(self):
        self.write_triggers({'git-commit': [99999, 732]}, {})
        ctx = self.bash('git commit -m x')['additionalContext']
        self.assertIn('TEXT-732', ctx)

    def test_missing_or_malformed_map_is_silent_and_gives_no_rules(self):
        for content in (None, 'not json', '[1, 2]', '{"git-commit": "oops"}', '\x00'):
            with self.subTest(content=content):
                for n in ('trig.json', 'trig-private.json'):
                    f = self.tmp / n
                    f.unlink(missing_ok=True)
                    if content is not None:
                        f.write_text(content)
                self.assertIsNone(self.bash('git commit -m x', session_id='m' + str(content)))

    def test_one_bad_map_file_does_not_hide_the_good_one(self):
        (self.tmp / 'trig-private.json').write_text('garbage')
        self.assertIn('TEXT-732', self.bash('git commit -m x')['additionalContext'])


class KeyHarness(HookBase):
    export = KEY_EXPORT
    triggers = {k: [i] for k, i in KEY_ID.items()}

    def setUp(self):
        super().setUp()
        self.n = 0
        self.write_triggers(self.triggers, {})

    def fired(self, **event):
        """Keys whose rule text arrived, in a fresh session so the once-only set never hides one."""
        self.n += 1
        event['session_id'] = f'k{self.n}'
        out = self.run_hook(**event)
        ctx = out['additionalContext'] if out else ''
        return {k for k in KEYS if f'TEXT-{k}' in ctx}

    def fired_bash(self, cmd):
        return self.fired(hook_event_name='PreToolUse', tool_name='Bash', tool_input={'command': cmd})

    def fired_path(self, path, tool='Edit'):
        ti = {'file_path': path}
        if tool == 'NotebookEdit':
            ti['notebook_path'] = path
        return self.fired(hook_event_name='PreToolUse', tool_name=tool, tool_input=ti)

    def check(self, table, fn):
        for arg, key in table:
            with self.subTest(arg=arg, key=key):
                self.assertIn(key, fn(arg))

    def check_not(self, table, fn):
        for arg, key in table:
            with self.subTest(arg=arg, key=key):
                self.assertNotIn(key, fn(arg))



class KeyDetectionTest(KeyHarness):
    def test_git_keys(self):
        self.check([('git commit -m x', 'git-commit'), ('cd x && rtk git commit -m y', 'git-commit'),
                    ('git push origin master', 'git-push'), ('rtk git push', 'git-push')], self.fired_bash)
        self.check_not([('git status', 'git-commit'), ('git log', 'git-push'), ('git pull', 'git-push'),
                        ('git push', 'git-commit'), ('git commit -m x', 'git-push')], self.fired_bash)

    def test_git_history(self):
        self.check([(f'git {c}', 'git-history') for c in ('merge x', 'rebase main', 'worktree add y', 'cherry-pick abc',
                                                         'stash', 'reset --hard', 'commit --amend', 'commit --amend --no-edit')],
                   self.fired_bash)
        self.check_not([('git commit -m x', 'git-history'), ('git status', 'git-history'), ('git push', 'git-history'),
                        ('git log --oneline', 'git-history')], self.fired_bash)

    def test_git_add_all(self):
        self.check([(c, 'git-add-all') for c in ('git add -A', 'git add --all', 'git add .', 'git commit -a -m x',
                                                'git commit -am "x"', 'git commit --all -m x', 'git checkout .',
                                                'git clean -fd', 'rtk git add -A')], self.fired_bash)
        self.check_not([(c, 'git-add-all') for c in ('git add src/app.py', 'git commit -m x', 'git checkout main',
                                                    'git status', 'git push')], self.fired_bash)

    def test_test_run(self):
        self.check([(c, 'test-run') for c in ('pest', 'vendor/bin/pest --parallel', 'vendor/bin/phpunit', 'php artisan test',
                                             'pytest -q', 'python3 -m pytest tests', 'npx vitest run', 'npx jest',
                                             'npm test', 'npm run test')], self.fired_bash)
        self.check_not([(c, 'test-run') for c in ('npm install', 'ls tests', 'echo hello', 'php artisan route:list',
                                                 'git commit -m x')], self.fired_bash)

    def test_php_tool(self):
        self.check([(c, 'php-tool') for c in ('php artisan route:list', 'composer install', 'vendor/bin/pint',
                                             'vendor/bin/phpstan analyse', 'vendor/bin/rector process',
                                             'php artisan test')], self.fired_bash)
        self.check_not([(c, 'php-tool') for c in ('ls', 'git status', 'npm test')], self.fired_bash)

    def test_live_check(self):
        self.check([(c, 'live-check') for c in ('curl http://x', 'docker compose up -d', 'docker compose restart web',
                                               'docker-compose up', 'docker-compose restart')], self.fired_bash)
        self.check_not([(c, 'live-check') for c in ('docker compose ps', 'docker ps', 'git status')], self.fired_bash)

    def test_db_cli(self):
        self.check([(c, 'db-cli') for c in ('mysql -e "select 1"', 'mariadb', 'sqlite3 x.db', 'php artisan tinker',
                                           'php artisan migrate')], self.fired_bash)
        self.check_not([(c, 'db-cli') for c in ('ls', 'git status')], self.fired_bash)

    def test_sessioneer_keys(self):
        self.check([('sessioneer --usage', 'quota-check'), ('rtk sessioneer --usage', 'quota-check'),
                    ('sessioneer --agent claude "do x"', 'session-launch'), ('sessioneer --model sonnet "x"', 'session-launch'),
                    ('sessioneer --effort high "x"', 'session-launch'), ('sessioneer --resume abc "x"', 'session-launch'),
                    ('sessioneer --send abc "x"', 'peer-send'), ('sessioneer --peers', 'peer-send')], self.fired_bash)
        self.check_not([('sessioneer --send abc x', 'quota-check'), ('sessioneer --peers', 'session-launch'),
                        ('sessioneer --usage', 'session-launch'), ('sessioneer --usage', 'peer-send'),
                        ('sessioneer --agent claude x', 'peer-send'), ('ls', 'quota-check')], self.fired_bash)

    def test_schedule(self):
        self.check([(c, 'schedule') for c in ('at 10:00', 'echo x | at now + 1 minute', 'atq', 'sleep 100', 'sleep 3600',
                                             'sleep 100 && echo done')], self.fired_bash)
        self.check_not([(c, 'schedule') for c in ('sleep 5', 'sleep 99', 'sleep 0.5', 'ls atlas', 'cat file',
                                                 'git status')], self.fired_bash)

    def test_path_keys(self):
        self.check([('/x/tests/FooTest.php', 'test-file'), ('/x/tests/test_a.py', 'test-file'),
                    ('/x/notes.md', 'md-edit'), ('/x/CLAUDE.md', 'project-doc'), ('/x/sub/AGENTS.md', 'project-doc'),
                    ('/x/CLAUDE.md', 'md-edit')], self.fired_path)
        self.check_not([('/x/src/Foo.php', 'test-file'), ('/x/notes.txt', 'md-edit'), ('/x/README.md', 'project-doc'),
                        ('/x/MYCLAUDE.md', 'project-doc'), ('/x/src/Foo.php', 'project-doc'), ('/x/src/Foo.php', 'md-edit')],
                       self.fired_path)

    def test_path_keys_for_every_edit_tool(self):
        for tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
            with self.subTest(tool=tool):
                self.assertIn('md-edit', self.fired_path('/x/notes.md', tool))
                self.assertNotIn('md-edit', self.fired_path('/x/notes.txt', tool))

    def test_live_repo_needs_www_and_a_compose_file_in_the_git_root(self):
        www = self.tmp / 'home' / 'www'
        for name, compose in (('withcompose', True), ('nocompose', False)):
            repo = www / name
            (repo / 'app').mkdir(parents=True)
            subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True, capture_output=True)
            (repo / 'app' / 'Foo.php').write_text('x')
            if compose:
                (repo / 'docker-compose.yml').write_text('services: {}\n')
        outside = self.tmp / 'other' / 'proj'
        (outside / 'app').mkdir(parents=True)
        subprocess.run(['git', '-C', str(outside), 'init', '-q'], check=True, capture_output=True)
        (outside / 'docker-compose.yml').write_text('services: {}\n')
        self.assertIn('live-repo', self.fired_path(str(www / 'withcompose' / 'app' / 'Foo.php')))
        self.assertNotIn('live-repo', self.fired_path(str(www / 'nocompose' / 'app' / 'Foo.php')))
        self.assertNotIn('live-repo', self.fired_path(str(outside / 'app' / 'Foo.php')))
        self.assertNotIn('live-repo', self.fired_bash(f'ls {www}/withcompose'))

    def test_tool_keys(self):
        table = [('Agent', 'agent-launch'), ('Task', 'agent-launch'), ('mcp__dibs__todo_create', 'dibs-create'),
                 ('mcp__dibs__todo_revise', 'dibs-revise'), ('mcp__dibs__todo_comment', 'dibs-comment'),
                 ('mcp__dibs__todo_heartbeat', 'dibs-comment'), ('mcp__dibs__todo_claim', 'dibs-claim'),
                 ('mcp__dibs__todo_complete', 'dibs-complete'), ('mcp__dibs__todo_release', 'dibs-release'),
                 ('mcp__playwright__browser_take_screenshot', 'screenshot')]
        self.check(table, lambda t: self.fired(hook_event_name='PreToolUse', tool_name=t, tool_input={}))

    def test_tool_keys_are_not_cross_wired(self):
        for tool, key in (('mcp__dibs__todo_claim', 'dibs-complete'), ('mcp__dibs__todo_revise', 'dibs-create'),
                          ('Agent', 'dibs-claim'), ('mcp__dibs__todo_complete', 'dibs-release'),
                          ('mcp__dibs__todo_release', 'dibs-complete')):
            with self.subTest(tool=tool):
                self.assertNotIn(key, self.fired(hook_event_name='PreToolUse', tool_name=tool, tool_input={}))
        self.assertEqual(self.fired(hook_event_name='PreToolUse', tool_name='Read', tool_input={'file_path': '/x/notes.md'}), set())

    def test_prompt_keys(self):
        fn = lambda p: self.fired(hook_event_name='UserPromptSubmit', prompt=p)
        self.check([('[sessioneer peer: a · /x · master] hi', 'peer-prompt'), ('Todo: fix the thing', 'todo-note'),
                    ('next: after X do Y', 'todo-note'), ('NEXT: later', 'todo-note'), ('todo: later', 'todo-note')], fn)
        self.check_not([('hello', 'peer-prompt'), ('hello', 'todo-note'), ('please do this Todo: x', 'todo-note'),
                        ('the next step is', 'todo-note'), ('see [sessioneer peer: a] hi', 'peer-prompt'),
                        ('Todo: x', 'peer-prompt'), ('[sessioneer peer: a] x', 'todo-note')], fn)


class PrivateKeysTest(KeyHarness):
    """home-net and work-creds read their regexes from RULE_PRIVATE_KEYS, never from the public hook."""

    def setUp(self):
        super().setUp()
        self.keys = self.tmp / 'keys.json'
        self.keys.write_text(json.dumps({'home-net': r'zzq-traefik|pihole\.conf', 'work-creds': r'(?i)cpanel-zzq'}))
        self.env['RULE_PRIVATE_KEYS'] = str(self.keys)

    def test_bash_commands_and_prompts_match_the_fixture_regexes(self):
        self.check([('cat zzq-traefik/dynamic.yml', 'home-net'), ('vim pihole.conf', 'home-net'),
                    ('cpanel-ZZQ login', 'work-creds')], self.fired_bash)
        fn = lambda p: self.fired(hook_event_name='UserPromptSubmit', prompt=p)
        self.check([('why is zzq-traefik broken', 'home-net'), ('add a CPANEL-zzq account', 'work-creds')], fn)

    def test_non_matching_text_fires_neither(self):
        for text in ('ls', 'git status', 'traefik'):
            self.assertFalse({'home-net', 'work-creds'} & self.fired_bash(text), text)
        self.assertFalse({'home-net', 'work-creds'} & self.fired(hook_event_name='UserPromptSubmit', prompt='hello'))

    def test_each_key_uses_only_its_own_regex(self):
        self.assertNotIn('work-creds', self.fired_bash('cat zzq-traefik/x'))
        self.assertNotIn('home-net', self.fired_bash('cpanel-zzq'))

    def test_missing_or_malformed_key_file_never_fires_and_never_crashes(self):
        for content in (None, 'not json', '[]', '{"home-net": "(unclosed"}'):
            with self.subTest(content=content):
                if content is None:
                    self.keys.unlink(missing_ok=True)
                else:
                    self.keys.write_text(content)
                self.assertFalse({'home-net', 'work-creds'} & self.fired_bash('cat zzq-traefik cpanel-zzq'))
                self.assertIn('git-commit', self.fired_bash('git commit -m x'))


class LabelHyphenWarningTest(HookBase):
    export = KEY_EXPORT
    triggers = {k: [i] for k, i in KEY_ID.items()}
    PREFIX = 'Label names use spaces, not hyphens:'

    def call(self, tool, ti, **kw):
        return self.run_hook(hook_event_name='PreToolUse', tool_name=f'mcp__dibs__{tool}', tool_input=ti, **kw)

    def test_hyphenated_label_names_warn_on_create_and_name_the_labels(self):
        ctx = self.call('todo_create', {'title': 't', 'labelNames': ['needs-research', 'plan'],
                                        'newLabelName': 'foo-bar'})['additionalContext']
        self.assertIn(self.PREFIX, ctx)
        warning = ctx[ctx.index(self.PREFIX):]
        self.assertIn('needs-research', warning)
        self.assertIn('foo-bar', warning)

    def test_revise_add_labels_warns(self):
        ctx = self.call('todo_revise', {'id': 1, 'addLabels': ['hand-off']})['additionalContext']
        self.assertIn(self.PREFIX, ctx)
        self.assertIn('hand-off', ctx)

    def test_warning_repeats_on_every_call_and_comes_with_the_rules(self):
        first = self.call('todo_create', {'labelNames': ['a-b']})['additionalContext']
        second = self.call('todo_create', {'labelNames': ['a-b']})['additionalContext']
        self.assertIn('TEXT-dibs-create', first)
        self.assertIn(self.PREFIX, first)
        self.assertNotIn('TEXT-dibs-create', second)
        self.assertIn(self.PREFIX, second)

    def test_no_hyphen_no_warning(self):
        for tool, ti in (('todo_create', {'title': 'a-b', 'labelNames': ['needs research', 'plan']}),
                         ('todo_create', {'title': 'x'}), ('todo_revise', {'id': 1, 'addLabels': ['plan'], 'title': 'a-b'}),
                         ('todo_revise', {'id': 1, 'body': 'x-y'})):
            with self.subTest(tool=tool, ti=ti):
                out = self.call(tool, ti, session_id=f'n{len(str(ti))}{tool}')
                self.assertNotIn(self.PREFIX, out['additionalContext'] if out else '')

    def test_other_tools_never_warn(self):
        out = self.call('todo_comment', {'labelNames': ['a-b']})
        self.assertNotIn(self.PREFIX, out['additionalContext'] if out else '')

    def test_warning_without_any_trigger_map(self):
        self.write_triggers({}, {})
        out = self.call('todo_create', {'labelNames': ['a-b']})
        self.assertIn(self.PREFIX, out['additionalContext'])


class QuotaCheckTest(HookBase):
    def setUp(self):
        super().setUp()
        self.counter, self.argsf, self.log = self.tmp / 'count', self.tmp / 'args', self.tmp / 'log'

    def stub(self, out, rc=0):
        make_stub(self.tmp / 'sessioneer', out, rc, self.counter, self.argsf, args_log=self.log)
        self.env['SESSIONEER_BIN'] = str(self.tmp / 'sessioneer')

    def runs(self):
        return len(self.counter.read_text().split()) if self.counter.exists() else 0

    def usage_runs(self):
        """Calls that asked --usage: the reading is cached, so one per window however the decision is fetched."""
        if not self.log.exists():
            return 0
        return sum(1 for line in self.log.read_text().splitlines() if '--usage' in line.split())

    def ctx(self, **kw):
        out = self.prompt('hello', **kw)
        return out['additionalContext'] if out else ''

    def test_at_or_above_90_warns_with_the_exact_text_and_runs_usage(self):
        self.stub(QUOTA_JSON % (95, 10))
        self.assertIn(QUOTA_MSG % (95, 'personal'), self.ctx())
        self.assertEqual(self.argsf.read_text().strip(), '--usage')

    def test_the_week_figure_counts_and_the_max_is_reported(self):
        self.stub(QUOTA_JSON % (10, 92))
        self.assertIn(QUOTA_MSG % (92, 'personal'), self.ctx())

    def test_exactly_90_warns(self):
        self.stub(QUOTA_JSON % (90, 0))
        self.assertIn(QUOTA_MSG % (90, 'personal'), self.ctx())

    def test_89_does_not(self):
        self.stub(QUOTA_JSON % (89, 89))
        self.assertNotIn('Quota at', self.ctx())

    def test_the_warning_comes_once_per_session_and_agent(self):
        self.stub(QUOTA_JSON % (95, 0))
        self.assertIn('Quota at 95%', self.ctx())
        self.assertNotIn('Quota at', self.ctx())
        self.assertIn('Quota at 95%', self.ctx(agent_id='sub1'))
        self.assertNotIn('Quota at', self.ctx(agent_id='sub1'))
        self.assertIn('Quota at 95%', self.ctx(session_id='s2'))

    def test_the_result_is_cached_so_the_binary_runs_once_in_the_window(self):
        self.stub(QUOTA_JSON % (95, 0))
        self.ctx()
        self.ctx()
        self.ctx(session_id='s2')
        self.assertEqual(self.usage_runs(), 1)

    def test_a_low_reading_is_cached_too(self):
        self.stub(QUOTA_JSON % (5, 5))
        self.ctx()
        self.ctx()
        self.assertEqual(self.usage_runs(), 1)
        self.assertNotIn('Quota at', self.ctx())

    def test_profile_comes_from_rule_quota_profile(self):
        self.stub(QUOTA_JSON % (1, 1))
        self.env['RULE_QUOTA_PROFILE'] = 'work'
        self.assertIn(QUOTA_MSG % (96, 'work'), self.ctx())

    def test_profile_comes_from_the_config_dir(self):
        self.stub(QUOTA_JSON % (1, 1))
        self.env['CLAUDE_CONFIG_DIR'] = '/home/x/.claude-work/'
        self.assertIn(QUOTA_MSG % (96, 'work'), self.ctx())
        out = self.run_hook(hook_event_name='SessionStart', source='startup')
        self.assertIn('Claude profile: work', out['additionalContext'])

    def test_a_plain_config_dir_is_the_personal_profile(self):
        self.stub(QUOTA_JSON % (95, 0))
        self.env['CLAUDE_CONFIG_DIR'] = '/home/x/.claude'
        self.assertIn(QUOTA_MSG % (95, 'personal'), self.ctx())

    def test_unusable_readings_are_silent(self):
        cases = [('not json', 0), ('', 0), ('{}', 0), (QUOTA_JSON % (99, 99), 3),
                 ('{"agents":{"claude":{"profiles":{"personal":{"ok":false,"quota":{"session":{"pct":99},"week_all":{"pct":99}}}}}}}', 0),
                 ('{"agents":{"claude":{"profiles":{"personal":{"ok":true,"quota":{"session":{"pct":"high"}}}}}}}', 0)]
        for n, (out, rc) in enumerate(cases):
            with self.subTest(out=out, rc=rc):
                self.stub(out, rc)
                subprocess.run(['rm', '-rf', str(self.tmp / 'state')])
                self.assertNotIn('Quota at', self.ctx(session_id=f'u{n}'))

    def test_missing_binary_is_silent(self):
        self.assertNotIn('Quota at', self.ctx())

    def test_only_prompts_read_the_quota(self):
        self.stub(QUOTA_JSON % (95, 0))
        self.bash('git status')
        self.run_hook(hook_event_name='SessionStart', source='startup')
        self.assertEqual(self.runs(), 0)

    def test_the_status_reminder_still_comes_with_the_warning(self):
        self.stub(QUOTA_JSON % (95, 0))
        ctx = self.ctx()
        self.assertIn('1226', ctx)
        self.assertIn(QUOTA_MSG % (95, 'personal'), ctx)


PARK_DECISION = '{"ok":true,"state":"PARK","why":"quota at 91% and no receiver has room","trigger":"quota"}'
GO_DECISION = '{"ok":true,"state":"GO","why":"context 90000, quota 12%","trigger":"none"}'


class NextQuotaTest(HookBase):
    """Intent: the prompt's quota warning follows `sessioneer --next --json` for this conversation; --usage
    is only the fallback when the decision cannot be read (the cases QuotaCheckTest already pins)."""

    def setUp(self):
        super().setUp()
        self.calls = self.tmp / 'calls'

    def stub(self, next_out, usage_out='', usage_rc=1):
        body = ['#!/bin/sh', f'echo "$@" >> {self.calls}',
                'for a in "$@"; do', '  if [ "$a" = --next ]; then',
                f'    printf \'%s\' {shlex.quote(next_out)}', '    exit 0', '  fi', 'done',
                f"printf '%s' {shlex.quote(usage_out)}", f'exit {usage_rc}']
        path = self.tmp / 'sessioneer'
        path.write_text('\n'.join(body) + '\n')
        os.chmod(path, 0o755)
        self.env['SESSIONEER_BIN'] = str(path)

    def calls_made(self):
        if not self.calls.exists():
            return []
        return [line.split() for line in self.calls.read_text().splitlines() if line.strip()]

    def ctx(self, **kw):
        out = self.prompt('hello', **kw)
        return out['additionalContext'] if out else ''

    def test_a_park_decision_warns_once_with_the_state_and_rule_728_without_usage(self):
        self.stub(PARK_DECISION)
        first = self.ctx()
        self.assertIn('PARK', first)
        self.assertIn('728', first)
        self.assertNotIn('PARK', self.ctx())

    def test_the_decision_is_asked_for_this_conversation_as_json(self):
        self.stub(PARK_DECISION)
        self.ctx()
        self.assertEqual(self.calls_made()[0][0], '--next')
        self.assertCountEqual(self.calls_made()[0], ['--next', 's1', '--json'])

    def test_a_go_decision_has_no_quota_warning_even_when_usage_reports_91(self):
        self.stub(GO_DECISION, QUOTA_JSON % (91, 10), 0)
        context = self.ctx()
        self.assertNotIn('Quota', context)
        self.assertNotIn('728', context)


LATE = 'This rule arrived after the call ran. Check that call and your earlier work in this session against it, and fix what it missed.'
TYPE_KEYS = {'code': ['live-repo'], 'tests': ['test-file', 'test-run'], 'docs': ['md-edit', 'project-doc'],
             'git': ['git-commit', 'git-history', 'git-add-all', 'git-push'], 'db': ['db-cli'],
             'live-site': ['live-check', 'live-repo'],
             'dibs': ['dibs-create', 'dibs-revise', 'dibs-comment', 'dibs-claim', 'dibs-complete', 'dibs-release'],
             'infra': ['home-net', 'schedule', 'live-check'], 'research': []}


class LateRuleNoticeTest(HookBase):
    """Contract 4: rules delivered on an allowed PreToolUse call end with the late-rule notice; nowhere else."""

    def test_pretooluse_rules_end_with_the_exact_notice_once(self):
        out = self.bash('git commit -m x')
        self.assertTrue(out['additionalContext'].endswith(LATE))
        self.assertEqual(out['additionalContext'].count(LATE), 1)
        self.assertIn('TEXT-732', out['additionalContext'])

    def test_notice_comes_once_for_several_rules_and_after_all_of_them(self):
        ctx = self.bash('git commit -m x')['additionalContext']
        self.assertEqual(ctx.count(LATE), 1)
        for i in (732, 737, 738):
            self.assertLess(ctx.index(f'TEXT-{i}'), ctx.index(LATE))

    def test_every_pretooluse_delivery_path_has_it(self):
        for ev in (dict(tool_name='Bash', tool_input={'command': 'git push'}),
                   dict(tool_name='Edit', tool_input={'file_path': '/x/tests/FooTest.php'}),
                   dict(tool_name='mcp__playwright__browser_take_screenshot', tool_input={}),
                   dict(tool_name='Bash', tool_input={'command': 'mysql -e "select 1"'})):
            with self.subTest(ev=ev):
                out = self.run_hook(hook_event_name='PreToolUse', session_id=f"n{ev['tool_name']}{ev['tool_input']}", **ev)
                self.assertTrue(out['additionalContext'].endswith(LATE))

    def test_no_rule_delivered_means_no_output_and_no_notice(self):
        self.bash('git commit -m x')
        self.assertIsNone(self.bash('git commit -m again'))
        self.assertIsNone(self.bash('echo hello'))

    def test_prompt_and_session_start_never_get_the_notice(self):
        out = self.run_hook(hook_event_name='UserPromptSubmit', prompt='[sessioneer peer: a · /x · master] hi')
        self.assertIn('TEXT-928', out['additionalContext'])
        self.assertNotIn(LATE, out['additionalContext'])
        out = self.prompt('plain prompt')
        self.assertNotIn(LATE, out['additionalContext'])
        out = self.run_hook(hook_event_name='SessionStart', source='compact')
        self.assertNotIn(LATE, out['additionalContext'])

    def test_a_dibs_claim_work_order_is_not_a_delivery_and_adds_no_notice(self):
        wo = {'workOrder': {'rules': [{'id': 732, 'revision': 1, 'text': 'x'}]}}
        out = self.run_hook(hook_event_name='PostToolUse', tool_name='mcp__dibs__todo_claim', tool_response=wo)
        self.assertTrue(out is None or LATE not in out.get('additionalContext', ''))


class RulesForTypesTest(KeyHarness):
    """Contract 3: TYPE_KEYS and rules_for_types(types, session_id, agent_id), importable by path, shared delivered state."""
    SCRIPT = (
        'import importlib.util, json, sys\n'
        'spec = importlib.util.spec_from_file_location("rule_inject", sys.argv[1])\n'
        'mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n'
        'types, session, agent = json.loads(sys.argv[2]), sys.argv[3], (sys.argv[4] or None)\n'
        'print(json.dumps({"result": mod.rules_for_types(types, session, agent), "table": getattr(mod, "TYPE_KEYS", None)}, default=str))\n')

    def call(self, types, session='s1', agent='', env=None):
        proc = subprocess.run(['python3', '-c', self.SCRIPT, str(HOOK), json.dumps(types), session, agent],
                              capture_output=True, text=True, env=env or self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def keys_in(self, payload):
        blob = json.dumps(payload['result'])
        return {k for k in KEYS if f'TEXT-{k}' in blob}

    def test_the_type_table_is_exposed_and_maps_as_specified(self):
        table = self.call(['research'])['table']
        self.assertEqual({k: sorted(v) for k, v in table.items()}, {k: sorted(v) for k, v in TYPE_KEYS.items()})

    def test_each_type_returns_exactly_its_rules(self):
        for index, (kind, keys) in enumerate(TYPE_KEYS.items()):
            with self.subTest(kind=kind):
                self.assertEqual(self.keys_in(self.call([kind], session=f'ty{index}')), set(keys))

    def test_several_types_return_the_union_without_duplicates(self):
        payload = self.call(['code', 'live-site', 'tests'])
        self.assertEqual(self.keys_in(payload), {'live-repo', 'live-check', 'test-file', 'test-run'})
        self.assertEqual(json.dumps(payload['result']).count('TEXT-live-repo'), 1)

    def test_delivered_rules_are_not_returned_again_and_are_shared_with_the_hook(self):
        self.assertEqual(self.keys_in(self.call(['git'])), set(TYPE_KEYS['git']))
        self.assertEqual(self.call(['git'])['result'], [])
        self.assertIsNone(self.bash('git commit -m x'))
        self.assertIsNone(self.bash('git push'))

    def test_rules_delivered_by_the_hook_are_not_returned(self):
        self.assertIsNotNone(self.bash('git commit -m x'))
        self.assertEqual(self.keys_in(self.call(['git'])), set(TYPE_KEYS['git']) - {'git-commit'})

    def test_state_is_per_session_and_per_agent(self):
        self.call(['db'])
        self.assertEqual(self.keys_in(self.call(['db'], session='other')), {'db-cli'})
        self.assertEqual(self.keys_in(self.call(['db'], agent='a1')), {'db-cli'})
        self.assertEqual(self.call(['db'], agent='a1')['result'], [])

    def test_a_revision_bump_returns_the_rule_again(self):
        self.call(['db'])
        (self.tmp / 'rules.md').write_text(KEY_EXPORT.replace(f'{KEY_ID["db-cli"]}@1', f'{KEY_ID["db-cli"]}@2'))
        self.assertEqual(self.keys_in(self.call(['db'])), {'db-cli'})

    def test_unknown_empty_and_research_types_return_nothing(self):
        for types in ([], ['research'], ['nonsense'], ['nonsense', 'research']):
            with self.subTest(types=types):
                self.assertEqual(self.call(types)['result'], [])

    def test_missing_export_or_trigger_map_returns_nothing_without_raising(self):
        self.assertEqual(self.call(['code'], env={**self.env, 'RULE_FILES': str(self.tmp / 'nope.md')})['result'], [])
        self.assertEqual(self.call(['code'], env={**self.env, 'RULE_TRIGGERS': str(self.tmp / 'nope.json')})['result'], [])

    def test_a_key_missing_from_the_trigger_map_is_skipped(self):
        triggers = {k: [i] for k, i in KEY_ID.items() if k != 'test-run'}
        self.write_triggers(triggers, {})
        self.assertEqual(self.keys_in(self.call(['tests'])), {'test-file'})


if __name__ == '__main__':
    unittest.main()
