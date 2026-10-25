/* 单调栈：下一个更大元素 */
/* 类比：排队时等待右边第一个比自己高的人 */
#include <stdio.h>

#define MAXN 1000

/* 找每个元素右边第一个比它大的元素 */
/* 结果存入result数组 */
void next_greater_element(int nums[], int n, int result[]) {
    int stack[MAXN];    /* 栈，存放下标（不是存值！） */
    int top = -1;       /* 栈顶指针，-1表示栈空 */

    /* 示例代码用固定数组，真实工程中可改成动态分配 */
    if (n > MAXN) {
        return;
    }
    
    /* 初始化结果数组为-1 */
    for (int i = 0; i < n; i++) {
        result[i] = -1;
    }
    
    /* 从左往右遍历：当前元素可能成为前面某些元素的答案 */
    for (int i = 0; i < n; i++) {
        /* 当前元素比栈顶元素更大时，栈顶元素的答案就是当前元素 */
        while (top >= 0 && nums[i] > nums[stack[top]]) {
            result[stack[top]] = nums[i];
            top--;  /* 栈顶元素已经找到答案，弹出 */
        }
        
        /* 当前下标入栈，等待未来更大的元素 */
        top++;
        stack[top] = i;
    }
}

int main() {
    int nums[] = {2, 1, 2, 4, 3};
    int n = 5;
    int result[5];
    
    next_greater_element(nums, n, result);
    
    printf("下一个更大元素：\n");
    for (int i = 0; i < n; i++) {
        printf("nums[%d]=%d -> %d\n", i, nums[i], result[i]);
    }
    
    return 0;
}
