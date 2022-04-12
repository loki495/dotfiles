<?php

include 'dotfiles/php/vendor/autoload.php';

$fn = __DIR__.'/cronlog';
$lines = file($fn);

//Apr 12 14:17:01 cd CRON[14368]: (root) CMD (   cd / && run-parts --report /etc/cron.hourly)

$user = $argv[1] ?? $_GET['user'];

$crons = [];

$cli = php_sapi_name() == 'cli';

foreach ($lines as $line) {

    $pattern = '/(... ..) (..:..:..) (.*?): \((.*?)\) CMD \((.*)\)/';
    preg_match($pattern, $line, $parts);
    if ($user && isset($parts[4]) && $parts[4] != $user) continue;

    if (isset($parts[4]) && !isset($parts[5])) {
        print_r($line);
    }

    $crons[$parts[5]][] = $parts[2];
}

if ($cli)
    print_r($crons);
else {

    $index = 0;
    $max_dates = 30;

    echo '<pre><table>';
    echo '<tr>';
    echo '<th></th>';
    echo '<th>CMD</th>';
    echo '<th>DATES</th>';
    echo '<th></th>';
    echo '</tr>';
    foreach ($crons as $cmd => $dates) {
        $index++;
        echo '<tr>';
        echo '<td>'.$index.'</td>';
        echo '<td><div style="max-width:700px">'.$cmd.'</div></td>';
        echo '<td>';
        $dates_printed = 0;
        foreach ($dates as $d) {
            echo $d.'<br>';
            $dates_printed++;
            if ($dates_printed > $max_dates) break;
        }
        echo '</td>';
        echo '</tr>';
    }
    echo '</table>';
}
