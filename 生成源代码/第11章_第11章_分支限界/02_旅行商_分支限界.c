#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_N 20
#define INF 1000000000.0

int n;                          /* 城市数量 */
double dist[MAX_N][MAX_N];      /* 距离矩阵 */

/* 搜索节点（核心状态） */
typedef struct {
    int level;                  /* 已访问的城市数 */
    int path[MAX_N];            /* 当前路线，例如 0 -> 3 -> 2 */
    int visited[MAX_N];         /* visited[i] = 1 表示城市 i 已访问 */
    double cost;                /* 当前已经走过的真实距离 */
    double lb;                  /* 理论下界（Lower Bound） */
} Node;

/* 优先队列（最小堆，按下界排序——TSP求最小值） */
typedef struct {
    Node *data[100000];
    int size;
} PriorityQueue;

PriorityQueue pq;

/* ===== 优先队列操作 ===== */

void pq_init(PriorityQueue *p) { p->size = 0; }

void pq_swim(PriorityQueue *p, int k) {
    while (k > 0) {
        int parent = (k - 1) / 2;
        if (p->data[parent]->lb > p->data[k]->lb) {
            Node *tmp = p->data[parent];
            p->data[parent] = p->data[k];
            p->data[k] = tmp;
            k = parent;
        } else break;
    }
}

void pq_sink(PriorityQueue *p, int k) {
    while (2 * k + 1 < p->size) {
        int child = 2 * k + 1;
        if (child + 1 < p->size && 
            p->data[child + 1]->lb < p->data[child]->lb)
            child++;
        if (p->data[k]->lb > p->data[child]->lb) {
            Node *tmp = p->data[k];
            p->data[k] = p->data[child];
            p->data[child] = tmp;
            k = child;
        } else break;
    }
}

void pq_push(PriorityQueue *p, Node *node) {
    if (p->size >= 100000) {
        printf("TSP优先队列溢出！\n");
        free(node);
        return;
    }
    p->data[p->size] = node;
    pq_swim(p, p->size);
    p->size++;
}

Node *pq_pop(PriorityQueue *p) {
    Node *top = p->data[0];
    p->size--;
    p->data[0] = p->data[p->size];
    pq_sink(p, 0);
    return top;
}

int pq_empty(PriorityQueue *p) { return p->size == 0; }

int path_less(int a[], int b[], int len) {
    for (int i = 0; i < len; i++) {
        if (a[i] != b[i]) return a[i] < b[i];
    }
    return 0;
}

/* 返回城市 city 连接到其他城市的 k 条最短边之和。
 * 为了让下界足够乐观，这里不强行排除已经访问过的城市；
 * 这样算出的值可能偏小，但不会偏大，适合做安全下界。
 */
double sum_k_min_edges(int city, int k) {
    double first = INF, second = INF;

    for (int j = 0; j < n; j++) {
        if (j == city) continue;

        if (dist[city][j] < first) {
            second = first;
            first = dist[city][j];
        } else if (dist[city][j] < second) {
            second = dist[city][j];
        }
    }

    if (k == 1) return first;
    if (k == 2) return first + second;

    return INF;
}

/* ===== 下界计算 ===== */
double calc_lb(Node *node) {
    /* 如果已经访问完所有城市，下界就是当前路径 + 回到起点的真实代价 */
    if (node->level == n) {
        int last = node->path[n - 1];
        return node->cost + dist[last][0];
    }

    double extra = 0.0;

    if (node->level == 1) {
        /* 根节点：起点还需要两条边接入最终回路 */
        extra += sum_k_min_edges(0, 2);
    } else {
        /* 已经走出起点：起点还需要最后一条边回收成环 */
        extra += sum_k_min_edges(0, 1);

        /* 当前路径末尾还需要继续连向后面的城市 */
        int last = node->path[node->level - 1];
        extra += sum_k_min_edges(last, 1);
    }

    /* 每个未访问城市未来都需要两条边接入回路 */
    for (int i = 0; i < n; i++) {
        if (!node->visited[i]) {
            extra += sum_k_min_edges(i, 2);
        }
    }

    /* 从城市视角统计边会重复计数，因此除以 2 */
    return node->cost + extra / 2.0;
}

/* ===== 分支限界求解 TSP =====
 * 返回最短回路长度，并通过 best_path[] 保存一种最优访问顺序。
 * best_path 中只保存 A 到其他城市的访问顺序，最后回到 A 可在输出时补上。
 */
double tsp_bb(int best_path[]) {
    pq_init(&pq);

    double best_cost = INF;   /* 当前找到的最短回路长度 */

    /* 1. 初始化根节点：从城市 0，也就是 A 出发 */
    Node *root = (Node *)calloc(1, sizeof(Node));
    if (root == NULL) {
        return INF;
    }

    root->level = 1;
    root->path[0] = 0;
    root->visited[0] = 1;
    root->cost = 0.0;
    root->lb = calc_lb(root);
    pq_push(&pq, root);

    /* 2. 只要队列不空，就不断探索 */
    while (!pq_empty(&pq)) {
        Node *cur = pq_pop(&pq); /* 取出 lb 最小的节点 */

        /* 核心剪枝：理论下界都不优于当前最优解，直接放弃 */
        if (cur->lb >= best_cost) {
            free(cur);
            continue;
        }

        /* 所有城市都已经访问完：检查回到起点后的完整回路长度 */
        if (cur->level == n) {
            int last = cur->path[n - 1];
            double total = cur->cost + dist[last][0];

            if (total < best_cost ||
                (total == best_cost && path_less(cur->path, best_path, n))) {
                best_cost = total;
                memcpy(best_path, cur->path, n * sizeof(int));
            }

            free(cur);
            continue;
        }

        /* 扩展：尝试走向每一个尚未访问的城市 */
        int last = cur->path[cur->level - 1];

        for (int next = 0; next < n; next++) {
            if (cur->visited[next]) continue;
            if (dist[last][next] >= INF) continue; /* 非完全图时可用 */

            Node *child = (Node *)malloc(sizeof(Node));
            if (child == NULL) {
                /* 教学代码中直接跳过；工业代码应释放队列中剩余节点 */
                continue;
            }

            memcpy(child, cur, sizeof(Node));

            child->path[cur->level] = next;
            child->visited[next] = 1;
            child->level = cur->level + 1;
            child->cost = cur->cost + dist[last][next];
            child->lb = calc_lb(child);

            /* 只有下界仍然有希望优于当前最优解，才入队 */
            if (child->lb < best_cost) {
                pq_push(&pq, child);
            } else {
                free(child);
            }
        }

        free(cur);
    }

    /* 清空优先队列中残留的节点（防内存泄漏） */
    while (!pq_empty(&pq)) {
        free(pq_pop(&pq));
    }

    return best_cost;
}

/* ===== 主函数 ===== */
int main(void) {
    n = 5;
    
    double example[5][5] = {
        {0, 3, 6, 2, 7},
        {3, 0, 4, 9, 3},
        {6, 4, 0, 5, 8},
        {2, 9, 5, 0, 6},
        {7, 3, 8, 6, 0}
    };
    
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            dist[i][j] = example[i][j];
    
    int best_path[MAX_N] = {0};
    double best_cost = tsp_bb(best_path);
    
    printf("TSP最优路径：");
    for (int i = 0; i < n; i++) {
        printf("%c -> ", 'A' + best_path[i]);
    }
    printf("%c\n", 'A' + best_path[0]);
    printf("最短距离：%.0f\n", best_cost);
    
    return 0;
}
