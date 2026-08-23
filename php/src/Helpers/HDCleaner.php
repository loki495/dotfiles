<?php

declare(strict_types=1);

namespace loki495\Helpers;

class HDCleaner {

    static public function clean_opencart1(array $dir): void {
        $path = fix_home_dir($dir['path']) . '/system/logs/error.txt';
        echo_color("Emptying $path\n", 'info');
        file_put_contents($path, '');
    }

    static public function clean_sessions(array $dir): void {
        $path = fix_home_dir($dir['path']);
        $days = $dir['days'];
        echo_color("Deleting sessions in $path older than $days days\n", 'info');
        $cmd = 'find ' . escapeshellarg($path) . ' -type f -mtime ' . escapeshellarg("+$days") . ' -delete';

        exec($cmd, $output);
	print_r($output);
    }

    static public function clean_backup_database(array $dir): void {
        $path = fix_home_dir($dir['path']);
        $days = $dir['days'];
        $ext = $dir['extension'] ?? '';
        echo_color("Deleting database *${ext} files in $path older than $days days\n", 'info');
	$cmd = 'find ' . escapeshellarg($path) . ' -type f -mtime ' . escapeshellarg("+$days");
	if ($ext)
	    $cmd .= ' -name ' . escapeshellarg("*.{$ext}");
	$cmd .= ' -delete';

        exec($cmd, $output);
	print_r($output);
    }

}
