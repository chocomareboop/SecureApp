/*
 * ink_cli.c — standalone command-line front end for the .ink parser.
 * Used for safe terminal demos of VULN-1 and for ASAN runs.
 *
 *   usage: ink_parser_cli <file.ink> [uploader_id]
 */
#include "ink_parser.h"

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    FILE *f;
    long size;
    uint8_t *buf;
    ink_meta_t meta;
    int32_t uploader_id = 3;
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <file.ink> [uploader_id]\n", argv[0]);
        return 2;
    }
    if (argc >= 3)
        uploader_id = (int32_t)strtol(argv[2], NULL, 10);

    f = fopen(argv[1], "rb");
    if (f == NULL) {
        perror("fopen");
        return 2;
    }
    if (fseek(f, 0, SEEK_END) != 0 || (size = ftell(f)) < 0 || fseek(f, 0, SEEK_SET) != 0) {
        fclose(f);
        fprintf(stderr, "cannot size file\n");
        return 2;
    }
    buf = malloc((size_t)size + 1);
    if (buf == NULL) {
        fclose(f);
        return 2;
    }
    if (fread(buf, 1, (size_t)size, f) != (size_t)size) {
        fclose(f);
        free(buf);
        fprintf(stderr, "short read\n");
        return 2;
    }
    fclose(f);

    rc = ink_parse(buf, (size_t)size, uploader_id, &meta);
    if (rc < 0) {
        printf("REJECTED: parser error %d\n", rc);
        free(buf);
        return 1;
    }

    printf("uploader_id  : %d\n", (int)uploader_id);
    printf("title        : %.64s\n", meta.title);
    printf("tags         : %.127s\n", meta.tags);
    printf("is_published : %d\n", (int)meta.is_published);
    printf("author_id    : %d\n", (int)meta.author_id);
    printf("body offset  : %d\n", rc);
    if (meta.author_id != uploader_id || meta.is_published != 0)
        printf("!! INTEGRITY VIOLATION: parser output no longer matches the uploader / draft state\n");

    free(buf);
    return 0;
}
