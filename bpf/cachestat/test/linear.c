#include <fcntl.h>
#include <unistd.h>
#include <sys/sdt.h>
#include <sys/stat.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>


int main(int argc, char** argv) {
    int step = argc == 3 ? atoi(argv[2]) : 0;
    int fd = open("/nvme/test/tsukushi.txt", O_RDONLY);
    char buf[10];
    srand(210);
    uint64_t size = atoi(argv[1]);

    struct stat statbuf;
    fstat(fd, &statbuf);
    uint64_t ino = statbuf.st_ino;
    
    uint64_t limit = step == 0 ? 1000 : size;
    for (uint64_t i = 0; i < limit;) {
        uint64_t target;
        if (step == 0) {
            target = rand() % size;
            i += 1;
        } else if (step > 0) {
            target = i;
            i += step;
        } else {
            scanf("%lu", &target);
        }
        DTRACE_PROBE2(leveldb, fcache_start_probe, ino, target);
        pread(fd, buf, 9, target * 4096);
        DTRACE_PROBE2(leveldb, pcache_access1, ino, target);
        DTRACE_PROBE2(leveldb, fcache_end_probe, ino, target);
    }
    DTRACE_PROBE2(leveldb, bcache_start_probe, 0, 0);
    DTRACE_PROBE2(leveldb, bcache_end_probe, 0, 0);
    DTRACE_PROBE2(leveldb, search1_start_probe, 0, 0);
    DTRACE_PROBE2(leveldb, search1_end_probe, 0, 0);
    // DTRACE_PROBE2(leveldb, search2_start_probe, 0, 0);
    // DTRACE_PROBE2(leveldb, search2_end_probe, 0, 0);
    // DTRACE_PROBE2(leveldb, pcache_access1, 0, 0);
    DTRACE_PROBE2(leveldb, pcache_access2, 0, 0);
}
