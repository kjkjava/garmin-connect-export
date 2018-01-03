SHELL := /bin/bash
COUNT := 4
.PHONY: help
help:
	@echo Usage:
	@echo make go COUNT=\<number of activities to download\>

.PHONY: go
go:
	./gcexport.py --username aaronferrucci --count $(COUNT) --format original --unzip

NUM_ACTIVITIES = $(shell find . -name activities.csv | wc -l)
.PHONY: count_activities_csv
count_activities_csv:
	@if [ $(NUM_ACTIVITIES) -ne 1 ] ; then \
	  echo "Too many activities.csv files found ($(NUM_ACTIVITIES))"; \
	  false; \
	fi

.PHONY: vimdiff
vimdiff: count_activities_csv
	vimdiff ../garmin_running/activities.csv $(shell find . -name activities.csv)
