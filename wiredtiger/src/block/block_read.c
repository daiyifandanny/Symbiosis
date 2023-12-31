/*-
 * Copyright (c) 2014-present MongoDB, Inc.
 * Copyright (c) 2008-2014 WiredTiger, Inc.
 *	All rights reserved.
 *
 * See the file LICENSE for redistribution information.
 */

#include "wt_internal.h"
#include <sys/sdt.h>
#include "external.h"
#include <x86intrin.h>

uint64_t timer1 = 0;
uint64_t timer2 = 0;

/*
 * __wt_bm_preload --
 *     Pre-load a page.
 */
int
__wt_bm_preload(WT_BM *bm, WT_SESSION_IMPL *session, const uint8_t *addr, size_t addr_size)
{
    WT_BLOCK *block;
    WT_DECL_ITEM(tmp);
    WT_DECL_RET;
    WT_FH *fh;
    WT_FILE_HANDLE *handle;
    wt_off_t offset;
    uint32_t checksum, logid, size;
    bool mapped;

    block = bm->block;

    WT_STAT_CONN_INCR(session, block_preload);

    /* Crack the cookie. */
    WT_RET(__wt_block_buffer_to_addr(block, addr, &logid, &offset, &size, &checksum));

    WT_RET(__wt_block_fh(session, block, logid, &fh));
    handle = fh->handle;
    mapped = bm->map != NULL && offset + size <= (wt_off_t)bm->maplen;
    if (mapped && handle->fh_map_preload != NULL)
        ret = handle->fh_map_preload(
          handle, (WT_SESSION *)session, (uint8_t *)bm->map + offset, size, bm->mapped_cookie);
    if (!mapped && handle->fh_advise != NULL)
        ret = handle->fh_advise(
          handle, (WT_SESSION *)session, offset, (wt_off_t)size, WT_FILE_HANDLE_WILLNEED);
    if (ret != EBUSY && ret != ENOTSUP)
        return (ret);

    /* If preload isn't supported, do it the slow way. */
    WT_RET(__wt_scr_alloc(session, 0, &tmp));
    ret = __wt_bm_read(bm, session, tmp, addr, addr_size);
    __wt_scr_free(session, &tmp);

    return (ret);
}

/*
 * __wt_bm_read --
 *     Map or read address cookie referenced block into a buffer.
 */
int
__wt_bm_read(
  WT_BM *bm, WT_SESSION_IMPL *session, WT_ITEM *buf, const uint8_t *addr, size_t addr_size)
{
    WT_BLOCK *block;
    WT_DECL_RET;
    WT_FH *fh;
    WT_FILE_HANDLE *handle;
    wt_off_t offset;
    uint32_t checksum, logid, size;
    bool mapped;

    WT_UNUSED(addr_size);
    block = bm->block;

    /* Crack the cookie. */
    WT_RET(__wt_block_buffer_to_addr(block, addr, &logid, &offset, &size, &checksum));

    /*
     * Map the block if it's possible.
     */
    WT_RET(__wt_block_fh(session, block, logid, &fh));
    handle = fh->handle;
    mapped = bm->map != NULL && offset + size <= (wt_off_t)bm->maplen;
    if (mapped && handle->fh_map_preload != NULL) {
        buf->data = (uint8_t *)bm->map + offset;
        buf->size = size;
        ret = handle->fh_map_preload(
          handle, (WT_SESSION *)session, buf->data, buf->size, bm->mapped_cookie);

        WT_STAT_CONN_INCR(session, block_map_read);
        WT_STAT_CONN_INCRV(session, block_byte_map_read, size);
        return (ret);
    }

#ifdef HAVE_DIAGNOSTIC
    /*
     * In diagnostic mode, verify the block we're about to read isn't on the available list, or for
     * live systems, the discard list.
     */
    WT_RET(
      __wt_block_misplaced(session, block, "read", offset, size, bm->is_live, __func__, __LINE__));
#endif
    /* Read the block. */
    __wt_capacity_throttle(session, size, WT_THROTTLE_READ);
    WT_RET(__wt_block_read_off(session, block, buf, logid, offset, size, checksum));

    /* Optionally discard blocks from the system's buffer cache. */
    WT_RET(__wt_block_discard(session, block, (size_t)size));

    return (0);
}

/*
 * __wt_bm_corrupt_dump --
 *     Dump a block into the log in 1KB chunks.
 */
static int
__wt_bm_corrupt_dump(WT_SESSION_IMPL *session, WT_ITEM *buf, uint32_t logid, wt_off_t offset,
  uint32_t size, uint32_t checksum) WT_GCC_FUNC_ATTRIBUTE((cold))
{
    WT_DECL_ITEM(tmp);
    WT_DECL_RET;
    size_t chunk, i, nchunks;

#define WT_CORRUPT_FMT "{%" PRIu32 ": %" PRIuMAX ", %" PRIu32 ", %#" PRIx32 "}"
    if (buf->size == 0) {
        __wt_errx(session, WT_CORRUPT_FMT ": empty buffer, no dump available", logid,
          (uintmax_t)offset, size, checksum);
        return (0);
    }

    WT_RET(__wt_scr_alloc(session, 4 * 1024, &tmp));

    nchunks = buf->size / 1024 + (buf->size % 1024 == 0 ? 0 : 1);
    for (chunk = i = 0;;) {
        WT_ERR(__wt_buf_catfmt(session, tmp, "%02x ", ((uint8_t *)buf->data)[i]));
        if (++i == buf->size || i % 1024 == 0) {
            __wt_errx(session,
              WT_CORRUPT_FMT ": (chunk %" WT_SIZET_FMT " of %" WT_SIZET_FMT "): %.*s", logid,
              (uintmax_t)offset, size, checksum, ++chunk, nchunks, (int)tmp->size,
              (char *)tmp->data);
            if (i == buf->size)
                break;
            WT_ERR(__wt_buf_set(session, tmp, "", 0));
        }
    }

err:
    __wt_scr_free(session, &tmp);
    return (ret);
}

/*
 * __wt_bm_corrupt --
 *     Report a block has been corrupted, external API.
 */
int
__wt_bm_corrupt(WT_BM *bm, WT_SESSION_IMPL *session, const uint8_t *addr, size_t addr_size)
{
    WT_DECL_ITEM(tmp);
    WT_DECL_RET;
    wt_off_t offset;
    uint32_t checksum, logid, size;

    /* Read the block. */
    WT_RET(__wt_scr_alloc(session, 0, &tmp));
    WT_ERR(__wt_bm_read(bm, session, tmp, addr, addr_size));

    /* Crack the cookie, dump the block. */
    WT_ERR(__wt_block_buffer_to_addr(bm->block, addr, &logid, &offset, &size, &checksum));
    WT_ERR(__wt_bm_corrupt_dump(session, tmp, logid, offset, size, checksum));

err:
    __wt_scr_free(session, &tmp);
    return (ret);
}

#ifdef HAVE_DIAGNOSTIC
/*
 * __wt_block_read_off_blind --
 *     Read the block at an offset, return the size and checksum, debugging only.
 */
int
__wt_block_read_off_blind(
  WT_SESSION_IMPL *session, WT_BLOCK *block, wt_off_t offset, uint32_t *sizep, uint32_t *checksump)
{
    WT_BLOCK_HEADER *blk;
    WT_DECL_ITEM(tmp);
    WT_DECL_RET;

    *sizep = 0;
    *checksump = 0;

    /*
     * Make sure the buffer is large enough for the header and read the first allocation-size block.
     */
    WT_RET(__wt_scr_alloc(session, block->allocsize, &tmp));
    WT_ERR(__wt_read(session, block->fh, offset, (size_t)block->allocsize, tmp->mem));
    blk = WT_BLOCK_HEADER_REF(tmp->mem);
    __wt_block_header_byteswap(blk);

    *sizep = blk->disk_size;
    *checksump = blk->checksum;

err:
    __wt_scr_free(session, &tmp);
    return (ret);
}
#endif

/*
 * __wt_block_fh --
 *     Get a block file handle.
 */
int
__wt_block_fh(WT_SESSION_IMPL *session, WT_BLOCK *block, uint32_t logid, WT_FH **fhp)
{
    WT_DECL_ITEM(tmp);
    WT_DECL_RET;
    const char *filename;

    if (!block->log_structured || logid == block->logid) {
        *fhp = block->fh;
        return (0);
    }

    /* TODO: fh readlock */
    if (logid * sizeof(WT_FILE_HANDLE *) < block->lfh_alloc && (*fhp = block->lfh[logid]) != NULL)
        return (0);

    /* TODO: fh writelock */
    /* Ensure the array goes far enough. */
    WT_RET(__wt_realloc_def(session, &block->lfh_alloc, logid + 1, &block->lfh));
    if (logid >= block->max_logid)
        block->max_logid = logid + 1;
    if ((*fhp = block->lfh[logid]) != NULL)
        return (0);

    WT_RET(__wt_scr_alloc(session, 0, &tmp));
    if (logid == 0)
        filename = block->name;
    else {
        WT_ERR(__wt_buf_fmt(session, tmp, "%s.%08" PRIu32, block->name, logid));
        filename = tmp->data;
    }
    WT_ERR(__wt_open(session, filename, WT_FS_OPEN_FILE_TYPE_DATA,
      WT_FS_OPEN_READONLY | block->file_flags, &block->lfh[logid]));
    *fhp = block->lfh[logid];
    WT_ASSERT(session, *fhp != NULL);

err:
    __wt_scr_free(session, &tmp);
    return (ret);
}

/*
 * __wt_block_read_off --
 *     Read an addr/size pair referenced block into a buffer.
 */
int
__wt_block_read_off(WT_SESSION_IMPL *session, WT_BLOCK *block, WT_ITEM *buf, uint32_t logid,
  wt_off_t offset, uint32_t size, uint32_t checksum)
{
    WT_BLOCK_HEADER *blk, swap;
    WT_FH *fh;
    size_t bufsize;

    __wt_verbose(session, WT_VERB_READ, "off %" PRIuMAX ", size %" PRIu32 ", checksum %#" PRIx32,
      (uintmax_t)offset, size, checksum);

    WT_STAT_CONN_INCR(session, block_read);
    WT_STAT_CONN_INCRV(session, block_byte_read, size);

    /*
     * Grow the buffer as necessary and read the block. Buffers should be aligned for reading, but
     * there are lots of buffers (for example, file cursors have two buffers each, key and value),
     * and it's difficult to be sure we've found all of them. If the buffer isn't aligned, it's an
     * easy fix: set the flag and guarantee we reallocate it. (Most of the time on reads, the buffer
     * memory has not yet been allocated, so we're not adding any additional processing time.)
     */
    if (F_ISSET(buf, WT_ITEM_ALIGNED))
        bufsize = size;
    else {
        F_SET(buf, WT_ITEM_ALIGNED);
        bufsize = WT_MAX(size, buf->memsize + 10);
    }

    // uint64_t temp1 = __rdtsc(), temp2, temp3;

    /*
     * Ensure we don't read information that isn't there. It shouldn't ever happen, but it's a cheap
     * test.
     */
    if (size < block->allocsize)
        WT_RET_MSG(session, EINVAL,
          "%s: impossibly small block size of %" PRIu32 "B, less than allocation size of %" PRIu32,
          block->name, size, block->allocsize);

    WT_RET(__wt_buf_init(session, buf, bufsize));
    WT_RET(__wt_block_fh(session, block, logid, &fh));

    uint32_t dummy;
    uint64_t timer = __rdtscp(&dummy);
    WT_RET(__wt_read(session, fh, offset, size, buf->mem));
    kernel_cache_time = __rdtscp(&dummy) - timer;
    kernel_cache_size = size;
    kernel_cache_start = offset;
    buf->size = size;

    // static ino_t last_ino = -1;
    // static int last_fd = -1;
    // WT_FILE_HANDLE_POSIX* pfh = (WT_FILE_HANDLE_POSIX*) fh->handle;
    // int fd = pfh->fd;
    // if (fd != last_fd) {
    //     struct stat buf;
    //     fstat(fd, &buf);
    //     last_ino = buf.st_ino;
    // }
    // ino_t ino = last_ino;

    // temp2 = __rdtsc();
    // timer1 += temp2 - temp1;
    
    // FILE* f = fopen("wt_trace_disk.txt", "a");
    // fprintf(f, "%lu %u\n", offset / 4096, size / 4096);
    // fclose(f);
    
    // for (uint64_t i = offset / 4096; i <= (uint64_t) (offset + size) / 4096; ++i) {
    //   DTRACE_PROBE2(leveldb, pcache_access1, ino, i);      
    // }

    /*
     * We incrementally read through the structure before doing a checksum, do little- to big-endian
     * handling early on, and then select from the original or swapped structure as needed.
     */
    blk = WT_BLOCK_HEADER_REF(buf->mem);
    __wt_block_header_byteswap_copy(blk, &swap);
    if (swap.checksum == checksum) {
        blk->checksum = 0;
        // temp2 = __rdtsc();
        if (__wt_checksum_match(buf->mem,
              F_ISSET(&swap, WT_BLOCK_DATA_CKSUM) ? size : WT_BLOCK_COMPRESS_SKIP, checksum)) {
            /*
             * Swap the page-header as needed; this doesn't belong here, but it's the best place to
             * catch all callers.
             */
            __wt_page_header_byteswap(buf->mem);
            
            // timer2 += __rdtsc() - temp2;
            
            return (0);
        }

        if (!F_ISSET(session, WT_SESSION_QUIET_CORRUPT_FILE))
            __wt_errx(session,
              "%s: read checksum error for %" PRIu32 "B block at offset %" PRIuMAX
              ": calculated block checksum  doesn't match expected checksum",
              block->name, size, (uintmax_t)offset);
    } else if (!F_ISSET(session, WT_SESSION_QUIET_CORRUPT_FILE))
        __wt_errx(session,
          "%s: read checksum error for %" PRIu32 "B block at offset %" PRIuMAX
          ": block header checksum of %#" PRIx32 " doesn't match expected checksum of %#" PRIx32,
          block->name, size, (uintmax_t)offset, swap.checksum, checksum);

    if (!F_ISSET(session, WT_SESSION_QUIET_CORRUPT_FILE))
        WT_IGNORE_RET(__wt_bm_corrupt_dump(session, buf, logid, offset, size, checksum));

    /* Panic if a checksum fails during an ordinary read. */
    F_SET(S2C(session), WT_CONN_DATA_CORRUPTION);
    if (block->verify || F_ISSET(session, WT_SESSION_QUIET_CORRUPT_FILE))
        return (WT_ERROR);
    WT_RET_PANIC(session, WT_ERROR, "%s: fatal read error", block->name);
}
