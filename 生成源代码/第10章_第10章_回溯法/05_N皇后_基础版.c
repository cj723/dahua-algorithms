#include <stdio.h>

#define MAX_N 15

int n;
int pos[MAX_N];   /* pos[row] = col 表示第 row 行的皇后放在第 col 列 */
int solution_count = 0;

int is_valid(int row, int col) {
    for (int prev = 0; prev < row; prev++) {
        int prev_col = pos[prev];

        /* 不需要检查同一行：回溯函数每次只在当前 row 放一个皇后 */

        /* 同列冲突 */
        if (prev_col == col) {
            return 0;
        }

        /* 对角线冲突：行差绝对值 == 列差绝对值 */
        int row_diff = row - prev;
        int col_diff = col - prev_col;
        if (col_diff < 0) col_diff = -col_diff;
        if (row_diff == col_diff) {
            return 0;
        }
    }
    return 1;
}

void print_board(void) {
    printf("第 %d 组解：\n", solution_count);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (pos[i] == j) printf("Q ");
            else printf(". ");
        }
        printf("\n");
    }
    printf("\n");
}

void backtrack(int row) {
    if (row == n) {
        solution_count++;
        print_board();
        return;
    }

    for (int col = 0; col < n; col++) {
        if (!is_valid(row, col)) {
            continue;
        }

        pos[row] = col;        /* 做选择 */
        backtrack(row + 1);    /* 递归到下一行 */
        /* 这里不需要显式撤销 pos[row]，因为下一次会被新值覆盖 */
    }
}

int main(void) {
    n = 4;
    backtrack(0);
    printf("总解数：%d\n", solution_count);
    return 0;
}
