#include <stdio.h>
#include <stdlib.h>

#define MAX_V 1000
#define INF 0x3f3f3f3f

/* 用邻接表存储图 */
typedef struct Node {
    int dest, weight;
    struct Node* next;
} Node;

void spfa(Node* graph[], int V, int src) {
    int dist[MAX_V];
    int inQueue[MAX_V];  /* 是否已经在队列中 */
    int count[MAX_V];    /* 入队次数，用于检测从源点可达的负权环 */
    
    int queue[MAX_V];
    int front = 0, rear = 0, qSize = 0;
    
    for (int i = 0; i < V; i++) {
        dist[i] = INF;
        inQueue[i] = 0;
        count[i] = 0;
    }
    dist[src] = 0;
    
    /* 起点入队 */
    queue[rear] = src;
    rear = (rear + 1) % MAX_V;
    qSize++;
    inQueue[src] = 1;
    count[src]++;
    
    while (qSize > 0) {
        int u = queue[front];
        front = (front + 1) % MAX_V;
        qSize--;
        inQueue[u] = 0;
        
        for (Node* p = graph[u]; p != NULL; p = p->next) {
            int v = p->dest;
            int w = p->weight;

            if (dist[u] != INF && dist[u] + w < dist[v]) {
                dist[v] = dist[u] + w;

                if (!inQueue[v]) {
                    queue[rear] = v;
                    rear = (rear + 1) % MAX_V;
                    qSize++;
                    inQueue[v] = 1;
                    count[v]++;

                    if (count[v] >= V) {
                        printf("存在从源点可达的负权环！\n");
                        return;
                    }
                }
            }
        }
    }
    
    for (int i = 0; i < V; i++) {
        if (dist[i] == INF)
            printf("到顶点 %d: 不可达\n", i);
        else
            printf("到顶点 %d: %d\n", i, dist[i]);
    }
}


Node* create_node(int dest, int weight) {
    Node* node = (Node*)malloc(sizeof(Node));
    if (node == NULL) {
        printf("内存分配失败\n");
        exit(1);
    }
    node->dest = dest;
    node->weight = weight;
    node->next = NULL;
    return node;
}

void add_edge(Node* graph[], int from, int dest, int weight) {
    Node* node = create_node(dest, weight);
    node->next = graph[from];
    graph[from] = node;
}

void free_graph(Node* graph[], int V) {
    for (int i = 0; i < V; i++) {
        Node* p = graph[i];
        while (p != NULL) {
            Node* next = p->next;
            free(p);
            p = next;
        }
    }
}

/* 测试：SPFA（Bellman-Ford 的队列优化版，可处理负权边） */
int main(void) {
    int V = 5;
    Node* graph[MAX_V] = {NULL};

    /* 与 Bellman-Ford 示例保持一致：有负权边，但没有负权环 */
    add_edge(graph, 0, 1, -1);
    add_edge(graph, 0, 2, 4);
    add_edge(graph, 1, 2, 3);
    add_edge(graph, 1, 3, 2);
    add_edge(graph, 1, 4, 2);
    add_edge(graph, 3, 2, 5);
    add_edge(graph, 3, 1, 1);
    add_edge(graph, 4, 3, -3);

    printf("SPFA 从顶点 0 出发的最短路径（含负权边）：\n\n");
    spfa(graph, V, 0);

    free_graph(graph, V);
    return 0;
}
