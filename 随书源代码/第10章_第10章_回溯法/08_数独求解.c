#include <stdio.h>

#define N 9

typedef int bool;
#define true 1
#define false 0

int board[N][N];

bool is_valid(int row, int col, int num) {
    /* 检查行 */
    for (int j = 0; j < N; j++) {
        if (board[row][j] == num) {
            return false;
        }
    }

    /* 检查列 */
    for (int i = 0; i < N; i++) {
        if (board[i][col] == num) {
            return false;
        }
    }

    /* 检查 3×3 小宫格 */
    int start_row = (row / 3) * 3;
    int start_col = (col / 3) * 3;
    for (int i = start_row; i < start_row + 3; i++) {
        for (int j = start_col; j < start_col + 3; j++) {
            if (board[i][j] == num) {
                return false;
            }
        }
    }

    return true;
}

bool solve_sudoku(void) {
    /* 先找一个空格 */
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (board[i][j] != 0) {
                continue;
            }

            /* 尝试填 1 ~ 9 */
            for (int num = 1; num <= 9; num++) {
                if (!is_valid(i, j, num)) {
                    continue;
                }

                board[i][j] = num;   /* 做选择 */

                if (solve_sudoku()) {
                    return true;      /* 找到一个可行解 */
                }

                board[i][j] = 0;     /* 撤销选择 */
            }

            /* 这个空格 1 ~ 9 都试过了，说明当前分支走不通 */
            return false;
        }
    }

    /* 没有空格了，说明填完了 */
    return true;
}

void print_board(void) {
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            printf("%d ", board[i][j]);
        }
        printf("\n");
    }
}

int main(void) {
    int puzzle[N][N] = {
        {5,3,0, 0,7,0, 0,0,0},
        {6,0,0, 1,9,5, 0,0,0},
        {0,9,8, 0,0,0, 0,6,0},

        {8,0,0, 0,6,0, 0,0,3},
        {4,0,0, 8,0,3, 0,0,1},
        {7,0,0, 0,2,0, 0,0,6},

        {0,6,0, 0,0,0, 2,8,0},
        {0,0,0, 4,1,9, 0,0,5},
        {0,0,0, 0,8,0, 0,7,9}
    };

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            board[i][j] = puzzle[i][j];
        }
    }

    if (solve_sudoku()) {
        printf("解出的数独：\n");
        print_board();
    } else {
        printf("无解！\n");
    }

    return 0;
}
