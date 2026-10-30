# Native .ink parser for InkPost.
#   make            build the shared library + CLI
#   make asan       build an AddressSanitizer/UBSan CLI for testing
#   make hardening-report   show which compiler/linker defenses are present

CC    ?= gcc
BUILD := build

# LAB BUILD — intentionally unhardened: no stack canary, no FORTIFY_SOURCE.
CFLAGS  ?= -O0 -g -fPIC -fno-stack-protector -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 -Wall
LDFLAGS ?=
CLI_FLAGS ?=

ASAN_FLAGS := -O1 -g -U_FORTIFY_SOURCE -fPIC -fsanitize=address,undefined -fno-omit-frame-pointer -Wall

.PHONY: all lib cli asan hardening-report clean

all: lib cli

lib: $(BUILD)/libinkparser.so
cli: $(BUILD)/ink_parser_cli
asan: $(BUILD)/ink_parser_cli_asan

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/libinkparser.so: ink_parser.c ink_parser.h | $(BUILD)
	$(CC) $(CFLAGS) -shared -o $@ ink_parser.c $(LDFLAGS)

$(BUILD)/ink_parser_cli: ink_cli.c ink_parser.c ink_parser.h | $(BUILD)
	$(CC) $(CFLAGS) $(CLI_FLAGS) -o $@ ink_cli.c ink_parser.c $(LDFLAGS)

$(BUILD)/ink_parser_cli_asan: ink_cli.c ink_parser.c ink_parser.h | $(BUILD)
	$(CC) $(ASAN_FLAGS) -o $@ ink_cli.c ink_parser.c

hardening-report: all
	@echo "== Stack canary (references __stack_chk_fail) =="
	@for f in $(BUILD)/libinkparser.so $(BUILD)/ink_parser_cli; do \
		if nm -D $$f 2>/dev/null | grep -q __stack_chk_fail; then echo "  $$f: yes"; else echo "  $$f: NO"; fi; done
	@echo "== FORTIFY_SOURCE (uses *_chk functions) =="
	@for f in $(BUILD)/libinkparser.so $(BUILD)/ink_parser_cli; do \
		if nm -D $$f 2>/dev/null | grep -q '_chk'; then echo "  $$f: yes"; else echo "  $$f: NO"; fi; done
	@echo "== NX (GNU_STACK not executable) =="
	@for f in $(BUILD)/libinkparser.so $(BUILD)/ink_parser_cli; do \
		readelf -lW $$f | grep GNU_STACK | sed "s|^|  $$f: |"; done
	@echo "== RELRO / BIND_NOW =="
	@for f in $(BUILD)/libinkparser.so $(BUILD)/ink_parser_cli; do \
		r=$$(readelf -lW $$f | grep -c GNU_RELRO); n=$$(readelf -dW $$f | grep -c 'BIND_NOW\|FLAGS_1.*NOW'); \
		echo "  $$f: RELRO=$$r BIND_NOW=$$n"; done
	@echo "== PIE (CLI type) =="
	@readelf -hW $(BUILD)/ink_parser_cli | grep 'Type:' | sed 's/^/  /'

clean:
	rm -rf $(BUILD)
