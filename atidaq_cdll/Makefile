# makefile for atidaq.so and/or atidaq.dll
#
# Linux: 	  merely call "make atidaq.so"
#
# MS Windows: Requires MinGW and MSYS. 
# 			  Call "make atidaq.dll" from MSYS command line
#

compile = gcc -c -fPIC 
link = gcc -shared -o

atidaq.so:  
	$(compile) atidaq/ftconfig.c
	$(compile) atidaq/ftrt.c
	$(compile) atidaq/dom.c
	$(compile) atidaq/expatls.c
	$(compile) atidaq/node.c
	$(compile) atidaq/stack.c
	$(compile) atidaq/xmlparse.c
	$(compile) atidaq/xmlrole.c
	$(compile) atidaq/xmltok.c
	$(link) atidaq.so ftconfig.o ftrt.o dom.o expatls.o node.o stack.o xmlparse.o xmlrole.o xmltok.o -lm

atidaq.dll: 
	$(compile) atidaq/ftconfig.c
	$(compile) atidaq/ftrt.c
	$(compile) atidaq/dom.c
	$(compile) atidaq/expatls.c
	$(compile) atidaq/node.c
	$(compile) atidaq/stack.c
	$(compile) atidaq/xmlparse.c
	$(compile) atidaq/xmlrole.c
	$(compile) atidaq/xmltok.c
	$(link)  atidaq.dll ftconfig.o ftrt.o dom.o expatls.o node.o stack.o xmlparse.o xmlrole.o xmltok.o -lm

clean:
	rm -f *.o
