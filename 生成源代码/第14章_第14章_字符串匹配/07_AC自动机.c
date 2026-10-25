#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ALPHABET_SIZE 26
#define MAX_QUEUE 10000

typedef struct ACNode {
    struct ACNode *children[ALPHABET_SIZE];
    struct ACNode *fail;
    int count;
} ACNode;

/* 创建节点 */
ACNode *create_node(void) {
    ACNode *node = (ACNode *)calloc(1, sizeof(ACNode));
    if (node == NULL) {
        printf("内存分配失败\n");
        exit(1);
    }
    return node;
}

/* 插入模式串 */
void insert(ACNode *root, const char *word) {
    ACNode *cur = root;

    for (int i = 0; word[i]; i++) {
        int idx = word[i] - 'a';
        if (idx < 0 || idx >= ALPHABET_SIZE) {
            continue;  /* 简化处理：跳过非小写字母 */
        }

        if (!cur->children[idx]) {
            cur->children[idx] = create_node();
        }

        cur = cur->children[idx];
    }

    cur->count++;
}

/* BFS 构建 fail 指针 */
void build_fail(ACNode *root) {
    ACNode *queue[MAX_QUEUE];
    int front = 0, rear = 0;

    root->fail = root;

    /* 第一层 fail 指向 root */
    for (int i = 0; i < ALPHABET_SIZE; i++) {
        if (root->children[i]) {
            root->children[i]->fail = root;
            if (rear >= MAX_QUEUE) {
                printf("队列容量不足\n");
                exit(1);
            }
            queue[rear++] = root->children[i];
        }
    }

    while (front < rear) {
        ACNode *cur = queue[front++];

        for (int i = 0; i < ALPHABET_SIZE; i++) {
            ACNode *child = cur->children[i];

            if (!child) continue;

            ACNode *p = cur->fail;

            while (p != root && !p->children[i]) {
                p = p->fail;
            }

            if (p->children[i] && p->children[i] != child) {
                child->fail = p->children[i];
            } else {
                child->fail = root;
            }

            /* 继承 fail 链上的匹配 */
            child->count += child->fail->count;

            if (rear >= MAX_QUEUE) {
                printf("队列容量不足\n");
                exit(1);
            }
            queue[rear++] = child;
        }
    }
}

/* 搜索 */
int ac_search(ACNode *root, const char *text) {
    ACNode *cur = root;
    int total = 0;

    for (int i = 0; text[i]; i++) {
        int idx = text[i] - 'a';
        if (idx < 0 || idx >= ALPHABET_SIZE) {
            cur = root;
            continue;
        }

        while (cur != root && !cur->children[idx]) {
            cur = cur->fail;
        }

        if (cur->children[idx]) {
            cur = cur->children[idx];
        }

        total += cur->count;
    }

    return total;
}

void ac_free(ACNode *root) {
    if (root == NULL) return;
    for (int i = 0; i < ALPHABET_SIZE; i++) {
        ac_free(root->children[i]);
    }
    free(root);
}

int main(void) {
    ACNode *root = create_node();

    insert(root, "abc");
    insert(root, "bcd");
    insert(root, "cde");

    build_fail(root);

    char text[] = "xabcdex";

    int ans = ac_search(root, text);

    printf("match count = %d\n", ans);
    ac_free(root);

    return 0;
}
