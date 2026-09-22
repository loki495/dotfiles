"""Offline installer regression tests; run only in a disposable container."""
import ctypes
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('DOTFILES_TEST_CONTAINER') != '1' or not Path('/.dockerenv').exists():
            self.fail('Run in a disposable Docker container with DOTFILES_TEST_CONTAINER=1')
        self.temp = tempfile.TemporaryDirectory(prefix='dotfiles-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home with spaces'
        self.home.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.download_log = self.root / 'downloads'
        self.env = dict(os.environ, HOME=str(self.home), PATH=f'{self.bin}:/usr/bin:/bin',
                        TEST_ROOT=str(self.root), DOWNLOAD_LOG=str(self.download_log),
                        NVIM_INSTALL_CHOICE='1', NVIM_LEGACY='0', SILENT_ECHOS='1')
        for key in ('SUDO_USER', 'BASH_ENV', 'ENV'):
            self.env.pop(key, None)
        self.archive('good', '#!/bin/sh\necho "NVIM v0.12.5"\n')
        self.archive('bad', '#!/bin/sh\necho "GLIBC_2.34 not found" >&2\nexit 1\n')
        self.stub('uname', '#!/bin/sh\n[ "$1" = -s ] && echo Linux || echo "${TEST_ARCH:-x86_64}"\n')
        self.stub('curl', '''#!/usr/bin/python3
import os, sys, shutil
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['DOWNLOAD_LOG'], 'a') as f:
    f.write(' '.join(args) + '\\n')
assert '--fail' in args
if os.environ.get('FAIL_DOWNLOAD') == '1':
    sys.exit(22)
if '--write-out' in args:
    print(args[-1].replace('/latest', '/tag/v0.12.5'), end='')
else:
    output = args[args.index('--output') + 1]
    if os.environ.get('EMPTY_DOWNLOAD') == '1':
        Path(output).touch()
    else:
        kind = 'bad' if (os.environ.get('BAD_SUPPORTED') == '1' and '/neovim/neovim/' in args[-1]) or os.environ.get('BAD_LEGACY') == '1' else 'good'
        shutil.copyfile(os.environ['TEST_ROOT'] + '/' + kind + '.tar.gz', output)
''')

    def stub(self, name, content):
        target = self.bin / name
        target.write_text(content)
        target.chmod(0o755)
        return target

    def archive(self, name, executable):
        with tarfile.open(self.root / f'{name}.tar.gz', 'w:gz') as archive:
            for filename, data, mode in [('bin/nvim', executable, 0o755),
                                         ('share/nvim/runtime/doc/help.txt', 'runtime', 0o644)]:
                info = tarfile.TarInfo('nvim-linux-x86_64/' + filename)
                encoded = data.encode()
                info.size, info.mode = len(encoded), mode
                archive.addfile(info, io.BytesIO(encoded))

    def run_script(self, script='install_neovim.sh', *args, success=True, **env):
        result = subprocess.run(['bash', str(REPO / script), *args], env=self.env | env,
                                input='', text=True, capture_output=True, timeout=15)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def shell(self, code, success=True):
        result = subprocess.run(['bash', '-ec', f'source "{REPO}/scripts/install/lib.sh"\n' + code],
                                env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def test_local_aliases_override_stale_paths_in_bash_and_fish(self):
        self.run_script('install_neovim.sh', '--user')
        for shell, suffix, setup in [
            ('bash', 'bash', 'shopt -s expand_aliases\nalias nvim=/missing/old\nalias vim=/missing/old'),
            ('fish', 'fish', 'alias nvim /missing/old; alias vim /missing/old'),
        ]:
            code = setup + '\nsource "$HOME/.local/share/dotfiles/neovim.' + suffix + '"\nnvim --version\nvim --version'
            result = subprocess.run([shell, '-c', code], env=self.env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count('NVIM v0.12.5'), 2)

    def test_alias_paths_and_arguments_are_shell_quoted(self):
        editor = self.home / "editor's $special; name"
        editor.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
        editor.chmod(0o755)
        self.env['EDITOR_TARGET'] = str(editor)
        self.shell('source "$DOTFILES_ROOT/scripts/install/neovim-aliases.sh"; install_neovim_aliases "$EDITOR_TARGET"')
        for shell, suffix in [('bash', 'bash'), ('fish', 'fish')]:
            code = ('shopt -s expand_aliases\n' if shell == 'bash' else '')
            code += 'source "$HOME/.local/share/dotfiles/neovim.' + suffix + '"\nnvim "two words" "literal;$value"'
            result = subprocess.run([shell, '-c', code], env=self.env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ['two words', 'literal;'])

    def test_failed_install_keeps_previous_alias_files(self):
        directory = self.home / '.local/share/dotfiles'
        directory.mkdir(parents=True)
        for suffix in ['bash', 'fish']:
            (directory / ('neovim.' + suffix)).write_text('previous aliases')
        self.run_script('install_neovim.sh', '--user', success=False, FAIL_DOWNLOAD='1')
        for suffix in ['bash', 'fish']:
            self.assertEqual((directory / ('neovim.' + suffix)).read_text(), 'previous aliases')

    def source_build_stubs(self):
        self.stub('make', '''#!/bin/sh
[ "${FAIL_BUILD:-0}" = 1 ] && exit 2
for arg in "$@"; do
    case "$arg" in CMAKE_INSTALL_PREFIX=*) printf '%s' "${arg#*=}" > "$TEST_ROOT/prefix";; esac
done
''')
        self.stub('cmake', '''#!/bin/sh
prefix=$(cat "$TEST_ROOT/prefix")
mkdir -p "$prefix/bin"
printf '%s\n' '#!/bin/sh' 'echo "NVIM source"' > "$prefix/bin/nvim"
chmod +x "$prefix/bin/nvim"
''')

    def test_source_install_preserves_data(self):
        self.source_build_stubs()
        data = self.home / '.local/share/nvim/keep'
        data.parent.mkdir(parents=True)
        data.write_text('keep')
        self.run_script('install_neovim.sh', '--user', '--source')
        self.assertIn('-source.', str((self.home / '.local/bin/nvim').resolve()))
        self.assertEqual(data.read_text(), 'keep')
        self.assertIn('/archive/refs/tags/', self.download_log.read_text())

    def test_failed_source_build_preserves_existing_install(self):
        self.source_build_stubs()
        binary = self.home / '.local/bin/nvim'
        binary.parent.mkdir(parents=True)
        binary.write_text('old binary')
        self.run_script('install_neovim.sh', '--user', '--source', '--force', success=False, FAIL_BUILD='1')
        self.assertEqual(binary.read_text(), 'old binary')
        self.assertEqual(list((self.home / '.local/opt/neovim').iterdir()), [])

    def test_source_and_legacy_are_mutually_exclusive(self):
        self.run_script('install_neovim.sh', '--user', '--source', '--legacy', success=False)
        self.assertFalse(self.download_log.exists())

    def test_section_supports_source_choice(self):
        self.source_build_stubs()
        self.run_script('install.sh', 'neovim', NVIM_SOURCE='1')
        self.assertIn('-source.', str((self.home / '.local/bin/nvim').resolve()))

    def test_default_install_excludes_systemd(self):
        checkout = self.root / 'checkout'
        (checkout / 'scripts/install').mkdir(parents=True)
        shutil.copy(REPO / 'install.sh', checkout)
        shutil.copy(REPO / 'scripts/install/lib.sh', checkout / 'scripts/install')
        shutil.copytree(REPO / 'bash/lib', checkout / 'bash/lib')
        (checkout / 'scripts/install/10-noop.sh').write_text('true\n')
        (checkout / 'scripts/install/40-systemd.sh').write_text('touch "$HOME/systemd-touched"\n')
        result = subprocess.run(['bash', str(checkout / 'install.sh')], env=self.env,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / 'systemd-touched').exists())

    def test_explicit_systemd_without_user_session_does_not_modify_configuration(self):
        self.stub('systemctl', '#!/bin/sh\nexit 1\n')
        self.run_script('install.sh', 'systemd', success=False)
        self.assertFalse((self.home / '.config/systemd').exists())

    def test_explicit_systemd_works_with_user_session(self):
        self.stub('systemctl', '#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/systemctl-calls"\n')
        self.run_script('install.sh', 'systemd')
        self.assertEqual((self.home / '.config/systemd').resolve(), REPO / '.config/systemd')
        calls = (self.home / 'systemctl-calls').read_text()
        self.assertIn('--user daemon-reload', calls)
        self.assertNotIn('enable', calls)

    def test_ai_configuration_never_calls_systemctl(self):
        self.stub('opencode', '#!/bin/sh\nexit 0\n')
        self.stub('systemctl', '#!/bin/sh\ntouch "$HOME/systemd-touched"\nexit 1\n')
        self.run_script('install.sh', 'ai-tools')
        self.assertTrue((self.home / '.config/opencode/agent').is_symlink())
        self.assertFalse((self.home / 'systemd-touched').exists())

    def test_existing_healthy_editor_is_not_shadowed(self):
        self.stub('nvim', '#!/bin/sh\necho "NVIM existing"\n')
        result = self.run_script('install_neovim.sh', '--user')
        self.assertIn('already works', result.stdout)
        self.assertFalse(self.download_log.exists())

    def test_broken_existing_editor_is_replaced_and_data_preserved(self):
        self.stub('nvim', '#!/bin/sh\necho "GLIBC_2.34 not found" >&2\nexit 1\n')
        data = self.home / '.local/share/nvim/lazy/plugin'
        data.mkdir(parents=True)
        (data / 'keep').write_text('plugin state')
        aliases = self.home / '.bashrc.local'
        aliases.write_text('alias vim=nvim\n')
        self.run_script('install_neovim.sh', '--user')
        self.assertTrue((self.home / '.local/bin/nvim').is_symlink())
        self.assertEqual((data / 'keep').read_text(), 'plugin state')
        self.assertEqual(aliases.read_text(), 'alias vim=nvim\n')
        self.assertIn('/.local/opt/neovim/', str((self.home / '.local/bin/nvim').resolve()))

    def test_incompatible_download_does_not_replace_existing_editor(self):
        self.env['BAD_SUPPORTED'] = '1'
        binary = self.home / '.local/bin/nvim'
        binary.parent.mkdir(parents=True)
        binary.write_text('old binary')
        result = self.run_script('install_neovim.sh', '--user', '--force', success=False)
        self.assertIn('--legacy', result.stderr)
        self.assertEqual(binary.read_text(), 'old binary')
        self.assertNotIn('neovim-releases', self.download_log.read_text())

    def test_explicit_legacy_build_works(self):
        self.env['BAD_SUPPORTED'] = '1'
        self.run_script('install_neovim.sh', '--user', '--legacy')
        self.assertIn('neovim/neovim-releases', self.download_log.read_text())
        self.assertTrue((self.home / '.local/bin/nvim').exists())

    def test_interactive_glibc_fallback_requires_and_honors_confirmation(self):
        master, slave = os.openpty()
        try:
            process = subprocess.Popen(['bash', str(REPO / 'install_neovim.sh'), '--user'],
                                       env=self.env | {'BAD_SUPPORTED': '1'}, stdin=slave,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            os.write(master, b'y\n')
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        finally:
            os.close(slave)
            os.close(master)
        self.assertIn('neovim/neovim-releases', self.download_log.read_text())
        self.assertTrue((self.home / '.local/bin/nvim').exists())

    def test_incompatible_legacy_binary_is_not_installed(self):
        self.run_script('install_neovim.sh', '--user', '--legacy', success=False, BAD_LEGACY='1')
        self.assertFalse((self.home / '.local/bin/nvim').exists())

    def test_failed_download_preserves_editor(self):
        binary = self.home / '.local/bin/nvim'
        binary.parent.mkdir(parents=True)
        binary.write_text('old binary')
        self.run_script('install_neovim.sh', '--user', '--force', success=False, FAIL_DOWNLOAD='1')
        self.assertEqual(binary.read_text(), 'old binary')

    def test_bad_archive_is_not_installed(self):
        self.run_script('install_neovim.sh', '--user', success=False, EMPTY_DOWNLOAD='1')
        self.assertFalse((self.home / '.local/bin/nvim').exists())

    def test_force_install_preserves_previous_version(self):
        self.run_script('install_neovim.sh', '--user')
        binary = self.home / '.local/bin/nvim'
        previous = binary.resolve()
        self.run_script('install_neovim.sh', '--user', '--force')
        self.assertNotEqual(binary.resolve(), previous)
        self.assertTrue(previous.exists())
        self.assertEqual(binary.with_name('nvim.old').resolve(), previous)

    def test_missing_config_directory_is_created_for_neovim_only(self):
        self.stub('nvim', '#!/bin/sh\necho "NVIM existing"\n')
        self.run_script('install.sh', 'neovim')
        self.assertEqual((self.home / '.config/nvim').resolve(), REPO / 'nvim')

    def test_selected_server_sections_run_without_desktop_dependencies(self):
        (self.home / 'dotfiles').symlink_to(REPO)
        self.stub('nvim', '#!/bin/sh\necho "NVIM existing"\n')
        self.run_script('install.sh', 'bash', 'neovim', 'git')
        self.assertEqual((self.home / '.gitconfig').resolve(), REPO / 'git/.gitconfig')
        self.assertEqual((self.home / '.config/nvim').resolve(), REPO / 'nvim')

    def test_neovim_choice_errors_do_not_report_success(self):
        for choice in ('9', ''):
            result = self.run_script('install.sh', 'neovim', success=False, NVIM_INSTALL_CHOICE=choice)
            self.assertNotIn('Dotfiles setup complete', result.stdout)
            self.assertFalse((self.home / '.config/nvim').exists())

    def test_unknown_options_and_architectures_fail_before_download(self):
        for args in [('--user', '--typo'), ('--user', '--global'), ()]:
            self.run_script('install_neovim.sh', *args, success=False)
        self.run_script('install_neovim.sh', '--user', success=False, TEST_ARCH='mips')
        self.assertFalse(self.download_log.exists())

    def test_section_names_are_literal(self):
        self.run_script('install.sh', '.*', success=False)
        self.assertFalse((self.home / '.bashrc').exists())

    def test_backups_are_unique_and_links_are_idempotent(self):
        target = self.home / '.config/nvim'
        target.mkdir(parents=True)
        (target / 'keep').write_text('first')
        target.with_name('nvim.old').mkdir()
        target.with_name('nvim.old').joinpath('keep').write_text('earlier')
        self.shell('backup_and_link "$HOME/.config/nvim" "$DOTFILES_ROOT/nvim"')
        self.shell('backup_and_link "$HOME/.config/nvim" "$DOTFILES_ROOT/nvim"')
        self.assertEqual((target.parent / 'nvim.old/keep').read_text(), 'earlier')
        self.assertEqual((target.parent / 'nvim.old.1/keep').read_text(), 'first')
        self.assertFalse((target.parent / 'nvim.old.2').exists())

    def test_custom_dangling_link_is_preserved(self):
        (self.home / 'target').symlink_to('/missing/custom-target')
        self.shell('backup_and_link "$HOME/target" "$DOTFILES_ROOT/nvim"')
        self.assertEqual(os.readlink(self.home / 'target.old'), '/missing/custom-target')

    def test_failed_link_restores_files_directories_and_dangling_links(self):
        self.stub('ln', '#!/bin/sh\necho "simulated link failure" >&2\nexit 1\n')
        for kind in ['file', 'directory', 'symlink']:
            target = self.home / kind
            if kind == 'directory':
                target.mkdir()
                (target / 'keep').write_text('keep')
            elif kind == 'symlink':
                target.symlink_to('/missing/custom')
            else:
                target.write_text('keep')
            self.shell('backup_and_link "$HOME/' + kind + '" "$DOTFILES_ROOT/nvim"', success=False)
            if kind == 'symlink':
                self.assertEqual(os.readlink(target), '/missing/custom')
            else:
                self.assertEqual((target / 'keep' if kind == 'directory' else target).read_text(), 'keep')
            self.assertFalse(target.with_name(kind + '.old').exists())

    def test_failed_neovim_link_restores_editor_and_removes_candidate(self):
        binary = self.home / '.local/bin/nvim'
        binary.parent.mkdir(parents=True)
        binary.write_text('previous editor')
        self.stub('ln', '#!/bin/sh\nexit 1\n')
        result = self.run_script('install_neovim.sh', '--user', '--force', success=False, SILENT_ECHOS='0')
        self.assertIn('Restored previous', result.stderr)
        self.assertEqual(binary.read_text(), 'previous editor')
        self.assertEqual(list((self.home / '.local/opt/neovim').iterdir()), [])

    def test_managed_files_are_idempotent_and_preserve_changed_content(self):
        source, target = self.home / 'source', self.home / 'parser.so'
        source.write_text('first')
        self.shell('install_managed_file "$HOME/source" "$HOME/parser.so"')
        inode = target.stat().st_ino
        self.shell('install_managed_file "$HOME/source" "$HOME/parser.so"')
        self.assertEqual(target.stat().st_ino, inode)
        self.assertFalse((self.home / '.dotfiles-backups').exists())
        for text in ['second', 'third']:
            source.write_text(text)
            self.shell('install_managed_file "$HOME/source" "$HOME/parser.so"')
        self.assertEqual(target.read_text(), 'third')
        self.assertEqual((self.home / '.dotfiles-backups/parser.so.old').read_text(), 'first')
        self.assertEqual((self.home / '.dotfiles-backups/parser.so.old.1').read_text(), 'second')

    def test_failed_managed_file_publication_preserves_previous_file(self):
        (self.home / 'source').write_text('new')
        (self.home / 'target').write_text('old')
        self.stub('mv', '#!/bin/sh\necho "simulated rename failure" >&2\nexit 1\n')
        self.shell('install_managed_file "$HOME/source" "$HOME/target"', success=False)
        self.assertEqual((self.home / 'target').read_text(), 'old')
        self.assertEqual(list(self.home.glob('.install.*')), [])

    def test_failed_managed_file_backup_stops_before_replacement(self):
        (self.home / 'source').write_text('new')
        (self.home / 'target').write_text('old')
        self.stub('cp', '#!/bin/sh\n[ "$1" = -a ] && exit 1\nexec /bin/cp "$@"\n')
        self.shell('if install_managed_file "$HOME/source" "$HOME/target"; then exit 1; fi')
        self.assertEqual((self.home / 'target').read_text(), 'old')
        self.assertEqual(list(self.home.glob('.install.*')), [])

    def test_failed_phar_download_never_truncates_existing_tool(self):
        (self.home / 'tool').write_text('working tool')
        self.env['FAIL_DOWNLOAD'] = '1'
        self.shell('download_executable https://example.invalid/tool "$HOME/tool"', success=False)
        self.assertEqual((self.home / 'tool').read_text(), 'working tool')
        self.assertEqual(list(self.home.glob('.download.*')), [])

    def test_neovim_wrapper_passes_legacy_choice(self):
        self.run_script('install.sh', 'neovim', NVIM_LEGACY='1', BAD_SUPPORTED='1')
        self.assertIn('neovim/neovim-releases', self.download_log.read_text())

    def test_arm64_asset_is_selected(self):
        for name in ('good', 'bad'):
            with tarfile.open(self.root / f'{name}.tar.gz', 'r:gz') as archive:
                members = [(item, archive.extractfile(item).read()) for item in archive]
            with tarfile.open(self.root / f'{name}.tar.gz', 'w:gz') as archive:
                for item, data in members:
                    item.name = item.name.replace('x86_64', 'arm64')
                    archive.addfile(item, io.BytesIO(data))
        self.run_script('install_neovim.sh', '--user', TEST_ARCH='aarch64')
        self.assertIn('nvim-linux-arm64.tar.gz', self.download_log.read_text())

    def test_parser_clone_failure_is_not_success_and_cleans_up(self):
        temporary = self.root / 'scratch'
        temporary.mkdir()
        self.stub('tree-sitter', '#!/bin/sh\necho "tree-sitter 0.26.1"\n')
        self.stub('npm', '#!/bin/sh\nexit 0\n')
        self.stub('git', '#!/bin/sh\nexit 1\n')
        result = self.run_script('install_neovim.sh', '--parsers', 'php', success=False, TMPDIR=str(temporary))
        self.assertIn('1 parser installation(s) failed', result.stderr)
        self.assertEqual(list(temporary.iterdir()), [])

    def test_unknown_parser_is_not_success(self):
        self.stub('tree-sitter', '#!/bin/sh\necho "tree-sitter 0.26.1"\n')
        self.stub('npm', '#!/bin/sh\nexit 0\n')
        self.run_script('install_neovim.sh', '--parsers', 'not_a_language', success=False)

    def test_cpp_external_scanner_is_linked_into_parser(self):
        self.stub('tree-sitter', '#!/bin/sh\ncase "$1" in --version) echo "tree-sitter 0.26.1";; generate) exit 0;; *) exit 1;; esac\n')
        self.stub('npm', '#!/bin/sh\nexit 0\n')
        self.stub('git', '''#!/bin/bash
[ \"$1\" = clone ] || exit 0
for destination in "$@"; do :; done
mkdir -p "$destination/src"
printf '%s\n' 'extern int scanner(void); int tree_sitter_blade(void) { return scanner(); }' > "$destination/src/parser.c"
printf '%s\n' 'extern "C" int scanner(void) { return 42; }' > "$destination/src/scanner.cc"
''')
        self.run_script('install_neovim.sh', '--parsers', 'blade')
        parser = ctypes.CDLL(str(self.home / '.local/share/nvim/site/parser/blade.so'))
        self.assertEqual(parser.tree_sitter_blade(), 42)

    def test_query_install_includes_recursive_inheritance(self):
        self.stub('git', """#!/bin/bash
[ "$1" = clone ] || exit 0
for destination in "$@"; do :; done
mkdir -p "$destination/queries/"{javascript,ecma,jsx,html_tags}
printf '%s\\n' '; inherits: ecma,jsx' > "$destination/queries/javascript/highlights.scm"
printf '%s\\n' '(identifier) @variable' > "$destination/queries/ecma/highlights.scm"
printf '%s\\n' '; inherits: html_tags' > "$destination/queries/jsx/highlights.scm"
printf '%s\\n' '(tag_name) @tag' > "$destination/queries/html_tags/highlights.scm"
""")
        self.run_script('install_neovim.sh', '--queries', 'javascript')
        for language in ['javascript', 'ecma', 'jsx', 'html_tags']:
            self.assertTrue((self.home / '.local/share/nvim/site/queries' / language / 'highlights.scm').is_file())

    def test_missing_inherited_queries_fail_explicitly(self):
        self.stub('git', """#!/bin/bash
[ "$1" = clone ] || exit 0
for destination in "$@"; do :; done
mkdir -p "$destination/queries/php"
printf '%s\\n' '; inherits: php_only' > "$destination/queries/php/highlights.scm"
""")
        result = self.run_script('install_neovim.sh', '--queries', 'php', success=False)
        self.assertIn('Missing inherited query language: php_only', result.stderr)
        self.assertFalse((self.home / '.local/share/nvim/site/queries/php/highlights.scm').exists())

    def test_query_clone_failure_cleans_up(self):
        temporary = self.root / 'scratch'
        temporary.mkdir()
        self.stub('git', '#!/bin/sh\nexit 1\n')
        self.run_script('install_neovim.sh', '--queries', 'php', success=False, TMPDIR=str(temporary))
        self.assertEqual(list(temporary.iterdir()), [])

    def test_failed_node_runtime_stops_before_installing_provider(self):
        self.stub('node', '#!/bin/sh\necho "GLIBC unavailable" >&2\nexit 1\n')
        self.stub('npm', '#!/bin/sh\ntouch "$HOME/npm-called"\n')
        result = self.run_script('install_neovim.sh', '--node-provider', success=False)
        self.assertIn('GLIBC unavailable', result.stderr)
        self.assertFalse((self.home / 'npm-called').exists())

    def test_failed_provider_download_does_not_report_success(self):
        self.stub('node', '#!/bin/sh\nexit 0\n')
        self.stub('npm', '#!/bin/sh\n[ "$1" = --version ] && exit 0\necho "registry unavailable" >&2\nexit 1\n')
        result = self.run_script('install_neovim.sh', '--node-provider', success=False)
        self.assertIn('registry unavailable', result.stderr)
        self.assertNotIn('Node provider installed', result.stdout)

    def test_empty_phar_download_is_rejected(self):
        self.env['EMPTY_DOWNLOAD'] = '1'
        self.shell('download_executable https://example.invalid/tool "$HOME/tool"', success=False)
        self.assertFalse((self.home / 'tool').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
