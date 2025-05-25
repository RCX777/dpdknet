

.PHONY: all
all: build

.PHONY: build
build:
	uv build

.PHONY: clean
clean:
	rm -rf dist
