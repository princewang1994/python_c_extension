all: dynamic

# run `make dynamic` to build libhello.so
dynamic: func.c func.h
	gcc -shared -fPIC -o libcos.so -lm func.c

clean:
	# add '-' to ignore errors return by 'rm'
	-rm -f *.o *.so
