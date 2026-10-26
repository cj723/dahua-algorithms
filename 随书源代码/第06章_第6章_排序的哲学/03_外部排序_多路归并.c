/* 外部排序 多路归并 */
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>

#define MEMORY_SIZE 10  // 内存一次只能放10个元素

// 比较函数
int cmp(const void *a, const void *b) {
    int x = *(const int *)a;
    int y = *(const int *)b;
    return (x > y) - (x < y);
}

/*
 * 步骤1：生成初始归并段
 * 每次从大文件读MEMORY_SIZE个数，排序后写入一个小文件
 */
int create_runs(const char *inputFile, char runFiles[][50], int maxRuns) {
    FILE *fin = fopen(inputFile, "r");
    if (!fin) return -1;
    int buffer[MEMORY_SIZE];
    int runCount = 0;

    while (!feof(fin) && runCount < maxRuns) {
        int count = 0;
        // 读一批数据到内存
        while (count < MEMORY_SIZE && fscanf(fin, "%d", &buffer[count]) == 1) {
            count++;
        }
        if (count == 0) break;

        // 内部排序
        qsort(buffer, count, sizeof(int), cmp);

        // 写入临时文件
        FILE *frun = fopen(runFiles[runCount], "w");
        if (!frun) {
            fclose(fin);
            return -1;
        }
        for (int i = 0; i < count; i++) {
            fprintf(frun, "%d\n", buffer[i]);
        }
        fclose(frun);
        runCount++;
    }
    fclose(fin);
    return runCount;
}

/*
 * 步骤2：二路归并（简化版，实际可以用多路）
 */
int two_way_merge(char file1[], char file2[], char output[]) {
    FILE *f1 = fopen(file1, "r");
    FILE *f2 = fopen(file2, "r");
    FILE *fout = fopen(output, "w");
    if (!f1 || !f2 || !fout) {
        if (f1) fclose(f1);
        if (f2) fclose(f2);
        if (fout) fclose(fout);
        return 0;
    }

    int a, b;
    int hasA = (fscanf(f1, "%d", &a) == 1);
    int hasB = (fscanf(f2, "%d", &b) == 1);

    while (hasA && hasB) {
        if (a <= b) {
            fprintf(fout, "%d\n", a);
            hasA = (fscanf(f1, "%d", &a) == 1);
        } else {
            fprintf(fout, "%d\n", b);
            hasB = (fscanf(f2, "%d", &b) == 1);
        }
    }
    while (hasA) {
        fprintf(fout, "%d\n", a);
        hasA = (fscanf(f1, "%d", &a) == 1);
    }
    while (hasB) {
        fprintf(fout, "%d\n", b);
        hasB = (fscanf(f2, "%d", &b) == 1);
    }

    fclose(f1); fclose(f2); fclose(fout);
    return 1;
}


// 测试：外部排序——模拟"数据太大，内存放不下"的场景
int main(void) {
    // 1. 生成一个模拟的大文件（20个整数）
    const char *inputFile = "/tmp/ext_sort_input.txt";
    FILE *f = fopen(inputFile, "w");
    if (!f) {
        printf("创建输入文件失败\n");
        return 1;
    }
    int testData[] = {42, 15, 73, 28, 61, 9, 34, 88, 17, 55,
                      3, 67, 21, 49, 82, 11, 36, 94, 25, 70};
    for (int i = 0; i < 20; i++) {
        fprintf(f, "%d\n", testData[i]);
    }
    fclose(f);
    printf("生成了 20 个数的输入文件: %s\n", inputFile);

    // 2. 生成初始归并段（每次读 MEMORY_SIZE=10 个，排序后写临时文件）
    char runFiles[10][50] = {
        "/tmp/ext_run_0.txt", "/tmp/ext_run_1.txt"
    };
    int runCount = create_runs(inputFile, runFiles, 10);
    if (runCount < 0) {
        printf("生成归并段失败\n");
        remove(inputFile);
        return 1;
    }
    printf("生成了 %d 个初始归并段\n", runCount);

    // 3. 二路归并
    char outputFile[] = "/tmp/ext_sort_output.txt";
    if (runCount >= 2) {
        if (!two_way_merge(runFiles[0], runFiles[1], outputFile)) {
            printf("归并失败\n");
            remove(inputFile);
            for (int i = 0; i < runCount; i++) remove(runFiles[i]);
            return 1;
        }
        printf("归并完成 → %s\n", outputFile);

        // 打印结果
        printf("最终排序结果: ");
        FILE *fout = fopen(outputFile, "r");
        if (!fout) {
            printf("读取输出文件失败\n");
            remove(inputFile);
            for (int i = 0; i < runCount; i++) remove(runFiles[i]);
            remove(outputFile);
            return 1;
        }
        int val;
        while (fscanf(fout, "%d", &val) == 1) {
            printf("%d ", val);
        }
        printf("\n");
        fclose(fout);
    }

    // 清理临时文件
    remove(inputFile);
    for (int i = 0; i < runCount; i++) remove(runFiles[i]);
    remove(outputFile);

    return 0;
}
