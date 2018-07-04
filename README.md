# SE499
## How to use the extension
* Compile utils-gdb.cpp
* Ensure utils-gdb.py is in the same folder as the object file of utils.cpp
* Run Makefile with -single flag if it's uniprocessor and with -multi if it's
  multiprocessor
    Ex: `make multi`
* Run `gdb ./utils`
* Verify that the python extension was properly loaded `info auto-load`. The
  command should indicate the utils-gdb.py extension was loaded as a script
* Run the program and call any of the commands as wish

Or simplier solution:
* Run gdb and then call command `source utils-gdb.py`

## List of commands
* clusters
* cluster_procs <cluster_address>
* cluster_tasks <cluster_address>
* tasks
* pushtask <address>
* pushtask_id <id> [cluster_id]
* poptask
