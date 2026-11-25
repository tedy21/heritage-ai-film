# One command: `make film`. See README.md.
PY ?= python3
# Use .venv if it exists, else the system python (when it already has the deps).
PYBIN = $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo $(PY); fi)
export PYTHONPATH := $(CURDIR)

.PHONY: help setup validate smoke narration keyframes radio film shot costs offline clean-cache import-gpu kaggle-input test

help:
	@echo "make setup      create .venv and install requirements"
	@echo "make validate   check storyboard.json against schema/"
	@echo "make smoke      call each provider once (logs to runs.jsonl)"
	@echo "make radio      narration + temp music on black (Phase 1 radio cut)"
	@echo "make film       whole pipeline -> outputs/final/tana_16x9.mp4 + tana_9x16.mp4"
	@echo "make shot ID=s03  regenerate one shot's assets, then re-assemble"
	@echo "make offline    whole pipeline with placeholders (no keys needed)"
	@echo "make costs      per-stage latency / cost table from runs.jsonl"

setup:
	@$(PYBIN) -c "import jsonschema, requests" 2>/dev/null || \
	  ($(PY) -m venv .venv && .venv/bin/pip install -q -r requirements.txt) || \
	  $(PY) -m pip install --user -r requirements.txt
	@command -v ffmpeg >/dev/null || (echo "ffmpeg is required (apt install ffmpeg)" && exit 1)

validate: setup
	$(PYBIN) -m pipeline.validate

smoke: setup
	$(PYBIN) -m pipeline.smoke_test

narration: setup
	$(PYBIN) -m pipeline.narration

keyframes: setup
	$(PYBIN) -m pipeline.keyframes

radio: setup
	$(PYBIN) -m pipeline.narration
	$(PYBIN) -m pipeline.assemble --radio

film: setup
	$(PYBIN) -m pipeline.run

shot: setup
	@test -n "$(ID)" || (echo "usage: make shot ID=s03" && exit 1)
	SHOT=$(ID) $(PYBIN) -m pipeline.narration
	SHOT=$(ID) $(PYBIN) -m pipeline.keyframes
	$(PYBIN) -m pipeline.assemble

offline: setup
	OFFLINE=1 $(PYBIN) -m pipeline.run

costs: setup
	$(PYBIN) -m pipeline.costs

clean-cache:
	rm -rf outputs/segments outputs/final

import-gpu: setup
	$(PYBIN) -m pipeline.import_gpu $(wildcard outputs/clips/timings.json outputs/music/candidates/timings.json)

kaggle-input:
	zip -qr kaggle_in.zip storyboard.json outputs/keyframes && echo "upload kaggle_in.zip as a Kaggle dataset"

test:
	$(PY) -m unittest discover -s tests -v
