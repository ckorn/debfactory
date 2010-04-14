#!/bin/sh
set -e
cd /build/pre_build/$(lsb_release -sc)/games
dget -du http://archive.getdeb.net/getdeb/ubuntu/pool/games/2/2h4u/2h4u_1.3-1~getdeb1.dsc
