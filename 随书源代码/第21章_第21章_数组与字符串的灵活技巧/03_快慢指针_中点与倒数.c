#include <stdio.h>
#include <stdlib.h>

struct ListNode {
    int val;
    struct ListNode *next;
};

/* 快慢指针变体一：寻找链表的中点 */
struct ListNode *find_middle(struct ListNode *head) {
    struct ListNode *slow = head;
    struct ListNode *fast = head;
    while (fast != NULL && fast->next != NULL) {
        slow = slow->next;
        fast = fast->next->next;
    }
    return slow;  /* fast到末尾时，slow正好在中点 */
}

/* 快慢指针变体二：寻找倒数第k个节点 */
struct ListNode *find_kth_from_end(struct ListNode *head, int k) {
    struct ListNode *fast = head;
    struct ListNode *slow = head;
    /* fast先出发k步 */
    for (int i = 0; i < k; i++) {
        if (fast == NULL) return NULL;  /* k超过链表长度 */
        fast = fast->next;
    }
    /* 两人同速走到底 */
    while (fast != NULL) {
        slow = slow->next;
        fast = fast->next;
    }
    return slow;  /* fast到末尾时，slow在倒数第k个 */
}

/* 测试：快慢指针 */
int main() {
    /* 构建链表 1 → 2 → 3 → 4 → 5 → NULL */
    struct ListNode nodes[5];
    for (int i = 0; i < 5; i++) {
        nodes[i].val = i + 1;
        nodes[i].next = (i < 4) ? &nodes[i+1] : NULL;
    }

    struct ListNode *mid = find_middle(&nodes[0]);
    printf("链表中点：%d（期望 3）\n", mid->val);

    struct ListNode *kth = find_kth_from_end(&nodes[0], 2);
    printf("倒数第2个：%d（期望 4）\n", kth->val);

    kth = find_kth_from_end(&nodes[0], 1);
    printf("倒数第1个：%d（期望 5）\n", kth->val);

    return 0;
}
