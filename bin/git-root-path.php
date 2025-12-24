#!/bin/env php
<?php

$type = preg_replace('/^--/','',$argv[1]);
if (!$type) exit;

$pwd = trim(`pwd`, "\n \t\r");
$root_path = trim(shell_exec("git rev-parse --show-toplevel 2>/dev/null") ?? '', "\n \t\r");

if (!$root_path) {
    if ($type == 'path') echo $pwd;
    exit; 
}
$parts = explode('/',$root_path);
$root_dir = trim(array_pop($parts));
$project = trim(array_pop($parts));
$www = trim(array_pop($parts));

$ignore_roots = [
    'public_html',
];

//$output ](bright white)[](dimmed white) 
$path = preg_replace('|^'.$root_path.'|','',$pwd);

if ($www == 'www' && in_array($root_dir, $ignore_roots)) {
    if ($type == 'root') echo $project;
    if ($type == 'path') echo $path;
    exit;
}

if ($type == 'root') echo $root_dir;
if ($type == 'path') echo $path;
