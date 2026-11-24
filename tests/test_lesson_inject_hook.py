"""ai/hooks/rule-inject.py + ai/hooks/lessons.py: lessons from the Dibs cache ride along with the rules.

Every run uses a temp LESSON_CACHE, temp state dir and temp HOME; refresh is off unless a test turns it on
with a stub command. Nothing touches the real home or a real Dibs.
"""
import json
import os
from pathlib import Path
import re
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_rule_inject_hook import HookBase, make_stub  # noqa: E402

LESSON_LINE = re.compile(r'^\[lesson (\d+)\] (.*)$', re.M)
LATE_PHRASE = 'arrived after the call ran'
CWD = '/home/andres/www/dotfiles'


def lesson(id, summary=None, triggers=('git commit',), group='dotfiles', area='Personal Projects', hits=1,
           last_seen='2026-11-01', **extra):
    return {'id': id, 'summary': summary if summary is not None else f'summary {id}', 'triggers': list(triggers),
            'group': group, 'area': area, 'hits': hits, 'last_seen': last_seen, **extra}


class LessonBase(HookBase):
    def setUp(self):
        super().setUp()
        self.cache = self.tmp / 'lessons.json'
        self.env.update({'LESSON_CACHE': str(self.cache), 'LESSON_REFRESH': 'off'})
        self.env.pop('LESSON_CAP', None)
        self.env.pop('LESSON_TTL', None)
        self.env.pop('LESSON_REFRESH_CMD', None)

    def write_cache(self, lessons, generated=None):
        self.cache.write_text(json.dumps({'generated': time.time() if generated is None else generated,
                                          'lessons': lessons}))

    def ids(self, out):
        """Lesson ids in the order the hook printed them."""
        return [int(m.group(1)) for m in LESSON_LINE.finditer(out['additionalContext'])] if out else []


class LessonInjectTest(LessonBase):
    """Group: selection. Which lessons are eligible for an event and in what order."""

    def test_lessons_are_appended_to_the_rules_in_one_additional_context(self):
        self.write_cache([lesson(11, 'Run Pint before the commit')])
        out = self.bash('git commit -m x', cwd=CWD)
        ctx = out['additionalContext']
        self.assertIn('TEXT-732', ctx)
        self.assertIn('Lessons for this action:', ctx)
        self.assertIn('[lesson 11] Run Pint before the commit', ctx)
        self.assertLess(ctx.index('Rules for this action:'), ctx.index('Lessons for this action:'))
        self.assertNotIn('permissionDecision', out)

    def test_no_cache_entry_for_the_key_adds_no_lessons_section(self):
        self.write_cache([lesson(11, triggers=['test run'])])
        out = self.bash('git commit -m x', cwd=CWD)
        self.assertNotIn('Lessons for this action:', out['additionalContext'])
        self.assertIn('TEXT-732', out['additionalContext'])

    def test_hyphenated_keys_match_space_triggers(self):
        self.write_cache([lesson(1, triggers=['test file']), lesson(2, triggers=['git commit']),
                          lesson(3, triggers=['git-commit'])])
        out = self.run_hook(hook_event_name='PreToolUse', tool_name='Edit',
                            tool_input={'file_path': '/x/tests/FooTest.php'}, cwd=CWD)
        self.assertEqual(self.ids(out), [1])

    def test_a_lesson_with_several_triggers_is_eligible_for_each(self):
        self.write_cache([lesson(5, triggers=['git commit', 'git push'])])
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD)), [5])
        self.assertEqual(self.ids(self.bash('git push', cwd=CWD, session_id='s2')), [5])

    def test_lessons_for_a_key_without_rules_are_delivered_without_the_late_notice(self):
        self.write_cache([lesson(7, triggers=['git add all'])])
        out = self.bash('git add -A', cwd=CWD)
        self.assertEqual(self.ids(out), [7])
        self.assertNotIn(LATE_PHRASE, out['additionalContext'])
        self.assertNotIn('Rules for this action:', out['additionalContext'])

    def test_late_notice_comes_from_rules_only(self):
        self.write_cache([lesson(7)])
        self.assertIn(LATE_PHRASE, self.bash('git commit -m x', cwd=CWD)['additionalContext'])
        self.write_cache([lesson(7), lesson(8)])
        out = self.bash('git commit -m again', cwd=CWD)  # rules already delivered, lesson 8 is new
        self.assertEqual(self.ids(out), [8])
        self.assertNotIn(LATE_PHRASE, out['additionalContext'])

    def test_draft_lessons_are_never_injected(self):
        self.write_cache([lesson(1, draft=True), lesson(2, draft=False), lesson(3)])
        self.assertEqual(sorted(self.ids(self.bash('git commit -m x', cwd=CWD))), [2, 3])

    def test_only_draft_lessons_leave_no_section(self):
        self.write_cache([lesson(1, draft=True)])
        self.assertNotIn('Lessons for this action:', self.bash('git commit -m x', cwd=CWD)['additionalContext'])

    def test_project_lessons_come_before_others_regardless_of_hits(self):
        self.write_cache([lesson(1, group='other', hits=99), lesson(2, group='dotfiles', hits=1),
                          lesson(3, group='elsewhere', hits=50), lesson(4, group='dotfiles', hits=2)])
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD)), [4, 2, 1, 3])

    def test_project_match_normalizes_names_and_matches_any_cwd_component(self):
        self.write_cache([lesson(1, group='Other', hits=9), lesson(2, group='My Cool-Project', hits=1)])
        out = self.bash('git commit -m x', cwd='/home/andres/www/my_cool.project/app/Http')
        self.assertEqual(self.ids(out), [2, 1])

    def test_without_cwd_there_is_no_project_tier(self):
        self.write_cache([lesson(1, hits=1), lesson(2, hits=5)])
        self.assertEqual(self.ids(self.bash('git commit -m x')), [2, 1])

    def test_order_within_a_tier_is_hits_then_last_seen_then_id(self):
        self.write_cache([lesson(10, hits=1, last_seen='2026-11-09'),
                          lesson(11, hits=3, last_seen='2026-01-01'),
                          lesson(12, hits=3, last_seen='2026-02-01'),
                          lesson(14, hits=2, last_seen='2026-05-05'),
                          lesson(13, hits=2, last_seen='2026-05-05')])
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD)), [12, 11, 13, 14, 10])

    def test_default_cap_is_five(self):
        self.write_cache([lesson(i, hits=100 - i) for i in range(1, 9)])
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD)), [1, 2, 3, 4, 5])

    def test_lesson_cap_env_overrides_the_cap(self):
        self.write_cache([lesson(i, hits=100 - i) for i in range(1, 9)])
        env = {**self.env, 'LESSON_CAP': '2'}
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD, env=env)), [1, 2])

    def test_the_cap_applies_after_the_project_tier_ordering(self):
        self.write_cache([lesson(1, group='other', hits=99), lesson(2, hits=1), lesson(3, hits=2)])
        env = {**self.env, 'LESSON_CAP': '2'}
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD, env=env)), [3, 2])

    def test_prompt_without_keys_gets_no_lessons(self):
        self.write_cache([lesson(1, triggers=['git commit', 'peer prompt'])])
        out = self.prompt('hello', cwd=CWD)
        self.assertNotIn('Lessons for this action', out['additionalContext'])
        self.assertNotIn('[lesson', out['additionalContext'])

    def test_prompt_with_keys_gets_lessons(self):
        self.write_cache([lesson(1, triggers=['peer prompt'])])
        out = self.prompt('[sessioneer peer: a · /x · master] hi', cwd=CWD)
        self.assertEqual(self.ids(out), [1])
        self.assertIn('TEXT-928', out['additionalContext'])

    def test_read_events_without_keys_stay_silent(self):
        self.write_cache([lesson(1)])
        self.assertIsNone(self.run_hook(hook_event_name='PreToolUse', tool_name='Read', tool_input={}, cwd=CWD))


class LessonFormatTest(LessonBase):
    """Group: rendering. One short line per lesson, bounded size."""

    def test_header_and_one_line_per_lesson(self):
        self.write_cache([lesson(1, hits=3, triggers=['git add all']), lesson(2, hits=2, triggers=['git add all'])])
        ctx = self.bash('git add -A', cwd=CWD)['additionalContext']
        tail = ctx[ctx.index('Lessons for this action:'):]
        self.assertEqual(tail.splitlines(), ['Lessons for this action:', '[lesson 1] summary 1', '[lesson 2] summary 2'])

    def test_newlines_in_a_summary_become_spaces(self):
        self.write_cache([lesson(1, 'first line\nsecond line\r\nthird')])
        ctx = self.bash('git commit -m x', cwd=CWD)['additionalContext']
        self.assertIn('[lesson 1] first line second line', ctx)
        self.assertEqual(len(LESSON_LINE.findall(ctx)), 1)
        self.assertNotIn('\nsecond line', ctx)

    def test_summary_is_cut_to_120_characters(self):
        self.write_cache([lesson(1, 'x' * 300), lesson(2, 'y' * 120, hits=0), lesson(3, 'z' * 119, hits=0)])
        ctx = self.bash('git commit -m x', cwd=CWD)['additionalContext']
        self.assertIn('[lesson 1] ' + 'x' * 120 + '\n', ctx + '\n')
        self.assertNotIn('x' * 121, ctx)
        self.assertIn('[lesson 2] ' + 'y' * 120, ctx)
        self.assertIn('[lesson 3] ' + 'z' * 119, ctx)

    def test_five_long_lessons_stay_under_1000_characters(self):
        self.write_cache([lesson(100 + i, 'w' * 300, triggers=['git add all'], hits=10 - i) for i in range(7)])
        ctx = self.bash('git add -A', cwd=CWD)['additionalContext']
        self.assertEqual(len(LESSON_LINE.findall(ctx)), 5)
        self.assertLess(len(ctx), 1000)


class LessonDedupeTest(LessonBase):
    """Group: delivered state. A lesson goes out once per session and agent, and resets with the rules."""

    def test_second_call_in_a_session_does_not_repeat_a_lesson(self):
        self.write_cache([lesson(1)])
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD)), [1])
        self.assertIsNone(self.bash('git commit -m again', cwd=CWD))

    def test_cap_leaves_lessons_for_the_next_call(self):
        self.write_cache([lesson(i, hits=100 - i) for i in range(1, 5)])
        env = {**self.env, 'LESSON_CAP': '2'}
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD, env=env)), [1, 2])
        second = self.bash('git commit -m x', cwd=CWD, env=env)
        self.assertEqual(self.ids(second), [3, 4])
        self.assertNotIn('TEXT-732', second['additionalContext'])  # rules were delivered with the first call
        self.assertIsNone(self.bash('git commit -m x', cwd=CWD, env=env))

    def test_lessons_are_delivered_even_when_the_rules_already_were(self):
        self.assertIsNotNone(self.bash('git commit -m x', cwd=CWD))  # rules only, empty cache
        self.write_cache([lesson(1)])
        out = self.bash('git commit -m x', cwd=CWD)
        self.assertEqual(self.ids(out), [1])
        self.assertNotIn('TEXT-732', out['additionalContext'])

    def test_delivery_is_recorded_as_lesson_line_in_the_rules_state_file(self):
        self.write_cache([lesson(42)])
        self.bash('git commit -m x', cwd=CWD, session_id='sess9')
        lines = (self.tmp / 'state' / 'sess9-main').read_text().split()
        self.assertIn('lesson:42', lines)
        self.assertIn('732@1', lines)

    def test_a_lesson_for_another_trigger_is_not_marked_delivered(self):
        self.write_cache([lesson(42, triggers=['git push'])])
        self.bash('git commit -m x', cwd=CWD, session_id='sess9')
        state = (self.tmp / 'state' / 'sess9-main').read_text().split()
        self.assertNotIn('lesson:42', state)
        self.assertEqual(self.ids(self.bash('git push', cwd=CWD, session_id='sess9')), [42])

    def test_a_new_session_gets_the_lessons_again(self):
        self.write_cache([lesson(1)])
        self.bash('git commit -m x', cwd=CWD)
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD, session_id='s2')), [1])

    def test_subagents_have_their_own_delivered_set(self):
        self.write_cache([lesson(1)])
        self.bash('git commit -m x', cwd=CWD)
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD, agent_id='a1')), [1])
        self.assertIsNone(self.bash('git commit -m x', cwd=CWD, agent_id='a1'))

    def test_session_start_compact_clear_resume_reset_lessons(self):
        self.write_cache([lesson(1)])
        for source in ('compact', 'clear', 'resume'):
            self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD)), [1], source)
            self.assertIsNone(self.bash('git commit -m x', cwd=CWD), source)
            self.run_hook(hook_event_name='SessionStart', source=source)
        self.assertEqual(self.ids(self.bash('git commit -m x', cwd=CWD)), [1])

    def test_session_start_startup_keeps_delivered_lessons(self):
        self.write_cache([lesson(1)])
        self.bash('git commit -m x', cwd=CWD)
        self.run_hook(hook_event_name='SessionStart', source='startup')
        self.assertIsNone(self.bash('git commit -m x', cwd=CWD))

    def test_a_revised_rule_resend_does_not_resend_a_delivered_lesson(self):
        self.write_cache([lesson(1)])
        self.bash('git commit -m x', cwd=CWD)
        (self.tmp / 'rules.md').write_text((self.tmp / 'rules.md').read_text().replace('732@1', '732@2'))
        out = self.bash('git commit -m x', cwd=CWD)
        self.assertIn('TEXT-732', out['additionalContext'])
        self.assertEqual(self.ids(out), [])


class LessonFailSilentTest(LessonBase):
    """Group: sad paths. A broken cache never blocks the hook or the rules."""

    def assert_rules_still_delivered(self, session):
        out = self.bash('git commit -m x', cwd=CWD, session_id=session)
        self.assertIn('TEXT-732', out['additionalContext'])
        self.assertNotIn('[lesson', out['additionalContext'])

    def test_missing_cache(self):
        self.assert_rules_still_delivered('a')

    def test_cache_that_is_not_json_or_not_an_object(self):
        for i, raw in enumerate(('', 'not json', '\x00\xff', '[]', '"x"', '42', 'null', '{"lessons": 5}',
                                 '{"lessons": null}', '{"generated": "now", "lessons": {"a": 1}}')):
            self.cache.write_text(raw)
            self.assert_rules_still_delivered(f's{i}')

    def test_unreadable_cache(self):
        self.cache.mkdir()  # a directory where the file should be
        self.assert_rules_still_delivered('a')

    def test_entries_with_wrong_types_or_missing_fields_are_skipped(self):
        bad = [None, 5, 'x', [], {}, {'id': 1}, {'summary': 'no id', 'triggers': ['git commit']},
               {'id': 'two', 'summary': 's', 'triggers': ['git commit']},
               {'id': 3, 'summary': None, 'triggers': ['git commit']},
               {'id': 4, 'summary': 's', 'triggers': 'git commit'},
               {'id': 5, 'summary': 's', 'triggers': [None, 7]},
               {'id': 6, 'summary': 's'}]
        self.write_cache(bad + [lesson(99, 'the good one')])
        out = self.bash('git commit -m x', cwd=CWD)
        self.assertIn('TEXT-732', out['additionalContext'])
        self.assertEqual(self.ids(out), [99])

    def test_entry_with_bad_hits_or_last_seen_does_not_hide_good_ones(self):
        self.write_cache([lesson(1, hits='many'), lesson(2, last_seen=None), lesson(3, hits=5)])
        out = self.bash('git commit -m x', cwd=CWD)
        self.assertIn(3, self.ids(out))
        self.assertEqual(self.ids(out)[0], 3)

    def test_bad_lesson_cap_falls_back_without_failing(self):
        self.write_cache([lesson(i, hits=100 - i) for i in range(1, 9)])
        for cap in ('abc', '', '-1'):
            out = self.bash('git commit -m x', cwd=CWD, env={**self.env, 'LESSON_CAP': cap}, session_id='c' + cap)
            self.assertIn('TEXT-732', out['additionalContext'])

    def test_unwritable_cache_location_is_silent(self):
        env = {**self.env, 'LESSON_CACHE': str(self.tmp / 'no' / 'such' / 'dir' / 'x.json')}
        out = self.bash('git commit -m x', cwd=CWD, env=env)
        self.assertIn('TEXT-732', out['additionalContext'])


class LessonRefreshTest(LessonBase):
    """Group: background refresh. Stale or missing cache starts a detached refresh; the hook never waits."""

    def setUp(self):
        super().setUp()
        self.marker = self.tmp / 'marker'
        self.stub = self.tmp / 'refresh-stub'
        make_stub(self.stub, counter=self.marker)
        self.env['LESSON_REFRESH'] = 'on'
        self.env['LESSON_REFRESH_CMD'] = str(self.stub)

    def runs(self, wait=3.0):
        deadline = time.time() + wait
        while time.time() < deadline:
            if self.marker.exists() and self.marker.read_text().strip():
                break
            time.sleep(0.05)
        return len(self.marker.read_text().split()) if self.marker.exists() else 0

    def assert_no_refresh(self):
        time.sleep(0.7)
        self.assertEqual(self.runs(wait=0), 0)

    def test_missing_cache_starts_a_refresh(self):
        self.bash('git commit -m x', cwd=CWD)
        self.assertEqual(self.runs(), 1)

    def test_stale_cache_starts_a_refresh_with_the_default_ttl(self):
        self.write_cache([lesson(1)], generated=time.time() - 7200)
        out = self.bash('git commit -m x', cwd=CWD)
        self.assertEqual(self.runs(), 1)
        self.assertEqual(self.ids(out), [1])  # the stale cache is still used for this call

    def test_fresh_cache_does_not_start_a_refresh(self):
        self.write_cache([lesson(1)], generated=time.time() - 60)
        self.bash('git commit -m x', cwd=CWD)
        self.assert_no_refresh()

    def test_lesson_ttl_env_sets_the_age_limit(self):
        env = {**self.env, 'LESSON_TTL': '30'}
        self.write_cache([lesson(1)], generated=time.time() - 10)
        self.bash('git commit -m x', cwd=CWD, env=env)
        self.assert_no_refresh()
        self.write_cache([lesson(1)], generated=time.time() - 120)
        self.bash('git commit -m x', cwd=CWD, env=env, session_id='s2')
        self.assertEqual(self.runs(), 1)

    def test_lesson_refresh_off_disables_it(self):
        env = {**self.env, 'LESSON_REFRESH': 'off'}
        self.bash('git commit -m x', cwd=CWD, env=env)
        self.assert_no_refresh()

    def test_cache_without_a_usable_generated_counts_as_stale(self):
        for gen in ('x', None):
            self.cache.write_text(json.dumps({'generated': gen, 'lessons': [lesson(1)]}))
            self.marker.unlink(missing_ok=True)
            self.bash('git commit -m x', cwd=CWD, session_id=f'g{gen}')
            self.assertEqual(self.runs(), 1, gen)

    def test_the_hook_does_not_wait_for_a_slow_refresh(self):
        make_stub(self.stub, counter=self.marker)
        text = self.stub.read_text().replace("printf '%s' ''", 'sleep 3')
        self.stub.write_text(text)
        started = time.time()
        self.bash('git commit -m x', cwd=CWD)  # run_hook waits for the pipes: the child must be detached from them
        self.assertLess(time.time() - started, 1.0)
        self.assertEqual(self.runs(), 1)

    def test_refresh_command_is_shlex_split(self):
        args = self.tmp / 'args'
        make_stub(self.stub, counter=self.marker, args=args)
        self.env['LESSON_REFRESH_CMD'] = f"{self.stub} --flag 'two words'"
        self.bash('git commit -m x', cwd=CWD)
        self.assertEqual(self.runs(), 1)
        time.sleep(0.2)
        self.assertEqual(args.read_text().strip(), '--flag two words')

    def test_broken_refresh_command_is_silent(self):
        self.env['LESSON_REFRESH_CMD'] = str(self.tmp / 'does-not-exist')
        out = self.bash('git commit -m x', cwd=CWD)
        self.assertIn('TEXT-732', out['additionalContext'])
        self.env['LESSON_REFRESH_CMD'] = "unbalanced 'quote"
        out = self.bash('git commit -m x', cwd=CWD, session_id='s2')
        self.assertIn('TEXT-732', out['additionalContext'])


if __name__ == '__main__':
    unittest.main()
