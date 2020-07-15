# makefile for atidaq.so and/or atidaq.dll
#
# Linux: 	  merely call "make atidaq.so"
#
# MS Windows: Requires MinGW and MSYS.
# 			  Call "make atidaq.dll" from MSYS command line
#
# See COPYING file distributed along with the pyForceDAQ copyright and license terms.

gcc = gcc
#gcc = x86_64-w64-mingw32-gcc  # using linux build 64bit

compile = $(gcc) -c -fPIC
link = $(gcc) -shared -o

compile_all:
	$(compile) atidaq/ftconfig.c
	$(compile) atidaq/ftrt.c
	$(compile) atidaq/dom.c
	$(compile) atidaq/expatls.c
	$(compile) atidaq/node.c
	$(compile) atidaq/stack.c
	$(compile) atidaq/xmlparse.c
	$(compile) atidaq/xmlrole.c
	$(compile) atidaq/xmltok.c

atidaq.so: compile_all
	$(link) atidaq.so ftconfig.o ftrt.o dom.o expatls.o node.o stack.o xmlparse.o xmlrole.o xmltok.o -lm

atidaq.dll: compile_all
	$(link)  atidaq.dll ftconfig.o ftrt.o dom.o expatls.o node.o stack.o xmlparse.o xmlrole.o xmltok.o -lm


clean:
	rm -f *.o
