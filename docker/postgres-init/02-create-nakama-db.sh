#!/bin/sh
set -e
psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE nakama;"
