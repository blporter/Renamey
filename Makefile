.PHONY: setup pull-models run undo build build-release test uninstall

TITLE_MODEL ?= "gemma4:e4b-mlx"
EPISODE_MODEL ?= "llama3.1:8b"

VERSION ?= v1.0.0

BUILD_OUTPUT := dist/renamey/renamey
RELEASE_ZIP := renamey-$(VERSION)-$(shell uname -s | tr '[:upper:]' '[:lower:]')-$(shell uname -m).zip

setup: .venv/.installed

.venv/.installed: requirements.txt
	python3 -m venv .venv
	.venv/bin/python3 -m pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	touch .venv/.installed
	@echo "venv ready. No activation needed - 'make run'/'make build'/'make test' use .venv directly."

pull-models:
	ollama pull $(TITLE_MODEL)
	ollama pull $(EPISODE_MODEL)
	ollama pull "nomic-embed-text"

run: setup
	.venv/bin/python3 src/main.py rename -c "$(CONTENT)" -f "$(FILEPATH)" -t $(TITLE_MODEL) -e $(EPISODE_MODEL) -v --resume

undo: setup
	.venv/bin/python3 src/main.py undo

build: $(BUILD_OUTPUT)

$(BUILD_OUTPUT): setup renamey.spec $(wildcard src/*.py) naming_reference.csv ignore_list.json
	.venv/bin/pyinstaller renamey.spec
	./install.sh

build-release: build
	cp install.sh dist/renamey/install.sh
	rm -f dist/$(RELEASE_ZIP)
	cd dist && zip -r $(RELEASE_ZIP) renamey
	@echo "Created dist/$(RELEASE_ZIP)"

uninstall:
	./install.sh uninstall

test: setup
	.venv/bin/pytest tests -vs