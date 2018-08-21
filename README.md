# SE499
## How to use the extension
* Compile any c++ source file to object file with the name, for example, X
* Ensure that the python extension's name is X-gdb.py
* Verify that the python extension was properly loaded `info auto-load`. The
  command should indicate the utils-gdb.py extension was loaded as a script
* Run the program and call any of the commands as wish
* Autocomplete or help works for these new commands
## Run the utils example
* Run Makefile with -single flag if it's uniprocessor and with -multi if it's
  multiprocessor
    Ex: `make multi`
* Run `gdb ./utils`

Or simpler solution:
* Run gdb and then call command `source utils-gdb.py`

## List of commands
* clusters
* processors <cluster_name>
* task
* task <cluster_name>
* task <task_address>
* task <task_name>
* task <cluster_name> <task_id>
* poptask
