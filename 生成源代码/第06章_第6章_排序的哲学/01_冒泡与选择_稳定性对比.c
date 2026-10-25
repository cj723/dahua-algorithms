#include <stdio.h>
#include <string.h>

typedef struct {
    char name[20];
    int score;
} Student;

/* 冒泡排序：稳定的 */
void bubble_sort(Student arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - 1 - i; j++) {
            if (arr[j].score > arr[j + 1].score) {
                Student temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

/* 选择排序：不稳定的 */
void selection_sort(Student arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        int minIdx = i;
        for (int j = i + 1; j < n; j++) {
            if (arr[j].score < arr[minIdx].score) {
                minIdx = j;
            }
        }
        /* 注意！这个交换可能跳过同分元素，打乱相对顺序 */
        if (minIdx != i) {
            Student temp = arr[i];
            arr[i] = arr[minIdx];
            arr[minIdx] = temp;
        }
    }
}

int main(void) {
    Student students[] = {
        {"张三", 658}, {"李四", 658}, {"王五", 600}, {"赵六", 701}
    };
    int n = 4;

    bubble_sort(students, n);
    printf("冒泡排序（稳定）：");
    for (int i = 0; i < n; i++)
        printf("%s(%d) ", students[i].name, students[i].score);
    printf("\n");

    /* 重置数据 */
    Student students2[] = {
        {"张三", 658}, {"李四", 658}, {"王五", 600}, {"赵六", 701}
    };
    selection_sort(students2, n);
    printf("选择排序（不稳定）：");
    for (int i = 0; i < n; i++)
        printf("%s(%d) ", students2[i].name, students2[i].score);
    printf("\n");

    return 0;
}
