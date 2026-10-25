#include <stdio.h>

/* 原地反转数组：空间复杂度 O(1) */
void reverse_array(int arr[], int n) {
    int left = 0, right = n - 1;
    while (left < right) {
        int temp = arr[left];
        arr[left] = arr[right];
        arr[right] = temp;
        left++;
        right--;
    }
}


/* ===== 自动生成的测试入口 ===== */
#define N 9
int main(void) {
    int d[N] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int i;

    printf("=== reverse_array ===\n");
    {
        int arr[N];
        for (i = 0; i < N; i++) arr[i] = d[i];
        printf("反转前: ");
        for (i = 0; i < N; i++) printf("%d ", arr[i]);
        printf("\n");
        reverse_array(arr, N);
        printf("反转后: ");
        for (i = 0; i < N; i++) printf("%d ", arr[i]);
        printf("\n");
    }

    return 0;
}
