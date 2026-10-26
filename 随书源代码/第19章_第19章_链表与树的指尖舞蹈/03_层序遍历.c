#include <stdio.h>
#include <stdlib.h>

/* 树节点定义 */
struct TreeNode {
    int val;
    struct TreeNode *left;
    struct TreeNode *right;
};

/* C 语言层序遍历的难点，一半在队列，一半在返回值。 */
int **level_order(struct TreeNode *root, int *returnSize, int **returnColumnSizes) {
    *returnSize = 0;              /* 记录总共有多少层 */
    *returnColumnSizes = NULL;    /* 先把输出参数初始化，避免空树时留下野指针 */

    if (root == NULL) {
        return NULL;
    }

    int resCapacity = 16;  /* 当前结果数组最多能装多少层 */
    int **res = (int **)malloc(resCapacity * sizeof(int *));
    *returnColumnSizes = (int *)malloc(resCapacity * sizeof(int));

    int queueCapacity = 1024;  /* 队列容量不写死为某个题目的节点上限 */
    struct TreeNode **queue = (struct TreeNode **)malloc(queueCapacity * sizeof(struct TreeNode *));
    int head = 0, tail = 0;

    if (res == NULL || *returnColumnSizes == NULL || queue == NULL) {
        free(res);
        free(*returnColumnSizes);
        free(queue);
        *returnColumnSizes = NULL;
        return NULL;
    }

    queue[tail++] = root;  /* CEO 入队 */

    while (head < tail) {
        int currentLevelSize = tail - head;  /* [关键]记录当前层的总人数！ */

        /* 结果数组容量不够时扩容 */
        if (*returnSize == resCapacity) {
            resCapacity *= 2;
            int **newRes = (int **)realloc(res, resCapacity * sizeof(int *));
            if (newRes == NULL) {
                free(queue);
                return res;
            }
            res = newRes;

            int *newColumnSizes = (int *)realloc(*returnColumnSizes, resCapacity * sizeof(int));
            if (newColumnSizes == NULL) {
                free(queue);
                return res;
            }
            *returnColumnSizes = newColumnSizes;
        }

        /* 为当前层分配存放结果的内存 */
        res[*returnSize] = (int *)malloc(currentLevelSize * sizeof(int));
        if (res[*returnSize] == NULL) {
            free(queue);
            return res;
        }
        (*returnColumnSizes)[*returnSize] = currentLevelSize;

        /* 集中处理当前这一层的所有人 */
        for (int i = 0; i < currentLevelSize; i++) {
            struct TreeNode *node = queue[head++];  /* 出队 */
            res[*returnSize][i] = node->val;        /* 领红包（存入结果） */

            /* 下属去排队。入队前检查容量，容量不够就扩容 */
            if (node->left != NULL) {
                if (tail == queueCapacity) {
                    queueCapacity *= 2;
                    struct TreeNode **newQueue = (struct TreeNode **)realloc(queue, queueCapacity * sizeof(struct TreeNode *));
                    if (newQueue == NULL) {
                        free(queue);
                        return res;
                    }
                    queue = newQueue;
                }
                queue[tail++] = node->left;
            }
            if (node->right != NULL) {
                if (tail == queueCapacity) {
                    queueCapacity *= 2;
                    struct TreeNode **newQueue = (struct TreeNode **)realloc(queue, queueCapacity * sizeof(struct TreeNode *));
                    if (newQueue == NULL) {
                        free(queue);
                        return res;
                    }
                    queue = newQueue;
                }
                queue[tail++] = node->right;
            }
        }
        (*returnSize)++;  /* 层数加 1 */
    }

    free(queue);  /* 结果数组要返回给调用者，队列只是临时工具，用完释放 */
    return res;
}



// 辅助：创建节点
struct TreeNode *make_node(int val) {
    struct TreeNode *n = (struct TreeNode *)malloc(sizeof(struct TreeNode));
    n->val = val; n->left = NULL; n->right = NULL;
    return n;
}

/* ===== 测试入口 ===== */
int main(void) {
    /*
     * 构建测试树:    3
     *              / \
     *             9  20
     *               /  \
     *              15   7
     */
    struct TreeNode *root = make_node(3);
    root->left = make_node(9);
    root->right = make_node(20);
    root->right->left = make_node(15);
    root->right->right = make_node(7);

    int returnSize;
    int *returnColumnSizes;
    int **result = level_order(root, &returnSize, &returnColumnSizes);

    printf("层序遍历结果：\n");
    for (int i = 0; i < returnSize; i++) {
        printf("第%d层: ", i + 1);
        for (int j = 0; j < returnColumnSizes[i]; j++) {
            printf("%d ", result[i][j]);
        }
        printf("\n");
    }

    /* 释放内存 */
    for (int i = 0; i < returnSize; i++) free(result[i]);
    free(result);
    free(returnColumnSizes);
    free(root->right->right); free(root->right->left);
    free(root->right); free(root->left); free(root);
    return 0;
}
