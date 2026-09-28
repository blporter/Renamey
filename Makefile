.PHONY: pull-models setup setup-dev test run-rename run-undo build build-release

TITLE_MODEL ?= "gemma4:e4b-mlx"
EPISODE_MODEL ?= "llama3.1:8b"

pull-models:
	ollama pull $(TITLE_MODEL)
	ollama pull $(EPISODE_MODEL)
	ollama pull "nomic-embed-text"

VERSION ?= v1.0.0

BUILD_OUTPUT := dist/renamey/renamey
RELEASE_ZIP := renamey-$(VERSION)-$(shell uname -s | tr '[:upper:]' '[:lower:]')-$(shell uname -m).zip

setup: .venv/.installed

.venv/.installed: pyproject.toml
	python3 -m venv .venv
	.venv/bin/python3 -m pip install --upgrade pip
	.venv/bin/pip install .
	touch .venv/.installed
	@echo "venv ready. No activation needed - 'make run'/'make build'/'make test' use .venv directly."

setup-dev: .venv/.installed-dev

.venv/.installed-dev: .venv/.installed
	.venv/bin/pip install --group dev
	touch .venv/.installed-dev

test: setup-dev
	.venv/bin/pytest tests -vs

run-rename: setup-dev
	.venv/bin/python3 src/main.py rename -c "$(CONTENT)" -f "$(FILEPATH)" -t $(TITLE_MODEL) -e $(EPISODE_MODEL) -v --resume

run-undo: setup-dev
	.venv/bin/python3 src/main.py undo

build: $(BUILD_OUTPUT)

$(BUILD_OUTPUT): setup renamey.spec $(wildcard src/*.py) src/assets/naming_reference.csv src/assets/ignore_list.json
	.venv/bin/pyinstaller renamey.spec

build-release: build
	rm -f dist/$(RELEASE_ZIP)
	cd dist && zip -r $(RELEASE_ZIP) renamey
	@echo "Created dist/$(RELEASE_ZIP)"