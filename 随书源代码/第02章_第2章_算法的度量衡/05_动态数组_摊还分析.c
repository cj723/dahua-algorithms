#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int *data;     // 实际存储数据的数组
    int size;      // 当前元素个数
    int capacity;  // 当前容量
} DynamicArray;

/* 创建动态数组 */
DynamicArray* create_array(int initial_capacity) {
    DynamicArray *arr = (DynamicArray *)malloc(sizeof(DynamicArray));
    if (arr == NULL) {
        return NULL;
    }

    arr->data = (int *)malloc(initial_capacity * sizeof(int));
    if (arr->data == NULL) {
        free(arr);
        return NULL;
    }

    arr->size = 0;
    arr->capacity = initial_capacity;
    return arr;
}

/* 添加元素（核心） */
void push_back(DynamicArray *arr, int value) {
    /* 如果满了，翻倍扩容 */
    if (arr->size == arr->capacity) {
        int new_capacity = arr->capacity * 2;  /* 容量翻倍 */
        int *temp = (int *)realloc(arr->data, new_capacity * sizeof(int));
        if (temp == NULL) {
            printf("  扩容失败：内存不足！\n");
            return;
        }
        arr->data = temp;  /* 确认成功后再赋值 */
        arr->capacity = new_capacity;
        printf("  扩容：新容量：%d\n", arr->capacity);
    }
    arr->data[arr->size++] = value;
}

/* 销毁 */
void destroy_array(DynamicArray *arr) {
    if (arr == NULL) {
        return;
    }
    free(arr->data);
    free(arr);
}


int main(void) {
    DynamicArray *arr = create_array(2);  /* 初始容量 2 */
    if (arr == NULL) {
        printf("创建动态数组失败！\n");
        return 1;
    }

    printf("往动态数组里塞 10 个元素：\n");
    for (int i = 1; i <= 10; i++) {
        printf("添加 %d → ", i);
        push_back(arr, i);
        printf("size=%d, capacity=%d\n", arr->size, arr->capacity);
    }
    destroy_array(arr);
    return 0;
}
