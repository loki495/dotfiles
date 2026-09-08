<?php

declare(strict_types=1);

/**
 * Tiny public trigger: CI calls this after a successful GHCR publish
 * (homie or insights) so Watchtower checks for and pulls whatever's new,
 * instead of waiting on its own 24h poll interval. Deliberately dumb - no
 * framework, no dependencies, just a token check and one internal call to
 * Watchtower's own HTTP API. Exposed publicly via the Cloudflare Tunnel
 * (cd.ac495.net), gated only by CD_TRIGGER_TOKEN - low blast radius even
 * if guessed: it can only ask Watchtower to check for image updates it's
 * already configured to track, nothing arbitrary. Run standalone via
 * `php -S 0.0.0.0:8086 -t . router.php`.
 */
$expectedToken = getenv('CD_TRIGGER_TOKEN');
$givenToken = $_GET['token'] ?? '';

if ($expectedToken === false || $expectedToken === '' || ! hash_equals($expectedToken, (string) $givenToken)) {
    http_response_code(403);
    echo 'Forbidden';
    exit;
}

$watchtowerUrl = getenv('WATCHTOWER_URL') ?: 'http://localhost:8082/v1/update';
$watchtowerToken = getenv('WATCHTOWER_TOKEN');

// Fire-and-forget: a real Watchtower update session (scan every container,
// check each image, recreate what changed) took ~13s in testing - longer
// than Cloudflare's edge origin-response timeout, so a caller that waits
// for Watchtower's own response sees a Cloudflare 502 even though the
// update ran fine. Background the call instead and acknowledge
// immediately; the caller only needs "the trigger was accepted", not the
// update's actual result.
$cmd = sprintf(
    'curl -s -m 60 -X POST -H %s %s > /dev/null 2>&1 &',
    escapeshellarg('Authorization: Bearer '.$watchtowerToken),
    escapeshellarg($watchtowerUrl)
);
exec($cmd);

http_response_code(202);
echo 'Update triggered';
