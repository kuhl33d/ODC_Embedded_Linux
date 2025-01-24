# kernel_module/Makefile
KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Explicitly set the compiler
CC := gcc-11

obj-m += system_monitor.o

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean