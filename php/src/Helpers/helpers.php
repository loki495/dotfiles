<?php

function dd() {

    $cli = php_sapi_name() == 'cli';

    $e = new \Exception();

    if (!$cli) echo '<pre>';

    $traces = $e->getTrace();

    foreach ($traces as $trace) {
        $file = $trace['file'];
        $line = $trace['line'];
        $class = $trace['class'] ?? '';
        $type = $trace['type'] ?? '';
        $function = $trace['function'];

        $line = str_pad($line, 4, ' ', STR_PAD_LEFT);
        $file = str_pad($file, 70, ' ', STR_PAD_RIGHT);

        $type = trim($type);
        $function = trim($function);

        echo_color($line . ' | ' . $file . ' | ', 'info');

        if ($type)
            echo_color($class . $type, 'info');

        echo_color($function, 'info');
		echo "\n";
    }

    foreach (func_get_args() as $k => $arg) {
        echo_color($k . ': ', 'info');
        print_r($arg);
    }

    echo "\n";

    exit;
}

function echo_color($str, $type = '') {
    switch ($type) {
        case 'error': //error
            echo "\033[31m$str\033[0m";
        break;
        case 'success': //success
            echo "\033[32m$str\033[0m";
        break;
        case 'warning': //warning
            echo "\033[33m$str\033[0m";
        break;
        case 'info': //info
            echo "\033[36m$str\033[0m";
        break;
        default:
		echo "\033[0m$str\033[0m";
        break;
    }
}

function fix_home_dir($fn) {
    return str_replace('~', $_SERVER['HOME'], $fn);}
