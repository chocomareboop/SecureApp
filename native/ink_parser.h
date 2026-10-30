/*
 * ink_parser.h — native parser for InkPost ".ink" import files.
 *
 * .ink format (all integers little-endian):
 *
 *   offset 0   "INK1"                 4-byte magic
 *   offset 4   u16 title_len
 *              title bytes            (title_len bytes)
 *              u16 tags_len
 *              tags bytes             (tags_len bytes, comma separated)
 *              body bytes             (rest of file, UTF-8 Markdown)
 */
#ifndef INK_PARSER_H
#define INK_PARSER_H

#include <stddef.h>
#include <stdint.h>

#define INK_MAGIC     "INK1"
#define INK_TITLE_MAX 64
#define INK_TAGS_MAX  128

/* Field order matters: is_published and author_id sit directly after title. */
typedef struct {
    char    title[INK_TITLE_MAX];
    int32_t is_published;   /* imported posts must start as drafts (0)  */
    int32_t author_id;      /* stamped with the uploader's user id       */
    char    tags[INK_TAGS_MAX];
} ink_meta_t;

enum {
    INK_ERR_FORMAT = -1,
    INK_ERR_TITLE  = -2,
    INK_ERR_TAGS   = -3
};

/*
 * Parse buf[0..len). On success fills *out and returns the byte offset where
 * the body starts (>= 0). On failure returns a negative INK_ERR_* code.
 */
int ink_parse(const uint8_t *buf, size_t len, int32_t uploader_id, ink_meta_t *out);

#endif /* INK_PARSER_H */
