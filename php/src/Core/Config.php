<?php

declare(strict_types=1);

namespace loki495\Core;

class Config {

    public array $data = [];

    public function addFile(string $fn): void {
        $fn = fix_home_dir($fn);
        $data = parse_ini_file($fn, true);

        foreach ($data as $k => $v)
            $this->data[$k] = $v;
    }

    public function get(string $k, string $base = ''): mixed {
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
