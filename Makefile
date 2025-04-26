CC := gcc

sim: CFLAGS += -O2 -D LINUX
sim: LDLIBS += -lSDL2
sim:
	$(CC) $(CFLAGS) simulator.c -o sim $(LDLIBS)

.PHONY: clean re

clean:
	$(RM) sim

.NOTPARALLEL: re
re: clean sim
