#include <stdio.h>
#include <string.h>

/*
 * LZ77 压缩简化演示
 *
 * 类比：你写作文抄了前面的句子，老师说“你抄袭！”
 * LZ77 说：重复没关系，标注清楚“从哪复制，复制多少字”就行
 */

#define WINDOW_SIZE 20   /* 滑动窗口大小 */
#define MAX_MATCH 10     /* 最长匹配长度 */

typedef struct {
    int is_literal;      /* 1 = 原样输出，0 = 引用 */
    char ch;             /* 字面字符 */
    int offset;          /* 回退偏移量 */
    int length;          /* 匹配长度 */
} Token;

int find_match(const char *text, int pos, int *out_offset, int *out_length) {
    int best_len = 0;
    int best_offset = 0;
    int win_start = (pos > WINDOW_SIZE) ? pos - WINDOW_SIZE : 0;
    int text_len = strlen(text);  /* 缓存长度，避免循环里反复调用 strlen */

    /* 在滑动窗口里找最长匹配 */
    for (int i = win_start; i < pos; i++) {
        int len = 0;
        while (len < MAX_MATCH &&
               pos + len < text_len &&
               text[i + len] == text[pos + len]) {
            len++;
        }
        if (len > best_len) {
            best_len = len;
            best_offset = pos - i;
        }
    }

    *out_offset = best_offset;
    *out_length = best_len;
    return (best_len >= 3);  /* 匹配至少 3 个字符才值得用引用 */
}

int main(void) {
    const char *text = "ABCDABCDABCDABCD";
    Token tokens[100];
    int tcount = 0;
    int pos = 0;
    int total_len = strlen(text);

    printf("原文： %s\n", text);
    printf("原文长度： %d 字节\n\n", total_len);

    while (pos < total_len) {
        int offset, length;

        if (find_match(text, pos, &offset, &length)) {
            tokens[tcount].is_literal = 0;
            tokens[tcount].offset = offset;
            tokens[tcount].length = length;
            printf("位置 %2d：引用（回退 %d，长度 %d）\n", pos, offset, length);
            pos += length;
        } else {
            tokens[tcount].is_literal = 1;
            tokens[tcount].ch = text[pos];
            printf("位置 %2d：字面 '%c'\n", pos, text[pos]);
            pos++;
        }
        tcount++;
    }

    printf("\n总计 %d 个 Token\n", tcount);

    return 0;
}
