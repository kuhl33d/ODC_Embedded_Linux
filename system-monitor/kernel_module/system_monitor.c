#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/netlink.h>
#include <linux/skbuff.h>
#include <linux/sched.h>
#include <linux/sched/signal.h>
#include <linux/mm.h>
#include <linux/timer.h>
#include <linux/proc_fs.h>
#include <linux/cpumask.h>
#include <linux/init.h>
#include <linux/kernel_stat.h>
#include <linux/slab.h>
#include <linux/netlink.h>
#include <net/sock.h>
#include <linux/jiffies.h>
#include <linux/time.h>
#include <linux/timekeeping.h>
#include <linux/cpufreq.h>
#include <linux/mm.h>
#include <linux/vmstat.h>
#include <linux/swap.h>
#include <linux/mm_types.h>
#include <linux/mmzone.h>

#define NETLINK_TEST 31
#define MAX_PROCESSES 100
#define MAX_PAYLOAD 8620

// Debug macros
#define DEBUG_PRINT(fmt, ...) \
    pr_info("System Monitor: " fmt "\n", ##__VA_ARGS__)
#define ERROR_PRINT(fmt, ...) \
    pr_err("System Monitor Error: " fmt "\n", ##__VA_ARGS__)

// Ensure struct alignment
#pragma pack(push, 1)

// Process information structure
struct process_info {
    pid_t pid;                      // Process ID
    unsigned long cpu_usage;        // CPU usage percentage
    char comm[TASK_COMM_LEN];      // Process name
    unsigned long mem_usage;        // Memory usage
    long state;                     // Process state
    unsigned long priority;         // Process priority
    unsigned long nice;            // Nice value
};

// Memory information structure
struct memory_info {
    unsigned long total;
    unsigned long used;
    unsigned long free;
    unsigned long cached;
    unsigned long available;
    unsigned long buffers;
};

// Main metrics structure
struct system_metrics {
    unsigned long cpu_usage[32];    // Per-CPU usage
    struct memory_info memory;      // Memory information
    struct process_info processes[MAX_PROCESSES];  // Process information
    int process_count;              // Number of processes
    unsigned long timestamp;        // Current timestamp
};

#pragma pack(pop)

// Global variables
static struct sock *nl_sk = NULL;
static struct timer_list metrics_timer;
static struct system_metrics *current_metrics = NULL;
static DEFINE_SPINLOCK(metrics_lock);

// Previous CPU statistics for delta calculation
static struct kernel_cpustat prev_cpu_stat[NR_CPUS];
static bool first_run = true;

// Function to get CPU statistics
static void get_cpu_stats(void)
{
    int cpu;
    struct kernel_cpustat curr_cpu_stat;
    u64 user, nice, system, idle, iowait, irq, softirq;
    u64 total, idle_time, non_idle_time;

    for_each_possible_cpu(cpu) {
        if (cpu >= NR_CPUS)
            break;

        curr_cpu_stat = kcpustat_cpu(cpu);

        if (!first_run) {
            user = curr_cpu_stat.cpustat[CPUTIME_USER] - 
                   prev_cpu_stat[cpu].cpustat[CPUTIME_USER];
            nice = curr_cpu_stat.cpustat[CPUTIME_NICE] - 
                   prev_cpu_stat[cpu].cpustat[CPUTIME_NICE];
            system = curr_cpu_stat.cpustat[CPUTIME_SYSTEM] - 
                    prev_cpu_stat[cpu].cpustat[CPUTIME_SYSTEM];
            idle = curr_cpu_stat.cpustat[CPUTIME_IDLE] - 
                   prev_cpu_stat[cpu].cpustat[CPUTIME_IDLE];
            iowait = curr_cpu_stat.cpustat[CPUTIME_IOWAIT] - 
                    prev_cpu_stat[cpu].cpustat[CPUTIME_IOWAIT];
            irq = curr_cpu_stat.cpustat[CPUTIME_IRQ] - 
                  prev_cpu_stat[cpu].cpustat[CPUTIME_IRQ];
            softirq = curr_cpu_stat.cpustat[CPUTIME_SOFTIRQ] - 
                     prev_cpu_stat[cpu].cpustat[CPUTIME_SOFTIRQ];

            idle_time = idle + iowait;
            non_idle_time = user + nice + system + irq + softirq;
            total = idle_time + non_idle_time;

            if (total > 0) {
                current_metrics->cpu_usage[cpu] = 
                    (non_idle_time * 100) / total;
            } else {
                current_metrics->cpu_usage[cpu] = 0;
            }
        }

        prev_cpu_stat[cpu] = curr_cpu_stat;
    }

    first_run = false;
}

// Function to get memory statistics
static void get_memory_stats(void)
{
    struct sysinfo si;
    unsigned long cached;

    si_meminfo(&si);
    cached = global_node_page_state(NR_FILE_PAGES);

    current_metrics->memory.total = si.totalram << PAGE_SHIFT;
    current_metrics->memory.free = si.freeram << PAGE_SHIFT;
    current_metrics->memory.buffers = si.bufferram << PAGE_SHIFT;
    current_metrics->memory.cached = cached << PAGE_SHIFT;
    current_metrics->memory.available = si_mem_available() << PAGE_SHIFT;
    
    current_metrics->memory.used = current_metrics->memory.total -
                                 current_metrics->memory.free -
                                 current_metrics->memory.buffers -
                                 current_metrics->memory.cached;
}

// Function to get process state
static char get_task_state(struct task_struct *task)
{
    if (task->__state & TASK_RUNNING)
        return 'R';
    if (task->__state & TASK_UNINTERRUPTIBLE)
        return 'D';
    if (task->__state & TASK_STOPPED)
        return 'T';
    if (task->exit_state & EXIT_ZOMBIE)
        return 'Z';
    return 'S';
}

// Function to get process information
static void get_process_stats(void)
{
    struct task_struct *task;
    int i = 0;
    unsigned long flags;

    rcu_read_lock();
    for_each_process(task) {
        if (i >= MAX_PROCESSES)
            break;

        get_task_struct(task);
        
        current_metrics->processes[i].pid = task->pid;
        memcpy(current_metrics->processes[i].comm, task->comm, TASK_COMM_LEN);
        current_metrics->processes[i].state = get_task_state(task);
        current_metrics->processes[i].priority = task->prio;
        current_metrics->processes[i].nice = task_nice(task);
        
        if (task->mm) {
            current_metrics->processes[i].mem_usage = 
                get_mm_rss(task->mm) << PAGE_SHIFT;
        }

        // Calculate CPU usage based on task's time values
        local_irq_save(flags);
        current_metrics->processes[i].cpu_usage = 
            (task->utime + task->stime) * 100UL /
            (jiffies - task->start_time + 1);
        local_irq_restore(flags);

        put_task_struct(task);
        i++;
    }
    rcu_read_unlock();

    current_metrics->process_count = i;
}

// Timer callback function
static void metrics_timer_callback(struct timer_list *t)
{
    struct sk_buff *skb;
    struct nlmsghdr *nlh;
    int ret;
    
    spin_lock(&metrics_lock);
    
    // Collect metrics
    get_cpu_stats();
    get_memory_stats();
    get_process_stats();
    current_metrics->timestamp = ktime_get_real_seconds();

    DEBUG_PRINT("Collecting metrics at timestamp: %lu", 
                current_metrics->timestamp);

    // Create new skb with proper size
    skb = nlmsg_new(NLMSG_ALIGN(sizeof(struct system_metrics)), GFP_ATOMIC);
    if (!skb) {
        ERROR_PRINT("Failed to allocate new skb");
        goto out;
    }

    // Add netlink header
    nlh = nlmsg_put(skb, 0, 0, NLMSG_DONE, 
                    NLMSG_ALIGN(sizeof(struct system_metrics)), 0);
    if (!nlh) {
        ERROR_PRINT("Failed to put nlmsg");
        kfree_skb(skb);
        goto out;
    }

    // Copy data
    memcpy(nlmsg_data(nlh), current_metrics, sizeof(struct system_metrics));
    nlmsg_end(skb, nlh);

    // Send message using multicast
    ret = nlmsg_multicast(nl_sk, skb, 0, 1, GFP_ATOMIC);
    if (ret < 0 && ret != -ESRCH) {
        ERROR_PRINT("Failed to send netlink message, error: %d", ret);
    } else {
        DEBUG_PRINT("Netlink message sent successfully");
    }

out:
    spin_unlock(&metrics_lock);
    mod_timer(&metrics_timer, jiffies + HZ);  // Schedule next update
}

// Module initialization
static int __init monitor_init(void)
{
    struct netlink_kernel_cfg cfg = {
        .groups = 1,
        .flags = 0,
        .input = NULL,
        .cb_mutex = NULL,
    };

    DEBUG_PRINT("Initializing System Monitor");

    // Create netlink socket
    nl_sk = netlink_kernel_create(&init_net, NETLINK_TEST, &cfg);
    if (!nl_sk) {
        ERROR_PRINT("Error creating netlink socket");
        return -ENOMEM;
    }

    // Allocate metrics structure
    current_metrics = kzalloc(sizeof(struct system_metrics), GFP_KERNEL);
    if (!current_metrics) {
        ERROR_PRINT("Failed to allocate metrics structure");
        netlink_kernel_release(nl_sk);
        return -ENOMEM;
    }

    // Initialize timer
    timer_setup(&metrics_timer, metrics_timer_callback, 0);
    mod_timer(&metrics_timer, jiffies + HZ);

    DEBUG_PRINT("Module loaded successfully");
    return 0;
}

// Module cleanup
static void __exit monitor_exit(void)
{
    DEBUG_PRINT("Cleaning up System Monitor");
    
    // Cancel any pending timer
    del_timer_sync(&metrics_timer);

    // Wait for any in-progress operations to complete
    synchronize_rcu();

    // Free resources
    if (current_metrics) {
        kfree(current_metrics);
        current_metrics = NULL;
    }

    // Release netlink socket
    if (nl_sk) {
        netlink_kernel_release(nl_sk);
        nl_sk = NULL;
    }

    DEBUG_PRINT("Module unloaded successfully");
}

module_init(monitor_init);
module_exit(monitor_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("kuhleed");
MODULE_DESCRIPTION("System Monitor Kernel Module");
MODULE_VERSION("1.0");