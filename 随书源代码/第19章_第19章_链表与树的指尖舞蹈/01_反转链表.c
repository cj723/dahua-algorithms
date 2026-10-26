#include <stdio.h>
#include <stdlib.h>

struct ListNode {
    int val;
    struct ListNode *next;
};

struct ListNode *reverse_list(struct ListNode *head) {
    struct ListNode *prev = NULL;       /* 前一个节点（最初没有前驱，所以是 NULL） */
    struct ListNode *curr = head;       /* 当前节点 */
    struct ListNode *nextTemp = NULL;   /* 临时工，用来保存下一个节点 */

    while (curr != NULL) {
        nextTemp = curr->next;  /* 1. 留后路：临时工先抱住下一个节点 */
        curr->next = prev;      /* 2. 向后转：当前节点指针反转，指向前一个节点 */
        prev = curr;            /* 3. prev 跟上：prev 移至当前节点（为下一轮做前驱） */
        curr = nextTemp;        /* 4. curr 前进：curr 移至下一个节点（继续迭代） */
    }

    /* 循环结束时，curr 变成了 NULL，prev 刚好停在原来链表的最后一个节点 */
    return prev;
}

/* 辅助：创建节点 */
struct ListNode *make_node(int val) {
    struct ListNode *n = (struct ListNode *)malloc(sizeof(struct ListNode));
    n->val = val; n->next = NULL;
    return n;
}

/* 辅助：释放链表 */
void free_list(struct ListNode *head) {
    while (head != NULL) {
        struct ListNode *next = head->next;
        free(head);
        head = next;
    }
}

/* 测试：反转链表 */
int main(void) {
    /* 构建链表 1 → 2 → 3 → 4 → 5 → NULL */
    struct ListNode *head = make_node(1);
    head->next = make_node(2);
    head->next->next = make_node(3);
    head->next->next->next = make_node(4);
    head->next->next->next->next = make_node(5);

    printf("原链表：");
    for (struct ListNode *p = head; p; p = p->next)
        printf("%d ", p->val);
    printf("\n");

    head = reverse_list(head);

    printf("反转后：");
    for (struct ListNode *p = head; p; p = p->next)
        printf("%d ", p->val);
    printf("\n");

    free_list(head);
    return 0;
}
