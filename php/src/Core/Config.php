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
        if ($base) {
            if (!isset($this->data[$base][$k]))
                throw new \RuntimeException("Config key '{$base}.{$k}' is not set");

            return $this->data[$base][$k];
        }

        if (!isset($this->data[$k]))
            throw new \RuntimeException("Config key '{$k}' is not set");

        return $this->data[$k];
    }
}
