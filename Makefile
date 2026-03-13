PREFIX ?= $(HOME)/.local
BINDIR  = $(PREFIX)/bin

.PHONY: all install fmt clean

all: install

install:
	mkdir -p $(BINDIR)
	install -m 755 nag.py $(BINDIR)/nag

fmt:
	black nag.py

clean:
	rm -rf .venv
