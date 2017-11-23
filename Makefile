COUNT := 4
.PHONY: help
help:
	@echo Usage:
	@echo make go COUNT=\<number of activities to download\>

.PHONY: go
go:
	./gcexport.py --username aaronferrucci --count $(COUNT) --format original --unzip
