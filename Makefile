.PHONY: pull-models run undo build build-release test install uninstall

TITLE_MODEL ?= "gemma4:e4b-mlx"
EPISODE_MODEL ?= "llama3.1:8b"

VERSION ?= v1.0.0

BUILD_OUTPUT := dist/renamey/renamey
RELEASE_ZIP := renamey-$(VERSION)-$(shell uname -s | tr '[:upper:]' '[:lower:]')-$(shell uname -m).zip

pull-models:
	ollama pull $(TITLE_MODEL)
	ollama pull $(EPISODE_MODEL)
	ollama pull "nomic-embed-text"

run:
	.venv/bin/python3 src/main.py rename -c "$(CONTENT)" -f "$(FILEPATH)" -t $(TITLE_MODEL) -e $(EPISODE_MODEL) -v --resume

undo:
	.venv/bin/python3 src/main.py undo

build: $(BUILD_OUTPUT)

$(BUILD_OUTPUT): renamey.spec $(wildcard src/*.py) naming_reference.csv ignore_list.json
	.venv/bin/pyinstaller renamey.spec

build-release: build
	cp install.sh dist/renamey/install.sh
	rm -f dist/$(RELEASE_ZIP)
	cd dist && zip -r $(RELEASE_ZIP) renamey
	@echo "Created dist/$(RELEASE_ZIP)"

install: $(BUILD_OUTPUT)
	./install.sh

uninstall:
	./install.sh uninstall

test:
	pytest tests -vs