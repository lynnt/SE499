# SE499
## How to use the extension
* Compile utils-gdb.cpp
* Ensure utils-gdb.py is in the same folder as the object file of utils.cpp
* Run Makefile with -single flag if it's uniprocessor and with -multi if it's
  multiprocessor
    Ex: `make -multi`
* Run `gdb ./utils`
* Verify that the python extension was properly loaded `info auto-load`. The
  command should indicate the utils-gdb.py extension was loaded as a script
* Run the program and call any of the commands as wish
