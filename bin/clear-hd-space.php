#!/usr/bin/php
<?php

declare(strict_types=1);

include __DIR__ . '/../php/vendor/autoload.php';

use loki495\Core\Config;
use loki495\Helpers\HDCleaner;

$config = new Config();
$config->addFile('~/.config/general/storage.ini');

$clean_dirs = $config->get('clean-dirs');

foreach ($clean_dirs as $dir) {
    match ($dir['type']) {
        'opencart1' => HDCleaner::clean_opencart1($dir),
        'sessions' => HDCleaner::clean_sessions($dir),
        'backup_database' => HDCleaner::clean_backup_database($dir),
        default => throw new \InvalidArgumentException("Unknown clean type: {$dir['type']}"),
    };
}

/*

Sample INI file

 [clean-dirs]
 0[path] = '~/example-site.com/public_html'
 0[type] = 'opencart1|sessions'
 0[days] = '(int)'  (for backup_database/sessions only)

Types:
- opencart1: deletes system/logs/error.txt
- sessions: deletes all files in subdirs older than 'days' days old
- backup_database: deletes all files in ~/backups/*\/database/*.sql.gz older than 'days' days old

 */
