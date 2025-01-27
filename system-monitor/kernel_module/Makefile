# kernel_module/Makefile
obj-m += system_monitor.o

KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Add flags to handle declarations and warnings
EXTRA_CFLAGS += -Wno-declaration-after-statement

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean