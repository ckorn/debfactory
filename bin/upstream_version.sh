#!/bin/sh
base=$(basename $(pwd))
version=$(echo $base | sed 's/.*-\(.\+\)/\1/')
dch -v ${version}-1~getdeb1 -D lucid New upstream version
