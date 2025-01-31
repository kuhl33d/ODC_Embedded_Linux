obj-m += system_monitor.o

KDIR := /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

# Add flags to handle declarations and warnings
EXTRA_CFLAGS += -Wno-declaration-after-statement -DDEBUG

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install:
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install
	depmod -a

uninstall:
	rm -f /lib/modules/$(shell uname -r)/extra/system_monitor.ko
	depmod -a