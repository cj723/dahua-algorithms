#include <stdio.h>
#include <string.h>

#define MAXN 10005   /* 最大节点数 */
#define MAXM 100005  /* 最大边数 */

/* 邻接表的边结构 */
typedef struct {
    int to;    /* 边的终点 */
    int next;  /* 同一起点的下一条边 */
} Edge;

Edge edges[MAXM];    /* 边数组 */
int head[MAXN];      /* head[i]表示以i为起点的第一条边的编号 */
int edge_count = 0;  /* 边的计数器 */

int dfn[MAXN];       /* 时间戳数组 */
int low[MAXN];       /* low 值数组 */
int stack[MAXN];     /* 栈 */
int in_stack[MAXN];  /* 标记节点是否在栈中 */
int top = -1;        /* 栈顶指针 */
int timestamp = 0;   /* 时间戳计数器 */
int scc_count = 0;   /* 强连通分量计数 */
int scc_id[MAXN];    /* 每个节点所属的强连通分量编号 */

/* 添加一条从 u 到 v 的有向边 */
void add_edge(int u, int v) {
    edges[edge_count].to = v;
    edges[edge_count].next = head[u];
    head[u] = edge_count;
    edge_count++;
}

/* Tarjan 算法核心 */
void tarjan(int u) {
    int i, v;

    /* 第一步：给 u 打上时间戳，初始化 low 值 */
    dfn[u] = low[u] = ++timestamp;

    /* 第二步：将 u 压入栈中，标记 u 在栈里 */
    stack[++top] = u;
    in_stack[u] = 1;

    /* 第三步：遍历 u 的所有邻居 */
    for (i = head[u]; i != -1; i = edges[i].next) {
        v = edges[i].to;

        if (dfn[v] == 0) {
            /* 如果 v 还没被访问过，递归访问 */
            tarjan(v);
            /* 回溯后，用 v 的 low 值更新 u 的 low 值 */
            if (low[v] < low[u]) {
                low[u] = low[v];
            }
        } else if (in_stack[v]) {
            /* 如果 v 已被访问且还在栈中（是 u 的祖先） */
            /* 说明发现了一条返祖边 */
            /* 不在栈中的 v 属于已完成 SCC，不能用于更新 low[u] */
            /* 易错点：栈中节点应取 min(low[u], dfn[v])，而非 min(low[u], low[v]) */
            if (dfn[v] < low[u]) {
                low[u] = dfn[v];
            }
        }
    }

    /* 第四步：如果 u 是强连通分量的根 */
    if (dfn[u] == low[u]) {
        scc_count++;
        printf("强连通分量 #%d: ", scc_count);
        do {
            v = stack[top--];
            in_stack[v] = 0;
            scc_id[v] = scc_count;
            printf("%d ", v);
        } while (v != u);
        printf("\n");
    }
}

int main(void) {
    int n, m, u, v;

    /* 初始化 */
    memset(head, -1, sizeof(head));
    memset(dfn, 0, sizeof(dfn));
    memset(low, 0, sizeof(low));
    memset(in_stack, 0, sizeof(in_stack));

    printf("请输入节点数和边数: ");
    scanf("%d %d", &n, &m);

    printf("请输入每条边(起点 终点):\n");
    for (int i = 0; i < m; i++) {
        scanf("%d %d", &u, &v);
        add_edge(u, v);
    }

    /* 对每个未访问的节点运行 Tarjan */
    for (int i = 1; i <= n; i++) {
        if (dfn[i] == 0) {
            tarjan(i);
        }
    }

    printf("共找到 %d 个强连通分量\n", scc_count);

    return 0;
}
