#include <stdio.h>

#define MAX_N 10

int n;
int nums[MAX_N];
int subset[MAX_N];   /* 当前子集里选了哪些元素 */
int size = 0;        /* 当前子集大小 */

void print_subset(void) {
    printf("{");
    for (int i = 0; i < size; i++) {
        if (i > 0) printf(", ");
        printf("%d", subset[i]);
    }
    printf("}\n");
}

void backtrack(int index) {
    if (index == n) {
        print_subset();
        return;
    }

    /* 分支1：不选 nums[index] */
    backtrack(index + 1);

    /* 分支2：选 nums[index] */
    subset[size++] = nums[index];
    backtrack(index + 1);
    size--;   /* 撤销选择 */
}

int main(void) {
    int data[] = {1, 2, 3};
    n = 3;

    for (int i = 0; i < n; i++) {
        nums[i] = data[i];
    }

    backtrack(0);
    return 0;
}
