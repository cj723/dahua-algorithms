#include <stdio.h>
#include <string.h>
#include <stdlib.h>

void build_next(const char *pattern, int *next, int m) {
    next[0] = -1;
    int i = 0, j = -1;
    while (i < m - 1) {
        if (j == -1 || pattern[i] == pattern[j]) {
            i++;
            j++;
            next[i] = j;
        } else {
            j = next[j];
        }
    }
}

/* KMP 匹配算法 */
int kmp_search(const char *text, const char *pattern) {
    int n = (int)strlen(text);
    int m = (int)strlen(pattern);

    if (m == 0) return 0;      /* 空模式串：约定匹配在起始位置 */
    if (n < m) return -1;      /* 模式串比文本还长，不可能匹配 */

    int *next = (int *)malloc(m * sizeof(int));
    if (next == NULL) {
        printf("内存分配失败\n");
        return -1;
    }
    
    build_next(pattern, next, m);
    
    int i = 0, j = 0;  /* i 是 text 的指针，j 是 pattern 的指针 */
    while (i < n && j < m) {
        if (j == -1 || text[i] == pattern[j]) {
            i++;
            j++;
        } else {
            j = next[j];  /* 模式串回退，文本指针不动！ */
        }
    }
    
    free(next);
    
    if (j == m) {
        return i - m;  /* 找到了，返回起始位置 */
    }
    return -1;
}

int main(void) {
    char text[] = "ABABDABACDABABCABAB";
    char pattern[] = "ABABCABAB";
    
    int pos = kmp_search(text, pattern);
    if (pos != -1) {
        printf("KMP 匹配成功！起始位置：%d\n", pos);
    } else {
        printf("未找到匹配\n");
    }
    return 0;
}
