SHELL := /bin/bash
COUNT := 4
# DEBUG = --debug
DEBUG =
.PHONY: help
help:
	@echo Usage:
	@echo make go COUNT=\<number of activities to download\>

.PHONY: verify_overlap
# the new activity file should overlap the old one (otherwise vimdiff
# sometimes seems confused).
verify_overlap:
	@grep -q $(shell tail -1 $(shell find . -name activities.csv) | cut --delimiter=, --fields=1) ../garmin_running/activities.csv

.PHONY: go
go:
	./gcdownload.py --username aaronferrucci --count $(COUNT) $(DEBUG)

NUM_ACTIVITIES = $(shell find . -name activities.csv | wc -l)
.PHONY: count_activities_csv
count_activities_csv:
	@if [ $(NUM_ACTIVITIES) -ne 1 ] ; then \
	  echo "Too many activities.csv files found ($(NUM_ACTIVITIES))"; \
	  false; \
	fi

.PHONY: vimdiff
vimdiff: verify_overlap
	gvimdiff ../garmin_running/activities.csv $(shell find . -name activities.csv)
