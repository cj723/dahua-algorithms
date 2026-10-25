#include <stdio.h>
#include <stdlib.h>

/* 链表节点（每个桶用链表存储） */
typedef struct Node {
    double value;
    struct Node *next;
} Node;

/* 创建新节点 */
Node* create_node(double value) {
    Node *node = (Node *)malloc(sizeof(Node));
    if (!node) return NULL;
    node->value = value;
    node->next = NULL;
    return node;
}

/* 在有序链表中插入节点（插入排序的思想） */
int insert_sorted(Node **head, double value) {
    Node *new_node = create_node(value);
    if (!new_node) return 0;
    
    /* 空表或插入到表头 */
    if (*head == NULL || (*head)->value >= value) {
        new_node->next = *head;
        *head = new_node;
        return 1;
    }
    
    /* 找到插入位置 */
    Node *current = *head;
    while (current->next != NULL && current->next->value < value) {
        current = current->next;
    }
    
    new_node->next = current->next;
    current->next = new_node;
    return 1;
}

/*
 * 桶排序
 * arr：待排序数组（主要面向 [0, 1) 区间；下方对 bucketIndex 的越界回填即为对 1.0 的容错处理）
 * n：数组长度
 */
int bucket_sort(double arr[], int n) {
    /* 创建 n 个空桶（用链表实现） */
    Node **buckets = (Node **)calloc(n, sizeof(Node *));
    if (!buckets) return 0;
    
    /* 第一步：分桶 */
    /* 就像水果摊老板把水果分到不同筐里 */
    for (int i = 0; i < n; i++) {
        if (arr[i] < 0.0 || arr[i] > 1.0) {
            free(buckets);
            return 0;
        }
        int bucketIndex = (int)(n * arr[i]);
        /* 边界处理：如果 arr[i] 刚好等于 1.0，放到最后一个桶 */
        if (bucketIndex >= n) {
            bucketIndex = n - 1;
        }
        if (!insert_sorted(&buckets[bucketIndex], arr[i])) {
            for (int j = 0; j < n; j++) {
                Node *current = buckets[j];
                while (current != NULL) {
                    Node *temp = current;
                    current = current->next;
                    free(temp);
                }
            }
            free(buckets);
            return 0;
        }
    }
    
    /* 第二步：按桶的顺序合并 */
    int idx = 0;
    for (int i = 0; i < n; i++) {
        Node *current = buckets[i];
        while (current != NULL) {
            arr[idx++] = current->value;
            Node *temp = current;
            current = current->next;
            free(temp);
        }
    }
    
    free(buckets);
    return 1;
}

int main(void) {
    double arr[] = {0.42, 0.32, 0.23, 0.52, 0.25, 0.47, 0.51, 0.56, 0.08, 0.36};
    int n = sizeof(arr) / sizeof(arr[0]);
    
    printf("原始数组：");
    for (int i = 0; i < n; i++) {
        printf("%.2f ", arr[i]);
    }
    printf("\n");
    
    if (!bucket_sort(arr, n)) {
        printf("排序失败：输入必须在 0 到 1 之间，或内存不足。\n");
        return 1;
    }
    
    printf("排序结果：");
    for (int i = 0; i < n; i++) {
        printf("%.2f ", arr[i]);
    }
    printf("\n");
    
    return 0;
}
