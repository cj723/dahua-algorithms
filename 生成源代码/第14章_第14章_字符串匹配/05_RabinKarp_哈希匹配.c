#include <stdio.h>
#include <string.h>

#define BASE 256    /* 字符集大小 */
#define MOD  1000000007  /* 大素数 10^9 + 7，减少哈希冲突 */

/* Rabin-Karp 算法 */
void rabin_karp(const char *text, const char *pattern) {
    int n = (int)strlen(text);
    int m = (int)strlen(pattern);

    if (m == 0) {
        printf("匹配成功！起始位置：0\n");
        return;
    }
    if (n < m) {
        return;
    }
    
    /* 计算 BASE^(m - 1) % MOD，用于滚动时减去最高位 */
    long long h = 1;
    for (int i = 0; i < m - 1; i++) {
        h = (h * BASE) % MOD;
    }
    
    /* 计算模式串和文本第一个窗口的哈希值 */
    long long hash_p = 0;  /* 模式串的哈希 */
    long long hash_t = 0;  /* 文本当前窗口的哈希 */
    for (int i = 0; i < m; i++) {
        hash_p = (BASE * hash_p + (unsigned char)pattern[i]) % MOD;
        hash_t = (BASE * hash_t + (unsigned char)text[i]) % MOD;
    }
    
    /* 滑动窗口 */
    for (int i = 0; i <= n - m; i++) {
        /* 哈希值匹配，逐字符确认 */
        if (hash_p == hash_t) {
            int j;
            for (j = 0; j < m; j++) {
                if (text[i + j] != pattern[j]) {
                    break;
                }
            }
            if (j == m) {
                printf("匹配成功！起始位置：%d\n", i);
            }
        }
        
        /* 滚动计算下一个窗口的哈希 */
        if (i < n - m) {
            long long lead = (unsigned char)text[i];
            long long tail = (unsigned char)text[i + m];
            hash_t = (BASE * (hash_t - lead * h) + tail) % MOD;
            /* C 语言取模可能得到负数，修正为非负 */
            if (hash_t < 0) {
                hash_t += MOD;
            }
        }
    }
}

int main(void) {
    char text[] = "ABABDABACDABABCABAB";
    char pattern[] = "ABABCABAB";
    
    printf("Rabin-Karp 匹配结果：\n");
    rabin_karp(text, pattern);
    return 0;
}
