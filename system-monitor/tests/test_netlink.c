#include <sys/socket.h>
#include <linux/netlink.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>

#define NETLINK_TEST 31
#define MAX_PAYLOAD 8620
#define MAX_PROCESSES 100
#define TASK_COMM_LEN 16

// Matching structures with kernel module
#pragma pack(push, 1)
struct process_info {
    pid_t pid;
    unsigned long cpu_usage;
    char comm[TASK_COMM_LEN];
    unsigned long mem_usage;
    long state;
    unsigned long priority;
    unsigned long nice;
};

struct system_metrics {
    unsigned long cpu_usage[32];  // NR_CPUS
    struct {
        unsigned long total;
        unsigned long used;
        unsigned long free;
        unsigned long cached;
        unsigned long available;
        unsigned long buffers;
    } memory;
    struct process_info processes[MAX_PROCESSES];
    int process_count;
    unsigned long timestamp;
};
#pragma pack(pop)

void format_bytes(char *buf, size_t buf_size, unsigned long bytes) {
    const char *units[] = {"B", "KB", "MB", "GB", "TB"};
    int i = 0;
    double size = bytes;

    while (size > 1024 && i < 4) {
        size /= 1024;
        i++;
    }

    snprintf(buf, buf_size, "%.2f %s", size, units[i]);
}

void print_metrics(struct system_metrics *metrics) {
    char buf[64];
    time_t t = (time_t)metrics->timestamp;
    printf("\033[2J\033[H");  // Clear screen and move cursor to top
    printf("=== System Metrics at %s", ctime(&t));
    
    // CPU Usage
    printf("\nCPU Usage:\n");
    for (int i = 0; i < 8; i++) {
        if (metrics->cpu_usage[i] > 0) {
            printf("CPU%d: %3lu%% ", i, metrics->cpu_usage[i]);
            // Print bar graph
            printf("[");
            int bars = metrics->cpu_usage[i] / 2;
            for (int j = 0; j < 50; j++) {
                if (j < bars) {
                    printf("|");
                } else {
                    printf(" ");
                }
            }
            printf("]\n");
        }
    }

    // Memory Information
    printf("\nMemory Information:\n");
    format_bytes(buf, sizeof(buf), metrics->memory.total);
    printf("Total:     %s\n", buf);
    format_bytes(buf, sizeof(buf), metrics->memory.used);
    printf("Used:      %s\n", buf);
    format_bytes(buf, sizeof(buf), metrics->memory.free);
    printf("Free:      %s\n", buf);
    format_bytes(buf, sizeof(buf), metrics->memory.cached);
    printf("Cached:    %s\n", buf);
    format_bytes(buf, sizeof(buf), metrics->memory.available);
    printf("Available: %s\n", buf);

    // Process Information
    printf("\nTop Processes (by CPU usage):\n");
    printf("%-6s %-6s %-6s %-6s %-4s %-4s %-15s\n",
           "PID", "CPU%", "MEM", "PRI", "NICE", "STATE", "NAME");
    printf("--------------------------------------------------\n");

    // Sort processes by CPU usage (simple bubble sort)
    struct process_info sorted[MAX_PROCESSES];
    memcpy(sorted, metrics->processes, sizeof(struct process_info) * metrics->process_count);
    for (int i = 0; i < metrics->process_count - 1; i++) {
        for (int j = 0; j < metrics->process_count - i - 1; j++) {
            if (sorted[j].cpu_usage < sorted[j + 1].cpu_usage) {
                struct process_info temp = sorted[j];
                sorted[j] = sorted[j + 1];
                sorted[j + 1] = temp;
            }
        }
    }

    // Print top 10 processes
    for (int i = 0; i < 10 && i < metrics->process_count; i++) {
        format_bytes(buf, sizeof(buf), sorted[i].mem_usage);
        printf("%-6d %-6lu %-6s %-6lu %-4ld %-4c %-15s\n",
               sorted[i].pid,
               sorted[i].cpu_usage,
               buf,
               sorted[i].priority,
               sorted[i].nice,
               (char)sorted[i].state,
               sorted[i].comm);
    }

    printf("\nTotal processes: %d\n", metrics->process_count);
    printf("\nPress 'q' to quit...\n");
}

int main() {
    struct sockaddr_nl src_addr;
    int sock_fd;
    struct nlmsghdr *nlh = NULL;
    
    // Create socket
    sock_fd = socket(PF_NETLINK, SOCK_RAW, NETLINK_TEST);
    if (sock_fd < 0) {
        printf("Socket creation failed: %s\n", strerror(errno));
        return -1;
    }

    // Initialize address
    memset(&src_addr, 0, sizeof(src_addr));
    src_addr.nl_family = AF_NETLINK;
    src_addr.nl_pid = getpid();
    src_addr.nl_groups = 1;  // Join multicast group 1

    // Bind socket
    if (bind(sock_fd, (struct sockaddr*)&src_addr, sizeof(src_addr)) < 0) {
        printf("Bind failed: %s\n", strerror(errno));
        close(sock_fd);
        return -1;
    }

    // Allocate receive buffer
    nlh = malloc(NLMSG_SPACE(MAX_PAYLOAD));
    if (!nlh) {
        printf("Failed to allocate buffer\n");
        close(sock_fd);
        return -1;
    }

    printf("Waiting for system metrics...\n");
    printf("Press Ctrl+C to exit\n");

    // Set up non-blocking I/O for keyboard input
    struct timeval tv;
    fd_set readfds;
    int stdin_fd = fileno(stdin);
    system("stty raw -echo");

    while (1) {
        FD_ZERO(&readfds);
        FD_SET(sock_fd, &readfds);
        FD_SET(stdin_fd, &readfds);

        tv.tv_sec = 1;
        tv.tv_usec = 0;

        int ret = select(sock_fd + 1, &readfds, NULL, NULL, &tv);
        
        if (ret < 0) {
            printf("select failed: %s\n", strerror(errno));
            break;
        }

        if (FD_ISSET(stdin_fd, &readfds)) {
            char c = getchar();
            if (c == 'q' || c == 'Q') {
                break;
            }
        }

        if (FD_ISSET(sock_fd, &readfds)) {
            ret = recv(sock_fd, nlh, NLMSG_SPACE(MAX_PAYLOAD), 0);
            if (ret < 0) {
                printf("recv failed: %s\n", strerror(errno));
                continue;
            }

            struct system_metrics *metrics = NLMSG_DATA(nlh);
            print_metrics(metrics);
        }
    }

    // Restore terminal settings
    system("stty sane");

    free(nlh);
    close(sock_fd);
    return 0;
}