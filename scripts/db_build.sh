#!/bin/bash
createdb swimdb
psql -d swimdb -f swimdb_build.sql