#include <stdio.h>
#include <stdlib.h>

#define MAX_TREE_HT 256

/* 哈夫曼树节点 */
typedef struct MinHeapNode {
    char data;          /* 存字符（如果是内部节点，我们用 '$' 占位） */
    int freq;           /* 存频率 */
    struct MinHeapNode *left, *right;
} MinHeapNode;

/* 最小堆（用来每次快速找到频率最小的两个节点） */
typedef struct {
    int size;
    int capacity;
    MinHeapNode **array;
} MinHeap;

/* 创建新节点 */
MinHeapNode *new_node(char data, int freq) {
    MinHeapNode *node = (MinHeapNode *)malloc(sizeof(MinHeapNode));
    if (!node) return NULL;
    node->data = data;
    node->freq = freq;
    node->left = node->right = NULL;
    return node;
}

/* 创建最小堆 */
MinHeap *create_min_heap(int capacity) {
    MinHeap *heap = (MinHeap *)malloc(sizeof(MinHeap));
    if (!heap) return NULL;
    heap->size = 0;
    heap->capacity = capacity;
    heap->array = (MinHeapNode **)malloc(capacity * sizeof(MinHeapNode *));
    if (!heap->array) {
        free(heap);
        return NULL;
    }
    return heap;
}

void free_huffman_tree(MinHeapNode *root) {
    if (!root) return;
    free_huffman_tree(root->left);
    free_huffman_tree(root->right);
    free(root);
}

void free_min_heap(MinHeap *heap) {
    if (!heap) return;
    free(heap->array);
    free(heap);
}

/* 交换两个节点 */
void swap_nodes(MinHeapNode **a, MinHeapNode **b) {
    MinHeapNode *t = *a;
    *a = *b;
    *b = t;
}

/* 最小堆化 */
void min_heapify(MinHeap *heap, int idx) {
    int smallest = idx;
    int left = 2 * idx + 1;
    int right = 2 * idx + 2;

    if (left < heap->size &&
        heap->array[left]->freq < heap->array[smallest]->freq)
        smallest = left;

    if (right < heap->size &&
        heap->array[right]->freq < heap->array[smallest]->freq)
        smallest = right;

    if (smallest != idx) {
        swap_nodes(&heap->array[smallest], &heap->array[idx]);
        min_heapify(heap, smallest);
    }
}

/* 插入节点 */
int insert_min_heap(MinHeap *heap, MinHeapNode *node) {
    if (!heap || !node || heap->size >= heap->capacity) return 0;
    int i = heap->size++;
    heap->array[i] = node;

    /* 上浮 */
    while (i && node->freq < heap->array[(i - 1) / 2]->freq) {
        heap->array[i] = heap->array[(i - 1) / 2];
        i = (i - 1) / 2;
    }
    heap->array[i] = node;
    return 1;
}

/* 提取最小节点 */
MinHeapNode *extract_min(MinHeap *heap) {
    if (!heap || heap->size <= 0) return NULL;
    MinHeapNode *temp = heap->array[0];
    heap->array[0] = heap->array[--heap->size];
    if (heap->size > 0) min_heapify(heap, 0);
    return temp;
}

/* 构建哈夫曼树 */
MinHeapNode *build_huffman_tree(char data[], int freq[], int size) {
    MinHeap *heap = create_min_heap(size);
    if (!heap) return NULL;

    for (int i = 0; i < size; i++) {
        MinHeapNode *node = new_node(data[i], freq[i]);
        if (!insert_min_heap(heap, node)) {
            free_huffman_tree(node);
            for (int j = 0; j < heap->size; j++) free_huffman_tree(heap->array[j]);
            free_min_heap(heap);
            return NULL;
        }
    }

    /* 每次合并两个最小的 */
    while (heap->size > 1) {
        MinHeapNode *left = extract_min(heap);
        MinHeapNode *right = extract_min(heap);

        /* '$' 表示内部节点，不是叶子 */
        MinHeapNode *top = new_node('$', left->freq + right->freq);
        if (!top) {
            free_huffman_tree(left);
            free_huffman_tree(right);
            for (int j = 0; j < heap->size; j++) free_huffman_tree(heap->array[j]);
            free_min_heap(heap);
            return NULL;
        }
        top->left = left;
        top->right = right;

        if (!insert_min_heap(heap, top)) {
            free_huffman_tree(top);
            for (int j = 0; j < heap->size; j++) free_huffman_tree(heap->array[j]);
            free_min_heap(heap);
            return NULL;
        }
    }

    MinHeapNode *root = extract_min(heap);
    free_min_heap(heap);
    return root;
}

/* 打印编码（递归遍历） */
void print_codes(MinHeapNode *root, int arr[], int top) {
    if (!root) return;
    if (root->left) {
        arr[top] = 0;
        print_codes(root->left, arr, top + 1);
    }
    if (root->right) {
        arr[top] = 1;
        print_codes(root->right, arr, top + 1);
    }
    /* 叶子节点 */
    if (!root->left && !root->right) {
        printf("  %c: ", root->data);
        for (int i = 0; i < top; i++)
            printf("%d", arr[i]);
        printf("\n");
    }
}

int main(void) {
    char data[] = {'a', 'b', 'c', 'd', 'e', 'f'};
    int freq[] = {45, 13, 12, 16, 9, 5};
    int size = sizeof(data) / sizeof(data[0]);

    MinHeapNode *root = build_huffman_tree(data, freq, size);
    if (!root) {
        printf("构建哈夫曼树失败：内存不足。\n");
        return 1;
    }

    int arr[MAX_TREE_HT + 1], top = 0;
    printf("哈夫曼编码：\n");
    print_codes(root, arr, top);

    free_huffman_tree(root);
    return 0;
}
