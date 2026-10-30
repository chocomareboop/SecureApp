/*
 * ink_parser.c — native parser for InkPost ".ink" import files.
 * See ink_parser.h for the file format.
 *
 * Every length field read from the file is untrusted: it is checked against
 * both the destination buffer and the bytes remaining before any copy.
 */
#include "ink_parser.h"

#include <stdio.h>
#include <string.h>

static uint16_t read_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | (p[1] << 8));
}

/*
 * Copy a length-prefixed field into dst (capacity dst_size, including the
 * terminator). Rejects the field if it would not fit or if it claims more
 * bytes than remain in the input.
 */
static int copy_field(char *dst, size_t dst_size, const uint8_t *src, size_t field_len, size_t remaining)
{
    int written;

    if (field_len >= dst_size || field_len > remaining)
        return -1;
    written = snprintf(dst, dst_size, "%.*s", (int)field_len, (const char *)src);
    if (written < 0 || (size_t)written >= dst_size)
        return -1;
    return 0;
}

int ink_parse(const uint8_t *buf, size_t len, int32_t uploader_id, ink_meta_t *out)
{
    ink_meta_t meta;
    size_t pos;
    uint16_t title_len;
    uint16_t tags_len;

    if (buf == NULL || out == NULL || len < 8)
        return INK_ERR_FORMAT;
    if (memcmp(buf, INK_MAGIC, 4) != 0)
        return INK_ERR_FORMAT;
    pos = 4;

    /* Imported posts always start as drafts owned by the uploader. */
    memset(&meta, 0, sizeof meta);
    meta.author_id = uploader_id;
    meta.is_published = 0;

    if (pos + 2 > len)
        return INK_ERR_FORMAT;
    title_len = read_u16(buf + pos);
    pos += 2;

    /* FIX-1 (CWE-120): never trust the length field from the file. */
    if (copy_field(meta.title, sizeof meta.title, buf + pos, title_len, len - pos) != 0)
        return INK_ERR_TITLE;
    pos += title_len;

    if (pos + 2 > len)
        return INK_ERR_FORMAT;
    tags_len = read_u16(buf + pos);
    pos += 2;
    if (copy_field(meta.tags, sizeof meta.tags, buf + pos, tags_len, len - pos) != 0)
        return INK_ERR_TAGS;
    pos += tags_len;

    *out = meta;
    return (int)pos;
}
