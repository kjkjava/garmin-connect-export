COUNT := 4
.PHONY: help
help:
	@echo Usage:
	@echo make go COUNT=\<number of activities to donwload\>

.PHONY: go
go:
	./gcexport.py --username aaronferrucci --count $(COUNT) --format original --unzip
