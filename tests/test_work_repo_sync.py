"""bin/work-repo-sync against throwaway bare 'production' remotes and clones in tmp_path."""
import fcntl
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'bin' / 'work-repo-sync'


class Env:
    def __init__(self, tmp):
        self.tmp = tmp
        self.home = tmp / 'home'
        self.home.mkdir()
        gc = tmp / 'gitconfig'
        gc.write_text('[user]\n\tname = t\n\temail = t@t\n[init]\n\tdefaultBranch = main\n'
                      '[advice]\n\tdetachedHead = false\n')
        self.env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_GLOBAL=str(gc),
                        GIT_CONFIG_NOSYSTEM='1', LC_ALL='C')
        for k in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
            self.env.pop(k, None)
        self.prod = tmp / 'prod.git'
        self.state = tmp / 'state'
        self.conf = tmp / 'repos.conf'
        self.g(tmp, 'init', '--bare', '-q', str(self.prod))
        self.seed = tmp / 'seed'
        self.g(tmp, 'clone', '-q', str(self.prod), str(self.seed))
        self.put(self.seed, 'a.txt', '1\n2\n3\n')
        self.put(self.seed, 'b.txt', 'b\n')
        self.g(self.seed, 'add', '.')
        self.g(self.seed, 'commit', '-qm', 'base')
        self.g(self.seed, 'push', '-q', 'origin', 'main')
        self.work = tmp / 'work'
        self.g(tmp, 'clone', '-q', str(self.prod), str(self.work))
        self.g(self.work, 'checkout', '-q', '-b', 'dev')
        for n in ('one', 'two'):
            self.put(self.work, f'dev_{n}.txt', n + '\n')
            self.g(self.work, 'add', '.')
            self.g(self.work, 'commit', '-qm', f'dev {n}')

    def g(self, path, *args, check=True):
        r = subprocess.run(['git', '-C', str(path), *args], env=self.env, capture_output=True, text=True)
        if check and r.returncode:
            raise AssertionError(f'git {args} failed: {r.stderr}')
        return r.stdout.strip()

    @staticmethod
    def put(repo, name, text):
        (Path(repo) / name).write_text(text)

    def advance(self, name='prod.txt', text='prod\n', msg='prod change'):
        self.put(self.seed, name, text)
        self.g(self.seed, 'add', '.')
        self.g(self.seed, 'commit', '-qm', msg)
        self.g(self.seed, 'push', '-q', 'origin', 'main')
        return self.g(self.seed, 'rev-parse', 'HEAD')

    def config(self, *lines):
        self.conf.write_text('\n'.join(lines) + '\n')

    def run(self, *extra, quiet='0', cfg=True, envx=None):
        if cfg and not self.conf.exists():
            self.config(f'{self.work}|origin|main|main|dev')
        env = dict(self.env)
        env.pop('WORK_SYNC_QUIET_MIN', None)
        if quiet is not None:
            env['WORK_SYNC_QUIET_MIN'] = quiet
        env.update(envx or {})
        r = subprocess.run([str(SCRIPT), '--config', str(self.conf), '--state-dir', str(self.state), *extra],
                           env=env, capture_output=True, text=True, timeout=120)
        return r

    def tip(self, ref, repo=None):
        return self.g(repo or self.work, 'rev-parse', ref)

    def refs(self, *prefixes, repo=None):
        return self.g(repo or self.work, 'for-each-ref', '--format=%(refname) %(objectname)', *prefixes)

    def attention(self):
        return (self.state / 'ATTENTION.md').read_text()

    def safety(self, repo=None):
        out = self.g(repo or self.work, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/work-sync/')
        return dict(line.split() for line in out.splitlines())

    def status(self, repo=None):
        return self.g(repo or self.work, 'status', '--porcelain', '-uall')


@pytest.fixture
def e(tmp_path):
    return Env(tmp_path)


def lines(r, word):
    return [ln for ln in r.stdout.splitlines() if ln.startswith(word)]


def msgs(e, ref='dev'):
    return e.g(e.work, 'log', '--format=%s', ref).splitlines()


def test_happy_path_mirror_ff_and_dev_rebased(e):
    """Per repo: fast-forwards mirror to production and rebases dev onto it; own commits and content preserved; exit 0; OK line."""
    old_dev = e.tip('dev')
    new = e.advance()
    r = e.run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert lines(r, 'OK') and not lines(r, 'FAIL')
    assert e.tip('main') == new
    assert e.g(e.work, 'merge-base', '--is-ancestor', 'main', 'dev', check=False) == ''
    assert e.g(e.work, 'merge-base', 'main', 'dev') == new
    assert msgs(e)[:2] == ['dev two', 'dev one']
    assert e.tip('dev') != old_dev
    assert (e.work / 'dev_one.txt').read_text() == 'one\n'
    assert (e.work / 'prod.txt').read_text() == 'prod\n'
    assert e.status() == ''


def test_state_dir_outputs_and_no_attention_needed(e):
    """State dir gets runs/<id>/summary.txt, per-repo logs, history.log, and ATTENTION.md 'needed no attention'."""
    e.advance()
    r = e.run()
    assert r.returncode == 0
    assert list((e.state / 'runs').glob('*/summary.txt'))
    assert len(list(p for p in (e.state / 'runs').glob('*/*') if p.name != 'summary.txt')) >= 1
    assert (e.state / 'history.log').exists()
    assert 'needed no attention' in e.attention()
    r2 = e.run()
    assert 'needed no attention' in e.attention()
    assert r2.returncode == 0


def test_safety_refs_hold_old_tips(e):
    """Before moving refs, permanent refs/work-sync/<run-id>/<branch> hold the old tips."""
    old_main, old_dev = e.tip('main'), e.tip('dev')
    e.advance()
    assert e.run().returncode == 0
    s = e.safety()
    by_branch = {k.split('/', 3)[3]: v for k, v in s.items()}
    assert by_branch['main'] == old_main
    assert by_branch['dev'] == old_dev


def test_no_push_and_only_the_named_branch_is_fetched(e):
    """Fetches only refs/heads/<remote_branch>; never pushes."""
    e.g(e.seed, 'push', '-q', 'origin', 'HEAD:refs/heads/other')
    e.advance()
    prod_before = e.refs(repo=e.prod)
    r = e.run()
    assert r.returncode == 0
    assert e.refs(repo=e.prod) == prod_before
    assert e.refs('refs/remotes/origin/other') == ''
    assert e.tip('refs/remotes/origin/main') == e.tip('main')


def test_dirty_work_and_preexisting_stashes_survive(e):
    """Dirty staged/unstaged/untracked work is stashed and restored with identical status; user stashes untouched; stash safety ref made."""
    for i in (1, 2):
        e.put(e.work, 'b.txt', f'stashed {i}\n')
        e.g(e.work, 'stash', 'push', '-m', f'user stash {i}')
    stashes_before = e.g(e.work, 'stash', 'list')
    e.put(e.work, 'staged.txt', 's\n')
    e.g(e.work, 'add', 'staged.txt')
    e.put(e.work, 'b.txt', 'unstaged edit\n')
    e.put(e.work, 'untracked.txt', 'u\n')
    status_before = e.status()
    e.advance()
    r = e.run()
    assert r.returncode == 0, r.stdout
    assert lines(r, 'OK')
    assert e.status() == status_before
    assert (e.work / 'untracked.txt').read_text() == 'u\n'
    assert e.g(e.work, 'stash', 'list') == stashes_before
    assert any(k.rsplit('/', 1)[1].startswith('stash-') for k in e.safety())
    assert e.tip('main') == e.tip('refs/remotes/origin/main')


def test_fetch_failure_is_fail_and_nothing_changes(e):
    """Fetch failure (bad remote) => FAIL, nothing changed."""
    e.g(e.work, 'remote', 'set-url', 'origin', str(e.tmp / 'does-not-exist.git'))
    before = e.refs()
    r = e.run()
    assert r.returncode == 1
    assert lines(r, 'FAIL')
    assert e.refs() == before
    assert 'FAIL' in e.attention()


def test_divergent_mirror_fails_closed(e):
    """Mirror diverged from production => FAIL, nothing changed, safety refs exist, dev not touched."""
    e.g(e.work, 'checkout', '-q', 'main')
    e.put(e.work, 'local.txt', 'x\n')
    e.g(e.work, 'add', '.')
    e.g(e.work, 'commit', '-qm', 'local mirror commit')
    e.g(e.work, 'checkout', '-q', 'dev')
    main_before, dev_before = e.tip('main'), e.tip('dev')
    e.advance()
    r = e.run()
    assert r.returncode == 1
    assert lines(r, 'FAIL')
    assert e.tip('main') == main_before
    assert e.tip('dev') == dev_before
    assert main_before in e.safety().values()
    assert 'FAIL' in e.attention()


def test_rebase_conflict_aborts_and_restores_dirty_work(e):
    """Dev rebase conflict => rebase --abort, dev tip unchanged, mirror still updated, uncommitted work restored, FAIL."""
    e.put(e.work, 'a.txt', '1\ndev edit\n3\n')
    e.g(e.work, 'commit', '-qam', 'dev edits a')
    dev_before = e.tip('dev')
    new = e.advance('a.txt', '1\nprod edit\n3\n', 'prod edits a')
    e.put(e.work, 'b.txt', 'dirty b\n')
    e.put(e.work, 'untracked.txt', 'u\n')
    status_before = e.status()
    r = e.run()
    assert r.returncode == 1
    assert lines(r, 'FAIL')
    assert e.tip('dev') == dev_before
    assert e.tip('main') == new
    assert e.status() == status_before
    git_dir = Path(e.g(e.work, 'rev-parse', '--absolute-git-dir'))
    assert not (git_dir / 'rebase-merge').exists() and not (git_dir / 'rebase-apply').exists()
    assert e.g(e.work, 'stash', 'list') == ''
    assert 'FAIL' in e.attention()


def test_failed_stash_restore_keeps_stash_and_reports_recovery(e):
    """Stash entry dropped only if status equals pre-stash status; otherwise kept, repo FAIL, recoverable via refs/work-sync/*/stash-*."""
    e.put(e.work, 'a.txt', '1\ndirty\n3\n')
    e.advance('a.txt', '1\nprod\n3\n', 'prod edits a')
    r = e.run()
    assert r.returncode == 1, r.stdout
    assert lines(r, 'FAIL')
    stash_refs = {k: v for k, v in e.safety().items() if k.rsplit('/', 1)[1].startswith('stash-')}
    assert stash_refs
    for sha in stash_refs.values():
        assert e.g(e.work, 'cat-file', '-t', sha) == 'commit'
        assert 'dirty' in e.g(e.work, 'show', f'{sha}:a.txt')
    assert e.g(e.work, 'stash', 'list') != ''
    assert 'refs/work-sync' in e.attention() and 'FAIL' in e.attention()
    assert 'stash' in e.attention()
    assert msgs(e)[:2] == ['dev two', 'dev one']
    assert e.tip('main') == e.tip('refs/remotes/origin/main')


def test_recovery_commands_listed_for_fail(e):
    """ATTENTION.md says it needs attention with a FAIL section including recovery commands."""
    e.g(e.work, 'remote', 'set-url', 'origin', str(e.tmp / 'nope.git'))
    e.run()
    text = e.attention()
    assert 'needed no attention' not in text
    assert 'FAIL' in text and 'git' in text


def _snapshot(e):
    return e.g(e.work, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads')


def _conflicting_rebase_in_progress(e):
    e.g(e.work, 'checkout', '-q', '-b', 'tmp', 'main')
    e.put(e.work, 'a.txt', '1\ntmp\n3\n')
    e.g(e.work, 'commit', '-qam', 'tmp')
    e.g(e.work, 'checkout', '-q', 'dev')
    e.put(e.work, 'a.txt', '1\ndev\n3\n')
    e.g(e.work, 'commit', '-qam', 'dev a')
    r = e.g(e.work, 'rebase', 'tmp', check=False)
    git_dir = Path(e.g(e.work, 'rev-parse', '--absolute-git-dir'))
    assert (git_dir / 'rebase-merge').exists() or (git_dir / 'rebase-apply').exists()


def _index_lock(e):
    (Path(e.g(e.work, 'rev-parse', '--absolute-git-dir')) / 'index.lock').write_text('')


def _unmerged(e):
    e.g(e.work, 'checkout', '-q', '-b', 'side', 'main')
    e.put(e.work, 'a.txt', '1\nside\n3\n')
    e.g(e.work, 'commit', '-qam', 'side')
    e.g(e.work, 'checkout', '-q', 'dev')
    e.put(e.work, 'a.txt', '1\ndev\n3\n')
    e.g(e.work, 'commit', '-qam', 'dev a')
    e.g(e.work, 'merge', 'side', check=False)
    assert 'U' in e.g(e.work, 'status', '--porcelain')


@pytest.mark.parametrize('setup', [_conflicting_rebase_in_progress, _index_lock, _unmerged],
                         ids=['rebase-in-progress', 'index-lock', 'unmerged-paths'])
def test_busy_repo_is_not_touched(e, setup):
    """Repo with rebase in progress, index.lock or unmerged paths => BUSY and nothing changed."""
    setup(e)
    e.advance()
    before = _snapshot(e)
    r = e.run()
    assert lines(r, 'BUSY'), r.stdout
    assert not lines(r, 'OK')
    assert _snapshot(e) == before
    assert r.returncode == 0


def test_held_repo_flock_is_busy(e):
    """A held flock on <git-common-dir>/work-repo-sync.lock => BUSY and nothing changed."""
    e.advance()
    before = _snapshot(e)
    common = Path(e.g(e.work, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    with open(common / 'work-repo-sync.lock', 'w') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        r = e.run()
    assert lines(r, 'BUSY'), r.stdout
    assert _snapshot(e) == before


def test_dev_published_to_remote_is_skipped_with_decision(e):
    """Dev commits already on any remote-tracking ref => SKIP (no rewrite), DECISION in ATTENTION.md, mirror still updated."""
    e.g(e.work, 'push', '-q', 'origin', 'dev')
    dev_before = e.tip('dev')
    new = e.advance()
    r = e.run()
    assert lines(r, 'SKIP'), r.stdout
    assert e.tip('dev') == dev_before
    assert e.tip('main') == new
    assert 'DECISION' in e.attention()


def test_dev_with_merge_commits_is_skipped(e):
    """Dev with merge commits => SKIP."""
    e.g(e.work, 'checkout', '-q', '-b', 'side', 'dev~1')
    e.put(e.work, 'side.txt', 's\n')
    e.g(e.work, 'add', '.')
    e.g(e.work, 'commit', '-qm', 'side work')
    e.g(e.work, 'checkout', '-q', 'dev')
    e.g(e.work, 'merge', '--no-ff', '-qm', 'merge side', 'side')
    dev_before = e.tip('dev')
    e.advance()
    r = e.run()
    assert lines(r, 'SKIP'), r.stdout
    assert e.tip('dev') == dev_before


def test_mirror_ahead_of_production_is_left_alone(e):
    """Mirror ahead of production by unpublished commits => not touched, not an error."""
    e.g(e.work, 'checkout', '-q', 'main')
    e.put(e.work, 'local.txt', 'x\n')
    e.g(e.work, 'add', '.')
    e.g(e.work, 'commit', '-qm', 'unpublished')
    e.g(e.work, 'checkout', '-q', 'dev')
    main_before = e.tip('main')
    r = e.run()
    assert r.returncode == 0, r.stdout
    assert not lines(r, 'FAIL')
    assert e.tip('main') == main_before


def test_dry_run_changes_no_refs(e):
    """--dry-run changes no refs and prints DRYRUN."""
    e.advance()
    before = e.g(e.work, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/work-sync')
    r = e.run('--dry-run')
    assert r.returncode == 0
    assert lines(r, 'DRYRUN'), r.stdout
    after = e.g(e.work, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/work-sync')
    assert after == before


def test_only_filters_by_path_substring(e):
    """--only filters by substring of path."""
    other = e.tmp / 'otherrepo'
    e.g(e.tmp, 'clone', '-q', str(e.prod), str(other))
    e.config(f'{e.work}|origin|main|main|dev', f'{other}|origin|main|main|-')
    new = e.advance()
    r = e.run('--only', 'otherrepo')
    assert r.returncode == 0
    assert e.tip('main', other) == new
    assert e.tip('main') != new
    assert len(lines(r, 'OK')) == 1


def test_no_dev_branch_mirror_checked_out_dirty(e):
    """'-' = no dev; mirror checked out and updated with dirty worktree, status preserved."""
    e.g(e.work, 'checkout', '-q', 'main')
    e.config(f'{e.work}|origin|main|main|-')
    e.put(e.work, 'b.txt', 'dirty\n')
    e.put(e.work, 'untracked.txt', 'u\n')
    status_before = e.status()
    new = e.advance()
    r = e.run()
    assert r.returncode == 0, r.stdout
    assert e.tip('main') == new
    assert (e.work / 'prod.txt').exists()
    assert e.status() == status_before


def test_concurrent_run_exits_2(e):
    """A second concurrent run (run.lock held) exits 2."""
    e.state.mkdir(parents=True)
    e.advance()
    before = _snapshot(e)
    with open(e.state / 'run.lock', 'w') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        r = e.run()
    assert r.returncode == 2
    assert _snapshot(e) == before


def test_usage_and_missing_config_exit_2(e):
    """Usage problems exit 2."""
    assert e.run('--bogus-flag', cfg=False).returncode == 2
    e.conf = e.tmp / 'missing.conf'
    assert e.run(cfg=False).returncode == 2


def test_shared_bare_repo_with_worktrees(e):
    """Multiple worktrees sharing one bare repo (mirror in one, dev in another) work."""
    bare = e.tmp / 'shared.git'
    e.g(e.tmp, 'clone', '-q', '--bare', str(e.prod), str(bare))
    e.g(bare, 'branch', 'dev', 'main')
    wt_main, wt_dev = e.tmp / 'wt-main', e.tmp / 'wt-dev'
    e.g(bare, 'worktree', 'add', '-q', str(wt_main), 'main')
    e.g(bare, 'worktree', 'add', '-q', str(wt_dev), 'dev')
    e.put(wt_dev, 'dev_only.txt', 'd\n')
    e.g(wt_dev, 'add', '.')
    e.g(wt_dev, 'commit', '-qm', 'dev only')
    e.config(f'{wt_dev}|origin|main|main|dev')
    new = e.advance()
    r = e.run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert lines(r, 'OK') and not lines(r, 'FAIL')
    assert e.tip('main', bare) == new
    assert e.g(bare, 'merge-base', 'main', 'dev') == new
    assert e.g(bare, 'log', '-1', '--format=%s', 'dev') == 'dev only'
    assert (wt_main / 'prod.txt').exists()
    assert (wt_dev / 'prod.txt').exists() and (wt_dev / 'dev_only.txt').exists()
    assert e.status(wt_main) == '' and e.status(wt_dev) == ''


def test_recently_touched_dirty_files_are_active_and_skipped(e):
    """With the default quiet window, dirty files touched just now mark the worktree active => SKIP, nothing changed."""
    e.put(e.work, 'untracked.txt', 'fresh\n')
    e.advance()
    before = _snapshot(e)
    r = e.run(quiet=None)
    assert lines(r, 'SKIP') or lines(r, 'BUSY'), r.stdout
    assert not lines(r, 'OK')
    assert e.tip('dev') == before.split('dev ')[1].split()[0]
    assert (e.work / 'untracked.txt').read_text() == 'fresh\n'


def test_slashed_branch_names_get_underscore_safety_refs(e):
    """Safety refs replace '/' in branch names with '_'; slashed mirror/dev names do not abort the run.
    (A mirror 'release' plus dev 'release/x' cannot coexist in git itself, so that D/F pair is not constructible.)"""
    e.g(e.work, 'branch', 'feat/m', 'main')
    e.g(e.work, 'checkout', '-q', '-b', 'feat/d', 'feat/m')
    e.put(e.work, 'fd.txt', 'x\n')
    e.g(e.work, 'add', '.')
    e.g(e.work, 'commit', '-qm', 'feat d')
    e.config(f'{e.work}|origin|main|feat/m|feat/d')
    old_m, old_d = e.tip('feat/m'), e.tip('feat/d')
    new = e.advance()
    r = e.run()
    assert r.returncode == 0, r.stdout
    by = {k.split('/', 3)[3]: v for k, v in e.safety().items()}
    assert by['feat_m'] == old_m and by['feat_d'] == old_d
    assert e.tip('feat/m') == new and e.g(e.work, 'merge-base', 'feat/m', 'feat/d') == new


def test_unwritable_safety_refs_fail_and_nothing_moves(e):
    """If safety refs cannot be written (refs/work-sync is a regular file) the run FAILs and no branch moves."""
    common = Path(e.g(e.work, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    (common / 'refs' / 'work-sync').write_text('not a dir\n')
    e.advance()
    before = _snapshot(e)
    r = e.run()
    assert r.returncode == 1, r.stdout
    assert lines(r, 'FAIL')
    assert _snapshot(e) == before


def test_unwritable_repo_lock_fails_that_repo_only(e):
    """An unwritable <git-common-dir>/work-repo-sync.lock (a directory) => FAIL for that repo; the run continues to the next repo."""
    common = Path(e.g(e.work, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    (common / 'work-repo-sync.lock').mkdir()
    other = e.tmp / 'second'
    e.g(e.tmp, 'clone', '-q', str(e.prod), str(other))
    e.config(f'{e.work}|origin|main|main|dev', f'{other}|origin|main|main|-')
    before = _snapshot(e)
    new = e.advance()
    r = e.run()
    assert r.returncode == 1
    assert len(lines(r, 'FAIL')) == 1 and str(e.work) in lines(r, 'FAIL')[0]
    assert _snapshot(e) == before
    assert any(str(other) in ln for ln in lines(r, 'OK'))
    assert e.tip('main', other) == new


def test_run_lock_released_after_run(e):
    """After a normal run no process keeps <state>/run.lock: an immediate second run succeeds with exit 0."""
    e.advance()
    assert e.run().returncode == 0
    with open(e.state / 'run.lock', 'w') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert e.run().returncode == 0


def test_active_dirty_worktree_is_busy_but_mirror_ff_by_ref(e):
    """Active (recently touched dirty) worktree => BUSY, dev untouched, mirror (not checked out) still fast-forwarded by ref."""
    e.put(e.work, 'untracked.txt', 'fresh\n')
    dev_before = e.tip('dev')
    new = e.advance()
    r = e.run(quiet=None)
    assert lines(r, 'BUSY'), r.stdout
    assert e.tip('dev') == dev_before
    assert e.tip('main') == new


def test_just_deleted_tracked_file_counts_as_active(e):
    """A dirty file deleted just now (default quiet window) counts as active => BUSY, nothing rebased, deletion kept."""
    (e.work / 'b.txt').unlink()
    dev_before = e.tip('dev')
    e.advance()
    r = e.run(quiet=None)
    assert lines(r, 'BUSY'), r.stdout
    assert not lines(r, 'OK') and not lines(r, 'FAIL')
    assert e.tip('dev') == dev_before
    assert not (e.work / 'b.txt').exists()


def test_dry_run_still_may_fetch_but_moves_no_branch(e):
    """Dry run may update remote-tracking refs but never branches or refs/work-sync."""
    new = e.advance()
    before = e.g(e.work, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/work-sync')
    assert e.run('--dry-run').returncode == 0
    assert e.g(e.work, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/work-sync') == before
    assert e.tip('main') != new


# ---- auto-discovery (opt-in by env) ----------------------------------------

def _disc(e, sub='proj', url=None):
    root = e.tmp / 'droot'
    root.mkdir(exist_ok=True)
    repo = root / sub
    repo.parent.mkdir(parents=True, exist_ok=True)
    e.g(e.tmp, 'clone', '-q', url or str(e.prod), str(repo))
    return repo


def _denv(e, **more):
    e.conf.write_text(getattr(e, '_cfgtext', ''))
    d = {'WORK_SYNC_DISCOVER_ROOT': str(e.tmp / 'droot'),
         'WORK_SYNC_AUTO_CONFIG': str(e.tmp / 'auto.conf')}
    d.update({k: str(v) for k, v in more.items()})
    return d


def _auto(e):
    p = e.tmp / 'auto.conf'
    return p.read_text() if p.exists() else ''


def test_discover_imports_and_syncs_in_same_run(e):
    """Discovery imports a repo whose main tracks a non-forge remote (dev='local' if that branch exists), syncs it the same run, lists it under AUTO-IMPORTED, and does not import twice."""
    repo = _disc(e)
    e.g(repo, 'checkout', '-q', '-b', 'local')
    e.put(repo, 'loc.txt', 'l\n')
    e.g(repo, 'add', '.')
    e.g(repo, 'commit', '-qm', 'local work')
    new = e.advance()
    env = _denv(e)
    r = e.run(envx=env)
    assert r.returncode == 0, r.stdout
    assert str(repo) in _auto(e) and _auto(e).count(str(repo)) == 1
    assert _auto(e).strip().endswith('|local')
    assert e.tip('main', repo) == new
    assert e.g(repo, 'merge-base', 'main', 'local') == new
    assert 'AUTO-IMPORTED' in e.attention()
    e.run(envx=env)
    assert _auto(e).count(str(repo)) == 1


def test_discover_without_local_branch_uses_dash(e):
    """dev is '-' when no local branch exists."""
    repo = _disc(e)
    e.run(envx=_denv(e))
    assert _auto(e).strip().endswith('|-')


def test_discover_forge_remote_reported_once_not_imported(e):
    """A forge-URL remote is refused: SKIP line + 'NEW REPO NOT SYNCED' once, not repeated, not imported."""
    repo = _disc(e)
    e.g(repo, 'remote', 'set-url', 'origin', 'https://github.com/x/y.git')
    env = _denv(e)
    r = e.run(envx=env)
    assert any(ln.startswith('SKIP') and str(repo) in ln for ln in r.stdout.splitlines()), r.stdout
    assert 'NEW REPO NOT SYNCED' in e.attention()
    assert str(repo) not in _auto(e)
    r2 = e.run(envx=env)
    assert not any(ln.startswith('SKIP') and str(repo) in ln for ln in r2.stdout.splitlines())
    assert 'NEW REPO NOT SYNCED' not in e.attention()


def test_discover_custom_forge_regex(e):
    """WORK_SYNC_FORGE_RE overrides which URLs are refused."""
    repo = _disc(e)
    e.run(envx=_denv(e, WORK_SYNC_FORGE_RE='prod\\.git'))
    assert str(repo) not in _auto(e)
    assert 'NEW REPO NOT SYNCED' in e.attention()


def test_discover_skips_repo_already_in_config(e):
    """Repos whose git common dir is already in the config are skipped by discovery."""
    repo = _disc(e)
    e._cfgtext = f'{repo}|origin|main|main|-\n'
    e.run(envx=_denv(e))
    assert str(repo) not in _auto(e)
    assert 'AUTO-IMPORTED' not in e.attention()
    assert 'NEW REPO NOT SYNCED' not in e.attention()


def test_discover_ignore_file(e):
    """Paths matching a substring in the WORK_SYNC_IGNORE file are skipped."""
    repo = _disc(e, 'skipme')
    ign = e.tmp / 'ignore'
    ign.write_text('skipme\n')
    e.run(envx=_denv(e, WORK_SYNC_IGNORE=ign))
    assert str(repo) not in _auto(e)
    assert 'NEW REPO NOT SYNCED' not in e.attention()


@pytest.mark.parametrize('sub', ['vendor/x', 'node_modules/x', '_archive1/x', 'foo-backup-1/x', '_pre-unify-a/x'])
def test_discover_prunes_directories(e, sub):
    """Discovery prunes vendor, node_modules, _archive*, *backup*, _pre-unify*."""
    repo = _disc(e, sub)
    e.run(envx=_denv(e))
    assert str(repo) not in _auto(e)
    assert 'NEW REPO NOT SYNCED' not in e.attention()


def test_discover_old_remote_ref_not_imported(e):
    """A remote-tracking ref older than WORK_SYNC_RECENT_DAYS is reported, not imported."""
    old = {'GIT_AUTHOR_DATE': '2020-01-01T00:00:00', 'GIT_COMMITTER_DATE': '2020-01-01T00:00:00'}
    prod2 = e.tmp / 'prod2.git'
    e.g(e.tmp, 'init', '--bare', '-q', str(prod2))
    s2 = e.tmp / 'seed2'
    e.g(e.tmp, 'clone', '-q', str(prod2), str(s2))
    e.put(s2, 'x', 'x\n')
    e.g(s2, 'add', '.')
    subprocess.run(['git', '-C', str(s2), 'commit', '-qm', 'old'], env={**e.env, **old}, check=True)
    e.g(s2, 'push', '-q', 'origin', 'main')
    repo = _disc(e, url=str(prod2))
    e.run(envx=_denv(e))
    assert str(repo) not in _auto(e)
    assert 'NEW REPO NOT SYNCED' in e.attention()


def test_discover_diverged_not_imported(e):
    """A repo whose main is diverged from its remote-tracking ref is reported, not imported."""
    repo = _disc(e)
    e.put(repo, 'loc.txt', 'l\n')
    e.g(repo, 'add', '.')
    e.g(repo, 'commit', '-qm', 'local on main')
    e.advance()
    e.g(repo, 'fetch', '-q', 'origin')
    e.run(envx=_denv(e))
    assert str(repo) not in _auto(e)
    assert 'NEW REPO NOT SYNCED' in e.attention()


def test_discover_skipped_on_dry_run_and_only(e):
    """--dry-run and --only skip discovery."""
    repo = _disc(e)
    e.config(f'{e.work}|origin|main|main|dev')
    env = _denv(e)
    e.conf.write_text(f'{e.work}|origin|main|main|dev\n')
    e.run('--dry-run', envx=env)
    e.run('--only', 'work', envx=env)
    assert str(repo) not in _auto(e)
    assert 'NEW REPO NOT SYNCED' not in e.attention()


# ---- notification (opt-in by env) -------------------------------------------

def _notifier(e, exit_code=0):
    log = e.tmp / 'notify.log'
    sh = e.tmp / 'notify.sh'
    sh.write_text(f'#!/bin/sh\nprintf "%s\\n" "$#" "$1" >> {log}\nexit {exit_code}\n')
    sh.chmod(0o755)
    return sh, log


def test_notify_not_called_on_clean_run(e):
    """Clean run => notify command not called."""
    sh, log = _notifier(e)
    e.advance()
    assert e.run(envx={'WORK_SYNC_NOTIFY_CMD': str(sh)}).returncode == 0
    assert not log.exists()


def test_notify_called_once_with_subject_and_body(e):
    """Non-empty attention content, not dry-run => notify called once with (subject, body)."""
    sh, log = _notifier(e)
    e.g(e.work, 'remote', 'set-url', 'origin', str(e.tmp / 'nope.git'))
    r = e.run(envx={'WORK_SYNC_NOTIFY_CMD': str(sh)})
    assert r.returncode == 1
    out = log.read_text().splitlines()
    assert out[0] == '2' and len(out) == 2 and out[1]


def test_notify_not_called_on_dry_run(e):
    """Dry run => notify not called even with attention content."""
    sh, log = _notifier(e)
    e.g(e.work, 'remote', 'set-url', 'origin', str(e.tmp / 'nope.git'))
    e.run('--dry-run', envx={'WORK_SYNC_NOTIFY_CMD': str(sh)})
    assert not log.exists()


def test_failing_notify_is_reported_without_changing_exit_code(e):
    """A failing notify command prints NOTIFICATION FAILED; the exit code is unaffected."""
    sh, log = _notifier(e, 3)
    e.g(e.work, 'remote', 'set-url', 'origin', str(e.tmp / 'nope.git'))
    r = e.run(envx={'WORK_SYNC_NOTIFY_CMD': str(sh)})
    assert 'NOTIFICATION FAILED' in r.stdout + r.stderr
    assert r.returncode == 1
    e.g(e.work, 'remote', 'set-url', 'origin', str(e.prod))
    r = e.run(envx={'WORK_SYNC_NOTIFY_CMD': str(sh)})
    assert r.returncode == 0


def test_attention_details_each_on_own_line(e):
    """ATTENTION.md sections put each detail on its own line (recovery command is not joined to the explanation)."""
    e.put(e.work, 'a.txt', '1\ndirty\n3\n')
    e.advance('a.txt', '1\nprod\n3\n', 'prod edits a')
    e.run()
    text = e.attention()
    cmd = [ln for ln in text.splitlines() if 'stash apply' in ln]
    assert cmd
    for ln in cmd:
        assert 'Your uncommitted work' not in ln and 'FAIL' not in ln
    assert len([ln for ln in text.splitlines() if ln.strip()]) >= 4
