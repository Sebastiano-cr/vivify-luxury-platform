.PHONY: all build install clean lazyledger lazyvivify lazysoc lazyhub lazybackup lazyzellij lazymon run-ledger deps

GO := go
# Use absolute path if go not in PATH (e.g. /home/vector/go1.25/bin/go)
BIN_DIR := $(HOME)/go/bin

all: build

build: lazyledger lazyvivify lazysoc lazyhub lazybackup lazyzellij lazymon

lazyledger:
	$(GO) build -o $(BIN_DIR)/lazyledger ./cmd/lazyledger

lazyvivify:
	$(GO) build -o $(BIN_DIR)/lazyvivify ./cmd/lazyvivify

lazysoc:
	$(GO) build -o $(BIN_DIR)/lazysoc ./cmd/lazysoc

lazybackup:
	$(GO) build -o $(BIN_DIR)/lazybackup ./cmd/lazybackup

lazyzellij:
	$(GO) build -o $(BIN_DIR)/lazyzellij ./cmd/lazyzellij

lazymon:
	$(GO) build -o $(BIN_DIR)/lazymon ./cmd/lazymon

lazyhub:
	$(GO) build -o $(BIN_DIR)/lazyhub ./cmd/lazyhub

install: build
	@echo "Installed: $(BIN_DIR)/lazyledger $(BIN_DIR)/lazyvivify $(BIN_DIR)/lazysoc $(BIN_DIR)/lazyhub $(BIN_DIR)/lazybackup $(BIN_DIR)/lazyzellij $(BIN_DIR)/lazymon"

run-ledger: lazyledger
	$(BIN_DIR)/lazyledger

deps:
	go mod tidy

clean:
	rm -f $(BIN_DIR)/lazyledger $(BIN_DIR)/lazyvivify $(BIN_DIR)/lazysoc $(BIN_DIR)/lazyhub $(BIN_DIR)/lazybackup $(BIN_DIR)/lazyzellij $(BIN_DIR)/lazymon
