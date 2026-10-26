#include <stdio.h>
#include <string.h>

#define MAX_LEN 1000

int max(int a, int b) {
    return a > b ? a : b;
}

int lcs_restore(const char *X, const char *Y, char result[]) {
    int m = (int)strlen(X);
    int n = (int)strlen(Y);
    int dp[MAX_LEN + 1][MAX_LEN + 1] = {0};

    if (m > MAX_LEN || n > MAX_LEN) {
        return -1;
    }

    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (X[i - 1] == Y[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    int i = m;
    int j = n;
    int len = dp[m][n];
    int pos = len;
    result[pos] = '\0';

    while (i > 0 && j > 0) {
        if (X[i - 1] == Y[j - 1]) {
            result[--pos] = X[i - 1];
            i--;
            j--;
        } else if (dp[i - 1][j] >= dp[i][j - 1]) {
            i--;
        } else {
            j--;
        }
    }

    return len;
}

int main(void) {
    char X[] = "ABCB";
    char Y[] = "BDCAB";
    char result[MAX_LEN + 1];

    int len = lcs_restore(X, Y, result);
    if (len < 0) {
        printf("字符串过长\n");
        return 1;
    }

    printf("LCS 长度：%d\n", len);
    printf("一种 LCS：%s\n", result);
    return 0;
}
