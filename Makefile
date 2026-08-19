run:
	.venv/bin/python3 main.py -f "$(FILEPATH)"

build:
	pyinstaller --onefile --paths=. --hidden-import=generator --add-data="naming_reference.csv:." main.py
