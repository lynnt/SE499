flag=-g -O0
input=utils
output=utils
single:
	u++ ${flag} ${input}.cpp -o ${output}
multi:
	u++ ${flag} -multi ${input}.cpp -o ${output}
lint:
	python3 -m pylint ${input}-gdb.py
type:
	pyre -l .pyre_configuration --source-directory . check
