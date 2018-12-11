#!/bin/bash
python bin/staging_collegeScraper.py
python bin/loadtimes.py --load 2019
python bin/loadtimes.py --stats 0