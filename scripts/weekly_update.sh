#!/bin/bash
python scrapers/collegeScraper.py
python bin/loadTimes.py -l 2019
python bin/loadTimes.py -s 2019