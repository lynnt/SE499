lint:
	python3 -m pylint *.py
type:
	pyre -l .pyre_configuration --source-directory . check
