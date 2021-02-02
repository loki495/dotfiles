<?php

include 'env.php';

use DevCoder\DotEnv;

(new DotEnv('backup.conf'))->load();

$ssh_base_path = getenv('SSH_BASE_PATH');
$ssh_path = getenv('SSH_PATH');

$ssh_host = getenv('SSH_HOST');
$ssh_port = getenv('SSH_PORT');
$ssh_user = getenv('SSH_USER');
$ssh_key = getenv('SSH_KEY');

$rsync_folders = explode(',', trim(getenv('RSYNC_FOLDERS'),'" '));

$remote_path = "";
$local_path = "";

$ssh_custom = "";
if ($ssh_port) {
    $ssh_custom = "-p $ssh_port";
}

if ($ssh_key) {
    $ssh_custom .= " -i $ssh_key";
}

if ($ssh_custom) {
    $ssh_custom = "-e 'ssh $ssh_custom'";
}

if ($ssh_user) {
    $ssh_host = "$ssh_user@$ssh_host";
}

$descriptorspec = [
    0 => ["pipe", "r"],   // stdin is a pipe that the child will read from
    1 => ["pipe", "w"],   // stdout is a pipe that the child will write to
    2 => ["pipe", "w"]    // stderr is a pipe that the child will write to
];

foreach ($rsync_folders as $paths) {
    list($remote_path, $local_path) = explode('=',$paths);
    $remote_path = trim($remote_path,'[] \'');
    $remote_full_path = "$ssh_base_path/$ssh_path/$remote_path";

    $cmd = "rsync --progress -vazuhr $ssh_custom  $ssh_host:$remote_full_path $local_path";

    $process = proc_open($cmd, $descriptorspec, $pipes, realpath('./'), array());
    if (is_resource($process)) {
        while ($s = fgets($pipes[1])) {
            print $s;
            flush();
        }
    }
}

echo "DONE SYNCING FILES\n";
