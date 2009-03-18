#!/bin/sh
find /var/www/build_ready -name "*.dsc" | sed "s/\/var\/www\/build_ready\///g" > /var/www/build_ready/ready.lst