#include <stdio.h>
#include <string.h>

#define MAXN 505  /* 每组最大节点数 */

int graph[MAXN][MAXN];  /* graph[u][v] = 1 表示学生 u 可以选课程 v */
int match[MAXN];        /* match[v] 表示课程 v 当前匹配到的学生编号 */
int used[MAXN];         /* 在一轮 DFS 中，课程 v 是否已经访问过 */
int n_left, n_right;    /* 左边学生数，右边课程数 */

/* DFS：尝试为学生 u 找到一门课程 */
int dfs(int u) {
    int v;

    for (v = 1; v <= n_right; v++) {
        if (graph[u][v] && !used[v]) {
            used[v] = 1;

            /* 如果课程 v 空着，或者当前占用 v 的学生还能改到别的课 */
            if (match[v] == 0 || dfs(match[v])) {
                match[v] = u;
                return 1;
            }
        }
    }

    return 0;
}

/* 匈牙利算法求最大匹配 */
int hungarian(void) {
    int u, count = 0;

    for (u = 1; u <= n_left; u++) {
        memset(used, 0, sizeof(used));
        if (dfs(u)) {
            count++;
        }
    }

    return count;
}

int main(void) {
    int m, u, v;

    memset(graph, 0, sizeof(graph));
    memset(match, 0, sizeof(match));

    printf("请输入学生数、课程数和可选关系数: ");
    scanf("%d %d %d", &n_left, &n_right, &m);

    printf("请输入每条可选关系(学生编号 课程编号):\n");
    for (int i = 0; i < m; i++) {
        scanf("%d %d", &u, &v);
        graph[u][v] = 1;
    }

    printf("最大匹配数: %d\n", hungarian());

    /* 输出匹配结果 */
    printf("匹配方案:\n");
    for (v = 1; v <= n_right; v++) {
        if (match[v] != 0) {
            printf("  学生%d <-> 课程%d\n", match[v], v);
        }
    }

    return 0;
}
