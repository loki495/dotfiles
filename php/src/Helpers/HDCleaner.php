<?php

namespace loki495\Helpers;

class HDCleaner {

    static public function clean_opencart1($dir) {
        $path = fix_home_dir($dir['path']) . '/system/logs/error.txt';
        echo_color("Emptying $path\n", 'info');
        file_put_contents($path, '');
    }

    static public function clean_sessions($dir) {
        $path = fix_home_dir($dir['path']);
        $days = $dir['days'];
        echo_color("Deleting sessions in $path older than $days days\n", 'info');
        $cmd = "find $path -type f -mtime +$days -delete";

        exec($cmd, $output);
	print_r($output);
    }

    static public function clean_backup_database($dir) {
        $path = fix_home_dir($dir['path']);
        $days = $dir['days'];
        $ext = $dir['extension'] ?? '';
        echo_color("Deleting database *${ext} files in $path older than $days days\n", 'info');
	$cmd = "find $path -type f -mtime +$days";
	if ($ext)
	    $cmd .= " -name \"*.{$ext}\" ";
	$cmd .= " -delete";

        exec($cmd, $output);
	print_r($output);
    }

}
