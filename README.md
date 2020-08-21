# map-heads
command line tool to create a pdf of figures for each model timestep and model layer of heads above G.S.

This tool is intended to run from the command line or as part of a batch file.

make sure to edit the inputs.txt file for the locations of files on your local machine
make sure python is added to your PATH environment variable
to check:
>>>python --version

or 

>>>echo %PATH%

and look for your python or conda environment in the list returned

to run:
>>>python C2VSimFG_MapHeads.py inputs.txt
