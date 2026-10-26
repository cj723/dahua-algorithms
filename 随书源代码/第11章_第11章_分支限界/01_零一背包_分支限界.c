#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ITEMS 100

/* 物品结构体 */
typedef struct {
    int id;           /* 物品编号 */
    double weight;    /* 重量 */
    double value;     /* 价值 */
    double ratio;     /* 单位价值 = value / weight */
} Item;

/* 搜索节点（核心状态） */
typedef struct {
    int level;          /* 当前决策到第几个物品（走到了决策树的哪一层） */
    double weight;      /* 当前已装重量 */
    double value;       /* 当前已装价值 */
    double ub;          /* 上界（Upper Bound），即当前路径的"最大潜力" */
    int selected[MAX_ITEMS];  /* 记录当前路径上选了哪些物品 */
} Node;

/* 优先队列（最大堆，按ub排序） */
typedef struct {
    Node *data[MAX_ITEMS * MAX_ITEMS];
    int size;
} PriorityQueue;

/* 比较函数：按单位价值降序排列 */
int cmp_ratio(const void *a, const void *b) {
    Item *ia = (Item *)a;
    Item *ib = (Item *)b;
    if (ib->ratio > ia->ratio) return 1;
    if (ib->ratio < ia->ratio) return -1;
    return 0;
}

/* 交换两个整数 */
void swap(int *a, int *b) {
    int t = *a; *a = *b; *b = t;
}

/* ===== 优先队列操作 ===== */

void pq_init(PriorityQueue *pq) {
    pq->size = 0;
}

/* 上浮操作 */
void pq_swim(PriorityQueue *pq, int k) {
    while (k > 0) {
        int parent = (k - 1) / 2;
        if (pq->data[parent]->ub < pq->data[k]->ub) {
            Node *tmp = pq->data[parent];
            pq->data[parent] = pq->data[k];
            pq->data[k] = tmp;
            k = parent;
        } else {
            break;
        }
    }
}

/* 下沉操作 */
void pq_sink(PriorityQueue *pq, int k) {
    while (2 * k + 1 < pq->size) {
        int child = 2 * k + 1;
        if (child + 1 < pq->size && 
            pq->data[child + 1]->ub > pq->data[child]->ub) {
            child++;
        }
        if (pq->data[k]->ub < pq->data[child]->ub) {
            Node *tmp = pq->data[k];
            pq->data[k] = pq->data[child];
            pq->data[child] = tmp;
            k = child;
        } else {
            break;
        }
    }
}

void pq_push(PriorityQueue *pq, Node *node) {
    if (pq->size >= MAX_ITEMS * MAX_ITEMS) {
        printf("优先队列溢出！节点数超过上限。\n");
        free(node);
        return;
    }
    pq->data[pq->size] = node;
    pq_swim(pq, pq->size);
    pq->size++;
}

Node *pq_pop(PriorityQueue *pq) {
    Node *top = pq->data[0];
    pq->size--;
    pq->data[0] = pq->data[pq->size];
    pq_sink(pq, 0);
    return top;
}

int pq_empty(PriorityQueue *pq) {
    return pq->size == 0;
}

/* ===== 限界函数：计算上界 ===== */
/*
 * 核心思想：只为估算上界时，允许把装不下的物品按比例"切开"。
 * 注意：物品必须已经按单位价值从高到低排序。
 */
double calc_ub(int n, Item items[], int level, double cur_weight, 
               double cur_value, double capacity) {
    double remain = capacity - cur_weight;
    double ub = cur_value;
    
    /* 贪心地从当前物品开始往后装（前提：物品已按单位价值降序排好） */
    for (int i = level; i < n; i++) {
        if (remain <= 0) break; /* 背包满了，结束 */
        if (items[i].weight <= remain) {
            /* 整个装得下 */
            ub += items[i].value;
            remain -= items[i].weight;
        } else {
            /* 整个装不下，就按比例切开，只为估算上界 */
            ub += items[i].value * (remain / items[i].weight);
            remain = 0;
        }
    }
    return ub;
}

/* ===== 主算法 ===== */
int knapsack_bb(int n, Item items[], double capacity, 
                int best_selected[]) {
    PriorityQueue pq;
    pq_init(&pq);
    
    double best_value = 0;  /* 当前已经找到的真实最优解 */
    
    /* 1. 初始化根节点（什么都还没装） */
    Node *root = (Node *)calloc(1, sizeof(Node));
    if (root == NULL) {
        return 0;
    }
    root->level = 0;
    root->weight = 0;
    root->value = 0;
    root->ub = calc_ub(n, items, 0, 0, 0, capacity);
    pq_push(&pq, root);
    
    /* 2. 只要队列不空，就一直探索 */
    while (!pq_empty(&pq)) {
        Node *cur = pq_pop(&pq); /* 永远先看"上界最大"的节点 */
        
        /* [核心剪枝]：如果这个节点理论上的最好结果，都不如当前最优解，直接丢掉 */
        if (cur->ub <= best_value) {
            free(cur);
            continue;
        }
        
        /* 所有物品都已经决策完了 */
        if (cur->level == n) {
            if (cur->value > best_value) {
                best_value = cur->value;
                memcpy(best_selected, cur->selected, n * sizeof(int));
            }
            free(cur);
            continue;
        }
        
        int i = cur->level; /* 准备决策第 i 个物品 */
        
        /* ===== 分支 A：选择第 i 个物品（前提是装得下） ===== */
        if (cur->weight + items[i].weight <= capacity) {
            Node *yes = (Node *)malloc(sizeof(Node));
            if (yes == NULL) {
                free(cur);
                break;
            }
            memcpy(yes, cur, sizeof(Node));
            yes->level = cur->level + 1;
            yes->weight = cur->weight + items[i].weight;
            yes->value = cur->value + items[i].value;
            yes->selected[i] = 1;
            yes->ub = calc_ub(n, items, yes->level, 
                             yes->weight, yes->value, capacity);
            
            /* 只有"理论最好成绩"仍有希望超过当前最优解，才继续探索 */
            if (yes->ub > best_value) {
                pq_push(&pq, yes);
            } else {
                free(yes);
            }
        }
        
        /* ===== 分支 B：不选择第 i 个物品 ===== */
        Node *no = (Node *)malloc(sizeof(Node));
        if (no == NULL) {
            free(cur);
            break;
        }
        memcpy(no, cur, sizeof(Node));
        no->level = cur->level + 1;
        no->selected[i] = 0;
        no->ub = calc_ub(n, items, no->level, 
                         no->weight, no->value, capacity);
        
        if (no->ub > best_value) {
            pq_push(&pq, no);
        } else {
            free(no);
        }
        
        free(cur); /* 当前节点使命完成 */
    }
    
    /* 清空优先队列中残留的节点（防内存泄漏） */
    while (!pq_empty(&pq)) {
        free(pq_pop(&pq));
    }
    
    return (int)best_value;
}

/* 工程注意：优先队列生产环境建议用堆替代定长数组 */

/* ===== 主函数 ===== */
int main(void) {
    int n = 4;
    Item items[] = {
        {1, 2, 10, 0},
        {2, 4, 10, 0},
        {3, 6, 12, 0},
        {4, 9, 18, 0}
    };
    double capacity = 15;
    
    /* 计算单位价值并排序 */
    for (int i = 0; i < n; i++) {
        items[i].ratio = items[i].value / items[i].weight;
    }
    qsort(items, n, sizeof(Item), cmp_ratio);
    
    printf("按单位价值排序后的物品：\n");
    printf("%-6s %-8s %-8s %-10s\n", "编号", "重量", "价值", "单价");
    for (int i = 0; i < n; i++) {
        printf("%-6d %-8.0f %-8.0f %-10.2f\n", 
               items[i].id, items[i].weight, 
               items[i].value, items[i].ratio);
    }
    printf("\n");
    
    int best_selected[MAX_ITEMS] = {0};
    int max_val = knapsack_bb(n, items, capacity, best_selected);
    
    printf("最优解：\n");
    printf("最大价值：%d 万元\n", max_val);
    printf("选择的物品：");
    double total_weight = 0;
    for (int i = 0; i < n; i++) {
        if (best_selected[i]) {
            printf("物品%d(%.0fkg, %.0f万) ", 
                   items[i].id, items[i].weight, items[i].value);
            total_weight += items[i].weight;
        }
    }
    printf("\n总重量：%.0f kg / %.0f kg\n", total_weight, capacity);
    
    return 0;
}
