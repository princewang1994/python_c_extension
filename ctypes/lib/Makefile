all: dynamic

# run `make dynamic` to build libhello.so
dynamic: func.c func.h
	gcc -shared -fPIC -o libcos.so func.c

app: func.c main.c
	gcc func.c main.c -lm -o app

clean:
	# add '-' to ignore errors return by 'rm'
	-rm -f app *.o *.so
