#include <stdio.h>
#include <stdlib.h>

struct TreeNode {
    int val;
    struct TreeNode *left;
    struct TreeNode *right;
};

struct TreeNode *lowest_common_ancestor(struct TreeNode *root,
                                        struct TreeNode *p,
                                        struct TreeNode *q) {
    /* 递归终止条件：到了空节点，或者找到了 p 或 q */
    if (root == NULL || root == p || root == q) {
        return root;
    }

    /* 1. 问左副手：左边有 p 或 q 吗？ */
    struct TreeNode *left = lowest_common_ancestor(root->left, p, q);

    /* 2. 问右副手：右边有 p 或 q 吗？ */
    struct TreeNode *right = lowest_common_ancestor(root->right, p, q);

    /* 3. 根据汇报结果做决策（处理当前节点逻辑，典型的后序位置） */
    if (left != NULL && right != NULL) {
        /* 左右两边各找到了一个，那我就是最近公共祖先！ */
        return root;
    }

    if (left != NULL) {
        /* 只有左边找到了，那就把左边的结果原样往上报 */
        return left;
    }

    if (right != NULL) {
        /* 只有右边找到了，那就把右边的结果原样往上报 */
        return right;
    }

    /* 左右都没找到 */
    return NULL;
}

/* 测试：最近公共祖先 */
int main(void) {
    /*
     * 构建树：
     *       3
     *     /   \
     *    5     1
     *   / \   / \
     *  6   2 0   8
     */
    struct TreeNode nodes[7];
    for (int i = 0; i < 7; i++) {
        nodes[i].left = nodes[i].right = NULL;
    }
    nodes[0].val = 3; nodes[0].left = &nodes[1]; nodes[0].right = &nodes[2];
    nodes[1].val = 5; nodes[1].left = &nodes[3]; nodes[1].right = &nodes[4];
    nodes[2].val = 1; nodes[2].left = &nodes[5]; nodes[2].right = &nodes[6];
    nodes[3].val = 6;
    nodes[4].val = 2;
    nodes[5].val = 0;
    nodes[6].val = 8;

    struct TreeNode *lca = lowest_common_ancestor(&nodes[0], &nodes[3], &nodes[4]);
    printf("6 和 2 的 LCA: %d（期望 5）\n", lca->val);

    lca = lowest_common_ancestor(&nodes[0], &nodes[3], &nodes[6]);
    printf("6 和 8 的 LCA: %d（期望 3）\n", lca->val);

    return 0;
}
