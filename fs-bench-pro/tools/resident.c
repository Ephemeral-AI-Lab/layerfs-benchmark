/* resident [--evict] FILE...: per file, optionally fdatasync + posix_fadvise(DONTNEED)
 * (drops only that file's clean pages; no privilege, nothing shared), then prints
 * "<resident_pages> <total_pages> <path>" from mincore. Exit 1 on any error. */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
int main(int argc, char **argv) {
    int evict = argc > 1 && strcmp(argv[1], "--evict") == 0, rc = 0;
    long page = sysconf(_SC_PAGESIZE);
    for (int i = 1 + evict; i < argc; i++) {
        int fd = open(argv[i], O_RDONLY);
        struct stat st;
        if (fd < 0 || fstat(fd, &st) < 0) { perror(argv[i]); rc = 1; continue; }
        if (evict && (fdatasync(fd) < 0 || posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED) != 0)) { perror(argv[i]); rc = 1; }
        size_t pages = (st.st_size + page - 1) / page, res = 0;
        if (pages) {
            void *m = mmap(NULL, st.st_size, PROT_READ, MAP_SHARED, fd, 0);
            unsigned char *v = malloc(pages);
            if (m == MAP_FAILED || !v || mincore(m, st.st_size, v) < 0) { perror(argv[i]); rc = 1; }
            else for (size_t p = 0; p < pages; p++) res += v[p] & 1;
            if (m != MAP_FAILED) munmap(m, st.st_size);
            free(v);
        }
        printf("%zu %zu %s\n", res, pages, argv[i]);
        close(fd);
    }
    return rc;
}
