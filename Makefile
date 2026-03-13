PREFIX ?= $(HOME)/.local
BINDIR = $(PREFIX)/bin
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

.PHONY: install fmt venv

venv: $(VENV)/bin/activate

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

install: venv
	install -m 755 nag.py $(BINDIR)/nag

fmt: venv
	$(VENV)/bin/black nag.py
