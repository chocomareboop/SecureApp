/*
 * ink_parser.c — native parser for InkPost ".ink" import files.
 * See ink_parser.h for the file format.
 *
 * LAB BUILD: contains an intentional memory-safety bug (VULN-1).
 */
#include "ink_parser.h"

#include <string.h>

static uint16_t read_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | (p[1] << 8));
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

    title_len = read_u16(buf + pos);
    pos += 2;

    /*
     * VULN-1 (CWE-120 / CWE-787): title_len is taken straight from the file and
     * is never checked against sizeof(meta.title) or against the bytes left in
     * buf. A title longer than 64 bytes overwrites is_published and author_id
     * (data corruption); a much longer one runs past the struct and smashes the
     * saved return address on the stack (control-flow hijack / crash).
     */
    memcpy(meta.title, buf + pos, title_len);
    meta.title[title_len] = '\0';
    pos += title_len;

    if (pos + 2 > len)
        return INK_ERR_FORMAT;
    tags_len = read_u16(buf + pos);
    pos += 2;
    if (tags_len >= sizeof meta.tags || tags_len > len - pos)
        return INK_ERR_TAGS;
    memcpy(meta.tags, buf + pos, tags_len);
    meta.tags[tags_len] = '\0';
    pos += tags_len;

    *out = meta;
    return (int)pos;
}
