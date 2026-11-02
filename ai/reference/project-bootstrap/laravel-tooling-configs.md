# Laravel tooling configs and composer scripts

Reference for the `project-bootstrap` command, steps 8 and 9.

## Step 8: Scaffold config files (Laravel only, if missing)

### phpstan.neon

```neon
includes:
    - vendor/larastan/larastan/extension.neon

parameters:
    level: 6

    paths:
        - app
        - routes
        - database
        - tests

    excludePaths:
        - bootstrap
        - storage
        - vendor

    bootstrapFiles:
        - vendor/autoload.php

    ignoreErrors:
        - '#Call to an undefined method .*Pest.*#'

    scanFiles:
        - vendor/laravel/framework/src/Illuminate/Foundation/helpers.php
```

Default level is **6**. (stocker is at 4 — older project, not the new default.)

### pint.json

```json
{
    "preset": "laravel"
}
```

### rector.php

```php
<?php

declare(strict_types=1);

use Rector\Config\RectorConfig;
use Rector\Php74\Rector\Closure\ClosureToArrowFunctionRector;
use Rector\Set\ValueObject\LevelSetList;
use Rector\Set\ValueObject\SetList;

return static function (RectorConfig $rectorConfig): void {
    $rectorConfig->paths([
        __DIR__.'/app',
        __DIR__.'/database',
        __DIR__.'/routes',
        __DIR__.'/tests',
    ]);

    $rectorConfig->sets([
        LevelSetList::UP_TO_PHP_83,   // adjust to match the project's actual PHP version
        SetList::CODE_QUALITY,
        SetList::DEAD_CODE,
    ]);

    $rectorConfig->importNames();
    $rectorConfig->importShortClasses(false);

    $rectorConfig->skip([
        ClosureToArrowFunctionRector::class => true,
    ]);
};
```

## Step 9: Add composer scripts (Laravel only)

Add to `composer.json` `scripts` section. Replace `<CONTAINER>` with the actual name:

```json
"scripts": {
    "pest":         "docker exec <CONTAINER> ./vendor/bin/pest",
    "pint":         "docker exec <CONTAINER> ./vendor/bin/pint",
    "phpstan":      "docker exec <CONTAINER> ./vendor/bin/phpstan analyse",
    "rector":       "docker exec <CONTAINER> ./vendor/bin/rector process --dry-run",
    "rector:apply": "docker exec <CONTAINER> ./vendor/bin/rector process"
}
```

Merge into any existing `scripts` block — don't replace entries already there.
