<?php

namespace loki495\Core;

class Config {

    public $data = [];

    public function __construct() {
    }

    public function addFile($fn) {
        $fn = fix_home_dir($fn);
        $data = parse_ini_file($fn, 1);

        foreach ($data as $k => $v)
            $this->data[$k] = $v;
    }

    public function get($k, $base = '') {
        if ($base)
            return $this->data[$base][$k];

        return $this->data[$k];
    }
}
