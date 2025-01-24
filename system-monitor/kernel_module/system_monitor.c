// kernel_module/system_monitor.c
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
#include <linux/slab.h>
#include <linux/uaccess.h>

#define NETLINK_USER 31
#define MAX_PROCESSES 100

// Structure for process information
struct process_info {
    pid_t pid;
    char comm[TASK_COMM_LEN];
    unsigned long cpu_usage;
    unsigned long mem_usage;
    unsigned int state;
};

// Main metrics structure
struct system_metrics {
    unsigned long cpu_usage[NR_CPUS];
    unsigned long total_memory;
    unsigned long used_memory;
    unsigned long free_memory;
    unsigned long cached_memory;
    unsigned long available_memory;
    struct process_info processes[MAX_PROCESSES];
    int process_count;
    unsigned long timestamp;
    unsigned long total_cpu_time;
    unsigned long idle_cpu_time;
};

static struct sock *nl_sk = NULL;
static struct timer_list metrics_timer;
static struct system_metrics *current_metrics = NULL;
static DEFINE_SPINLOCK(metrics_lock);

// Function to get CPU statistics
static void get_cpu_stats(void)
{
    int cpu;
    struct kernel_cpustat stat;

    for_each_possible_cpu(cpu) {
        if (cpu >= NR_CPUS)
            break;
            
        // Get per-CPU usage
        current_metrics->cpu_usage[cpu] = kcpustat_cpu(cpu).cpustat[CPUTIME_USER] +
                                        kcpustat_cpu(cpu).cpustat[CPUTIME_SYSTEM];
    }
}

// Function to get memory statistics
static void get_memory_stats(void)
{
    struct sysinfo si;
    si_meminfo(&si);

    current_metrics->total_memory = si.totalram << PAGE_SHIFT;
    current_metrics->free_memory = si.freeram << PAGE_SHIFT;
    current_metrics->available_memory = si_mem_available() << PAGE_SHIFT;
    current_metrics->used_memory = current_metrics->total_memory - 
                                 current_metrics->available_memory;
}

// Function to get process information
static void get_process_stats(void)
{
    struct task_struct *task;
    int i = 0;

    rcu_read_lock();
    for_each_process(task) {
        if (i >= MAX_PROCESSES)
            break;

        current_metrics->processes[i].pid = task->pid;
        memcpy(current_metrics->processes[i].comm, task->comm, TASK_COMM_LEN);
        current_metrics->processes[i].state = task->state;
        
        // Get process memory usage
        if (task->mm) {
            current_metrics->processes[i].mem_usage = 
                get_mm_rss(task->mm) << PAGE_SHIFT;
        }

        // Calculate CPU usage (simplified)
        current_metrics->processes[i].cpu_usage = 
            task->utime + task->stime;

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
    
    spin_lock(&metrics_lock);
    
    // Collect all metrics
    get_cpu_stats();
    get_memory_stats();
    get_process_stats();
    current_metrics->timestamp = ktime_get_real_seconds();

    // Prepare and send netlink message
    skb = nlmsg_new(sizeof(struct system_metrics), GFP_ATOMIC);
    if (skb) {
        nlh = nlmsg_put(skb, 0, 0, NLMSG_DONE, 
                        sizeof(struct system_metrics), 0);
        memcpy(nlmsg_data(nlh), current_metrics, 
               sizeof(struct system_metrics));
        nlmsg_multicast(nl_sk, skb, 0, NETLINK_USER, GFP_ATOMIC);
    }

    spin_unlock(&metrics_lock);

    // Reschedule timer
    mod_timer(&metrics_timer, jiffies + HZ);
}

// Module initialization
static int __init monitor_init(void)
{
    struct netlink_kernel_cfg cfg = {
        .groups = 1,
    };

    // Create netlink socket
    nl_sk = netlink_kernel_create(&init_net, NETLINK_USER, &cfg);
    if (!nl_sk) {
        pr_err("Error creating netlink socket.\n");
        return -ENOMEM;
    }

    // Allocate metrics structure
    current_metrics = kzalloc(sizeof(struct system_metrics), GFP_KERNEL);
    if (!current_metrics) {
        netlink_kernel_release(nl_sk);
        return -ENOMEM;
    }

    // Initialize timer
    timer_setup(&metrics_timer, metrics_timer_callback, 0);
    mod_timer(&metrics_timer, jiffies + HZ);

    pr_info("System monitor module loaded\n");
    return 0;
}

// Module cleanup
static void __exit monitor_exit(void)
{
    del_timer(&metrics_timer);
    kfree(current_metrics);
    netlink_kernel_release(nl_sk);
    pr_info("System monitor module unloaded\n");
}

module_init(monitor_init);
module_exit(monitor_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("System Monitor Kernel Module");