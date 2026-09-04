.PHONY: install-models run undo build test

TITLE_MODEL ?= "gemma4:e4b-mlx"
EPISODE_MODEL ?= "llama3.1:8b"

install-models:
	ollama pull $(TITLE_MODEL)
	ollama pull $(EPISODE_MODEL)
	ollama pull "nomic-embed-text"

run:
	.venv/bin/python3 src/main.py rename -c "$(CONTENT)" -f "$(FILEPATH)" -t $(TITLE_MODEL) -e $(EPISODE_MODEL) --dry-run -v

undo:
	.venv/bin/python3 src/main.py undo

build:
	pyinstaller --onefile --paths=src --add-data="naming_reference.csv:." --add-data="ignore_list.json:." --name="renamey" src/main.py

test:
	pytest tests -vs