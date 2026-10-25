#include <stdio.h>
#include <string.h>

/* BF 暴力匹配算法 */
int bf_search(const char *text, const char *pattern) {
    int n = (int)strlen(text);
    int m = (int)strlen(pattern);

    if (m == 0) return 0;      /* 空模式串：约定匹配在起始位置 */
    if (n < m) return -1;      /* 模式串比文本还长，不可能匹配 */
    
    for (int i = 0; i <= n - m; i++) {
        int j = 0;
        for (; j < m; j++) {
            if (text[i + j] != pattern[j]) {
                break;  /* 不匹配，跳出内层循环 */
            }
        }
        if (j == m) {
            return i;  /* 找到了，返回起始位置 */
        }
    }
    return -1;  /* 没找到 */
}

int main(void) {
    char text[] = "ABABDABACDABABCABAB";
    char pattern[] = "ABABCABAB";
    
    int pos = bf_search(text, pattern);
    if (pos != -1) {
        printf("匹配成功！起始位置：%d\n", pos);
    } else {
        printf("未找到匹配\n");
    }
    return 0;
}
