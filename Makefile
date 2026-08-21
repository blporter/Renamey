run:
	.venv/bin/python3 src/main.py -f "$(FILEPATH)"

build:
	pyinstaller --onefile --paths=src --hidden-import=generator --add-data="naming_reference.csv:." --name="renamey" src/main.py
