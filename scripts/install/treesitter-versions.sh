# shellcheck shell=bash
# These version declarations are consumed by install_neovim.sh.
# shellcheck disable=SC2034
# Keep grammars aligned with the query snapshot; update together with capture tests.
TS_QUERY_REVISION=cf12346a3414fa1b06af75c79faebe7f76df080a
TS_BLADE_REVISION=b5291d1ba207a8ebb8383b2ecb8a8a6535210a50
declare -A TS_REVISIONS=(
    [bash]=0c46d792d54c536be5ff7eb18eb95c70fccdb232
    [html]=cbb91a0ff3621245e890d1c50cc811bffb77a26b
    [css]=6e327db434fec0ee90f006697782e43ec855adf5
    [yaml]=1805917414a9a8ba2473717fd69447277a175fae
    [javascript]=6fbef40512dcd9f0a61ce03a4c9ae7597b36ab5c
    [typescript]=75b3874edb2dc714fb1fd77a32013d0f8699989f
    [tsx]=75b3874edb2dc714fb1fd77a32013d0f8699989f
    [vue]=22bdfa6c9fc0f5ffa44c6e938ec46869ac8a99ff
    [json]=46aa487b3ade14b7b05ef92507fdaa3915a662a3
    [php]=576a56fa7f8b68c91524cdd211eb2ffc43e7bb11
    [php_only]=576a56fa7f8b68c91524cdd211eb2ffc43e7bb11
    [blade]="$TS_BLADE_REVISION"
    [rust]=e86119bdb4968b9799f6a014ca2401c178d54b5f
    [toml]=64b56832c2cffe41758f28e05c756a3a98d16f41
)

clone_treesitter_source() {
    local repository="$1" destination="$2" revision="$3"
    git clone --quiet --depth 1 "$repository" "$destination" &&
        git -C "$destination" fetch --quiet --depth 1 origin "$revision" &&
        git -C "$destination" checkout --quiet --detach FETCH_HEAD &&
        git -c url.https://github.com/.insteadOf=git@github.com: -C "$destination" \
            submodule update --init --recursive --depth 1
}
