#include <stdio.h>

#define MAX_N 15

int n;
int pos[MAX_N];
int col_used[MAX_N];
int diag1_used[2 * MAX_N];   /* row - col + n */
int diag2_used[2 * MAX_N];   /* row + col */
int solution_count = 0;

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
        int d1 = row - col + n;
        int d2 = row + col;

        if (col_used[col] || diag1_used[d1] || diag2_used[d2]) {
            continue;
        }

        /* 做选择 */
        pos[row] = col;
        col_used[col] = 1;
        diag1_used[d1] = 1;
        diag2_used[d2] = 1;

        backtrack(row + 1);

        /* 撤销选择 */
        col_used[col] = 0;
        diag1_used[d1] = 0;
        diag2_used[d2] = 0;
    }
}

int main(void) {
    n = 4;
    backtrack(0);
    printf("总解数：%d\n", solution_count);
    return 0;
}
