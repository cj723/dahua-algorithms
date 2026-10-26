#include <stdio.h>

#define MAX_N 10

int n;
int nums[MAX_N];      /* 输入元素 */
int path[MAX_N];      /* 当前构造中的排列 */
int used[MAX_N];      /* used[i] = 1 表示 nums[i] 已经被选过 */

void print_permutation(void) {
    for (int i = 0; i < n; i++) {
        printf("%d ", path[i]);
    }
    printf("\n");
}

void backtrack(int depth) {
    /* depth 表示当前要填写 path[depth] */
    if (depth == n) {
        print_permutation();
        return;
    }

    for (int i = 0; i < n; i++) {
        if (used[i]) {
            continue;  /* 这个元素已经用过了 */
        }

        /* 做选择 */
        used[i] = 1;
        path[depth] = nums[i];

        /* 递归深入 */
        backtrack(depth + 1);

        /* 撤销选择 */
        used[i] = 0;
    }
}

int main(void) {
    int data[] = {1, 2, 3};
    n = 3;

    for (int i = 0; i < n; i++) {
        nums[i] = data[i];
        used[i] = 0;
    }

    backtrack(0);
    return 0;
}
