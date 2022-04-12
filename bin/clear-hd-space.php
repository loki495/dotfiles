#!/usr/bin/php
<?php

include $_SERVER['HOME'] . '/dotfiles/php/vendor/autoload.php';

use loki495\Core\Config;
use loki495\Helpers\HDCleaner;

$config = new Config();
$config->addFile('~/.config/general/storage.ini');

$clean_dirs = $config->get('clean-dirs');

foreach ($clean_dirs as $dir) {

    $cleaner = 'clean_' . $dir['type'];
    HDCleaner::$cleaner($dir);
}

/*

Sample INI file

 [clean-dirs]
 0[path] = '~/retrogamingstores.com/public_html'
 0[type] = 'opencart1|sessions'
 0[days] = '(int)'  (for sessions only)

Types:
- opencart1: deletes system/logs/error.txt
- sessions: deletes all files in subdirs older than 'days' days old

 */
