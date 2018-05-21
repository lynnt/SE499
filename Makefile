lint:
	python3 -m pylint *.py
type:
	pyre --source-directory . check
