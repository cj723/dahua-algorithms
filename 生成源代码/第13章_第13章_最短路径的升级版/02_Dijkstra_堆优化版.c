#include <stdio.h>
#include <stdlib.h>

#define MAX_V 1000
#define MAX_E 5000
#define INF 0x3f3f3f3f

/* 邻接表节点：只存真实存在的边，适合稀疏图 */
typedef struct EdgeNode {
    int to;
    int weight;
    struct EdgeNode* next;
} EdgeNode;

/* 最小堆节点：按当前距离排序 */
typedef struct {
    int vertex;
    int dist;
} HeapNode;

HeapNode heap[MAX_E + MAX_V];
int heapSize = 0;

void swap(HeapNode* a, HeapNode* b) {
    HeapNode t = *a;
    *a = *b;
    *b = t;
}

void push(int vertex, int dist) {
    if (heapSize >= MAX_E + MAX_V) {
        printf("堆空间不足\n");
        exit(1);
    }

    int i = heapSize++;
    heap[i].vertex = vertex;
    heap[i].dist = dist;

    while (i > 0) {
        int parent = (i - 1) / 2;
        if (heap[parent].dist <= heap[i].dist) break;
        swap(&heap[parent], &heap[i]);
        i = parent;
    }
}

HeapNode pop_min(void) {
    HeapNode ret = heap[0];
    heap[0] = heap[--heapSize];

    int i = 0;
    while (1) {
        int left = i * 2 + 1;
        int right = i * 2 + 2;
        int smallest = i;

        if (left < heapSize && heap[left].dist < heap[smallest].dist)
            smallest = left;
        if (right < heapSize && heap[right].dist < heap[smallest].dist)
            smallest = right;
        if (smallest == i) break;

        swap(&heap[i], &heap[smallest]);
        i = smallest;
    }

    return ret;
}

void add_edge(EdgeNode* graph[], int from, int to, int weight) {
    EdgeNode* node = (EdgeNode*)malloc(sizeof(EdgeNode));
    if (node == NULL) {
        printf("内存分配失败\n");
        exit(1);
    }
    node->to = to;
    node->weight = weight;
    node->next = graph[from];
    graph[from] = node;
}

void dijkstra_heap(EdgeNode* graph[], int V, int src) {
    int dist[MAX_V];
    int visited[MAX_V];

    for (int i = 0; i < V; i++) {
        dist[i] = INF;
        visited[i] = 0;
    }

    heapSize = 0;
    dist[src] = 0;
    push(src, 0);

    while (heapSize > 0) {
        HeapNode cur = pop_min();
        int u = cur.vertex;

        if (visited[u]) continue;  /* 堆里可能有旧距离，跳过即可 */
        visited[u] = 1;

        for (EdgeNode* e = graph[u]; e != NULL; e = e->next) {
            int v = e->to;
            int w = e->weight;
            if (!visited[v] && dist[u] != INF && dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;
                push(v, dist[v]);
            }
        }
    }

    printf("堆优化 Dijkstra 从顶点 %d 出发的最短距离：\n", src);
    for (int i = 0; i < V; i++) {
        if (dist[i] == INF)
            printf("到顶点 %d: 不可达\n", i);
        else
            printf("到顶点 %d: %d\n", i, dist[i]);
    }
}

void free_graph(EdgeNode* graph[], int V) {
    for (int i = 0; i < V; i++) {
        EdgeNode* p = graph[i];
        while (p != NULL) {
            EdgeNode* next = p->next;
            free(p);
            p = next;
        }
    }
}

/* 测试：稀疏图上的 Dijkstra 堆优化版 */
int main(void) {
    int V = 5;
    EdgeNode* graph[MAX_V] = {NULL};

    add_edge(graph, 0, 1, 10);
    add_edge(graph, 0, 2, 3);
    add_edge(graph, 1, 2, 1);
    add_edge(graph, 1, 3, 2);
    add_edge(graph, 2, 1, 4);
    add_edge(graph, 2, 3, 8);
    add_edge(graph, 2, 4, 2);
    add_edge(graph, 3, 4, 7);
    add_edge(graph, 4, 3, 9);

    printf("稀疏图：5 个顶点，9 条有向边\n");
    dijkstra_heap(graph, V, 0);

    free_graph(graph, V);
    return 0;
}
