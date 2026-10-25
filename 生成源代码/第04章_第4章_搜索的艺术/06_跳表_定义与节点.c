#include <stdio.h>
#include <stdlib.h>

#define MAX_LEVEL 4  /* 为了演示,限制最大层数为4 */

/* 跳表节点 */
typedef struct SkipListNode {
    int key;                                  /* 节点存的数据 */
    struct SkipListNode *forward[MAX_LEVEL];  /* 核心:指针数组记录每一层的后继节点 */
} SkipListNode;

/* 跳表主结构 */
typedef struct SkipList {
    SkipListNode *header;  /* 头节点(哨兵,充当所有层的起点) */
    int level;             /* 记录当前跳表实际达到的最高层数 */
} SkipList;

/* 创建节点 */
SkipListNode *create_node(int key, int level) {
    SkipListNode *node = (SkipListNode *)malloc(sizeof(SkipListNode));
    if (node == NULL) {
        return NULL;
    }

    (void)level;  /* 教学版固定分配 MAX_LEVEL 个 forward 指针 */
    node->key = key;
    for (int i = 0; i < MAX_LEVEL; i++) {
        node->forward[i] = NULL;
    }
    return node;
}

/* 创建跳表 */
SkipList *create_skip_list(void) {
    SkipList *list = (SkipList *)malloc(sizeof(SkipList));
    if (list == NULL) {
        return NULL;
    }

    list->header = create_node(-1, MAX_LEVEL);  /* 哨兵节点 */
    if (list->header == NULL) {
        free(list);
        return NULL;
    }

    list->level = 0;
    return list;
}

/* 随机生成层数(模拟"抛硬币"决定建几层索引) */
int random_level(void) {
    int level = 0;
    while (rand() % 2 && level < MAX_LEVEL - 1) {
        level++;
    }
    return level;
}

/* 查找目标值 target */
int skip_list_search(SkipList *list, int target) {
    if (list == NULL) {
        return 0;
    }

    SkipListNode *current = list->header;

    /* 外层循环:从当前最高层,一层一层往下找 */
    for (int i = list->level; i >= 0; i--) {

        /* 内层循环:在当前这一层,只要右边的值比目标小,就一直往右走 */
        while (current->forward[i] != NULL && current->forward[i]->key < target) {
            current = current->forward[i];
        }
        /* 当右边的值 >= 目标值,或者右边没路了,随外层循环自然降到下一层 */
    }

    /* 降落到最底层后,current 是刚好小于 target 的节点 */
    current = current->forward[0];

    if (current != NULL && current->key == target) {
        return 1;
    }
    return 0;
}

/* 按指定层高插入:用于稳定复现书稿 4.4.3 的教学样例 */
int skip_list_insert_with_level(SkipList *list, int key, int newLevel) {
    if (list == NULL || newLevel < 0 || newLevel >= MAX_LEVEL) {
        return 0;
    }

    SkipListNode *update[MAX_LEVEL];
    SkipListNode *current = list->header;

    for (int i = list->level; i >= 0; i--) {
        while (current->forward[i] != NULL && current->forward[i]->key < key) {
            current = current->forward[i];
        }
        update[i] = current;
    }

    current = current->forward[0];
    if (current != NULL && current->key == key) {
        return 1;
    }

    if (newLevel > list->level) {
        for (int i = list->level + 1; i <= newLevel; i++) {
            update[i] = list->header;
        }
        list->level = newLevel;
    }

    SkipListNode *new_node = create_node(key, newLevel);
    if (new_node == NULL) {
        return 0;
    }

    for (int i = 0; i <= newLevel; i++) {
        new_node->forward[i] = update[i]->forward[i];
        update[i]->forward[i] = new_node;
    }

    return 1;
}

/* 插入新数据 key */
void skip_list_insert(SkipList *list, int key) {
    int newLevel = random_level();
    (void)skip_list_insert_with_level(list, key, newLevel);
}

/* 打印跳表 */
void print_skip_list(SkipList *list) {
    if (list == NULL) {
        return;
    }

    printf("跳表结构:\n");
    for (int i = list->level; i >= 0; i--) {
        SkipListNode *node = list->header->forward[i];
        printf("  L%d: ", i + 1);
        while (node != NULL) {
            printf("%d -> ", node->key);
            node = node->forward[i];
        }
        printf("NULL\n");
    }
}

void free_skip_list(SkipList *list) {
    if (list == NULL) {
        return;
    }

    SkipListNode *node = list->header->forward[0];
    while (node != NULL) {
        SkipListNode *next = node->forward[0];
        free(node);
        node = next;
    }
    free(list->header);
    free(list);
}

int main(void) {
    SkipList *list = create_skip_list();
    if (list == NULL) {
        printf("创建跳表失败\n");
        return 1;
    }

    /* 复现书稿 4.4.3:
       L3: 1 -> 9
       L2: 1 -> 4 -> 7 -> 9
       L1: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 */
    int keys[] =    {1, 2, 3, 4, 5, 6, 7, 8, 9};
    int levels[] =  {2, 0, 0, 1, 0, 0, 1, 0, 2};
    int n = sizeof(keys) / sizeof(keys[0]);

    for (int i = 0; i < n; i++) {
        if (!skip_list_insert_with_level(list, keys[i], levels[i])) {
            printf("插入 %d 失败\n", keys[i]);
            free_skip_list(list);
            return 1;
        }
    }

    print_skip_list(list);

    int targets[] = {8, 10};
    int targetCount = sizeof(targets) / sizeof(targets[0]);
    for (int i = 0; i < targetCount; i++) {
        int result = skip_list_search(list, targets[i]);
        printf("查找 %d: %s\n", targets[i], result ? "找到" : "未找到");
    }

    free_skip_list(list);
    return 0;
}
