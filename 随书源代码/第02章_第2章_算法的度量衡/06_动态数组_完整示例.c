#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int *data;     // 实际存储数据的数组
    int size;      // 当前元素个数
    int capacity;  // 当前容量
} DynamicArray;

// 创建动态数组
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

// 添加元素：满了就翻倍扩容
int push_back(DynamicArray *arr, int value) {
    if (arr->size == arr->capacity) {
        int new_capacity = arr->capacity * 2;
        int *temp = (int *)realloc(arr->data, new_capacity * sizeof(int));
        if (temp == NULL) {
            return 0;
        }
        arr->data = temp;
        arr->capacity = new_capacity;
        printf("  扩容：capacity -> %d\n", arr->capacity);
    }

    arr->data[arr->size] = value;
    arr->size++;
    return 1;
}

// 打印动态数组当前状态
void print_array(DynamicArray *arr) {
    printf("data = [");
    for (int i = 0; i < arr->size; i++) {
        printf("%d", arr->data[i]);
        if (i + 1 < arr->size) {
            printf(", ");
        }
    }
    printf("], size=%d, capacity=%d\n", arr->size, arr->capacity);
}

// 销毁动态数组
void destroy_array(DynamicArray *arr) {
    if (arr == NULL) {
        return;
    }
    free(arr->data);
    free(arr);
}

int main(void) {
    DynamicArray *arr = create_array(2);
    if (arr == NULL) {
        printf("创建动态数组失败\n");
        return 1;
    }

    printf("动态数组完整示例：\n");
    for (int i = 1; i <= 10; i++) {
        printf("添加 %d：", i);
        if (!push_back(arr, i)) {
            printf("扩容失败\n");
            destroy_array(arr);
            return 1;
        }
        print_array(arr);
    }

    destroy_array(arr);
    return 0;
}
