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

#define NETLINK_USER 31
#define MAX_PROCESSES 100

// Process state definitions
#define PROCESS_RUNNING 'R'
#define PROCESS_SLEEPING 'S'
#define PROCESS_DISK_SLEEP 'D'
#define PROCESS_STOPPED 'T'
#define PROCESS_ZOMBIE 'Z'

// Structure definitions
struct process_info {
    pid_t pid;
    char comm[TASK_COMM_LEN];
    unsigned long cpu_usage;
    unsigned long mem_usage;
    char state;
    unsigned long priority;
    unsigned long nice;
    unsigned long num_threads;
    unsigned long vsize;    // Virtual memory size
    unsigned long rss;      // Resident Set Size
};

struct system_metrics {
    unsigned long cpu_usage[NR_CPUS];
    unsigned long cpu_freq[NR_CPUS];
    struct {
        unsigned long total;
        unsigned long used;
        unsigned long free;
        unsigned long shared;
        unsigned long buffers;
        unsigned long cached;
        unsigned long available;
        unsigned long swap_total;
        unsigned long swap_free;
    } memory;
    struct process_info processes[MAX_PROCESSES];
    int process_count;
    unsigned long timestamp;
    struct {
        unsigned long pgpgin;
        unsigned long pgpgout;
        unsigned long pswpin;
        unsigned long pswpout;
    } io_stats;
};

// Global variables
static struct sock *nl_sk = NULL;
static struct timer_list metrics_timer;
static struct system_metrics *current_metrics = NULL;
static DEFINE_SPINLOCK(metrics_lock);
// Helper function to get CPU frequency
static unsigned long get_cpu_freq(int cpu)
{
    unsigned long freq = 0;
    struct cpufreq_policy *policy;

    policy = cpufreq_cpu_get(cpu);
    if (policy) {
        freq = policy->cur;
        cpufreq_cpu_put(policy);
    }

    return freq;
}

// Function to get CPU statistics
static void get_cpu_stats(void)
{
    int cpu;
    u64 user, nice, system, idle, iowait, irq, softirq;
    u64 total, busy;
    
    for_each_possible_cpu(cpu) {
        if (cpu >= NR_CPUS)
            break;

        // Get CPU frequency
        current_metrics->cpu_freq[cpu] = get_cpu_freq(cpu);

        // Get CPU usage
        user = kcpustat_cpu(cpu).cpustat[CPUTIME_USER];
        nice = kcpustat_cpu(cpu).cpustat[CPUTIME_NICE];
        system = kcpustat_cpu(cpu).cpustat[CPUTIME_SYSTEM];
        idle = kcpustat_cpu(cpu).cpustat[CPUTIME_IDLE];
        iowait = kcpustat_cpu(cpu).cpustat[CPUTIME_IOWAIT];
        irq = kcpustat_cpu(cpu).cpustat[CPUTIME_IRQ];
        softirq = kcpustat_cpu(cpu).cpustat[CPUTIME_SOFTIRQ];

        // Calculate total and busy time
        total = user + nice + system + idle + iowait + irq + softirq;
        busy = total - idle - iowait;

        // Calculate percentage
        if (total > 0) {
            current_metrics->cpu_usage[cpu] = (busy * 100) / total;
        } else {
            current_metrics->cpu_usage[cpu] = 0;
        }
    }
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
    current_metrics->memory.shared = si.sharedram << PAGE_SHIFT;
    current_metrics->memory.buffers = si.bufferram << PAGE_SHIFT;
    current_metrics->memory.cached = cached << PAGE_SHIFT;
    current_metrics->memory.swap_total = si.totalswap << PAGE_SHIFT;
    current_metrics->memory.swap_free = si.freeswap << PAGE_SHIFT;
    
    // Calculate used and available memory
    current_metrics->memory.used = current_metrics->memory.total -
                                 current_metrics->memory.free -
                                 current_metrics->memory.buffers -
                                 current_metrics->memory.cached;
    
    current_metrics->memory.available = si_mem_available() << PAGE_SHIFT;
}

// Function to get I/O statistics
static void get_io_stats(void)
{
    struct sysinfo si;
    si_meminfo(&si);

    // File I/O statistics using vmstat counters
    current_metrics->io_stats.pgpgin = 
        global_node_page_state(NR_VM_ZONE_STAT_ITEMS + NR_VM_NODE_STAT_ITEMS);
    current_metrics->io_stats.pgpgout = 
        global_node_page_state(NR_FILE_DIRTY);

    // Swap statistics from sysinfo
    current_metrics->io_stats.pswpin = 
        (si.totalswap - si.freeswap) >> (PAGE_SHIFT - 10);  // Convert to KB
    current_metrics->io_stats.pswpout = 
        si.totalswap >> (PAGE_SHIFT - 10);  // Convert to KB
}
// Function to get process state as char
static char get_task_state(struct task_struct *task)
{
    if (task->__state & TASK_RUNNING)
        return PROCESS_RUNNING;
    if (task->__state & TASK_UNINTERRUPTIBLE)
        return PROCESS_DISK_SLEEP;
    if (task->__state & TASK_STOPPED)
        return PROCESS_STOPPED;
    if (task->__state & TASK_TRACED)
        return PROCESS_STOPPED;
    if (task->exit_state & EXIT_ZOMBIE)
        return PROCESS_ZOMBIE;
    return PROCESS_SLEEPING;
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
        current_metrics->processes[i].state = get_task_state(task);
        current_metrics->processes[i].priority = task->prio;
        current_metrics->processes[i].nice = task_nice(task);
        
        if (task->signal)
            current_metrics->processes[i].num_threads = task->signal->nr_threads;
        
        if (task->mm) {
            current_metrics->processes[i].vsize = task->mm->total_vm << PAGE_SHIFT;
            current_metrics->processes[i].rss = get_mm_rss(task->mm) << PAGE_SHIFT;
            current_metrics->processes[i].mem_usage = 
                (current_metrics->processes[i].rss * 100UL) /
                current_metrics->memory.total;
        }

        current_metrics->processes[i].cpu_usage = 
            (task->utime + task->stime) * 100UL /
            (jiffies - task->start_time + 1);

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
    get_io_stats();
    current_metrics->timestamp = ktime_get_real_seconds();

    // Create new netlink message
    skb = nlmsg_new(sizeof(struct system_metrics), GFP_ATOMIC);
    if (skb) {
        nlh = nlmsg_put(skb, 0, 0, NLMSG_DONE, 
                        sizeof(struct system_metrics), 0);
        if (nlh) {
            memcpy(nlmsg_data(nlh), current_metrics, 
                   sizeof(struct system_metrics));
            netlink_broadcast(nl_sk, skb, 0, NETLINK_USER, GFP_ATOMIC);
        } else {
            kfree_skb(skb);
        }
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
        pr_err("System Monitor: Error creating netlink socket.\n");
        return -ENOMEM;
    }

    // Allocate metrics structure
    current_metrics = kzalloc(sizeof(struct system_metrics), GFP_KERNEL);
    if (!current_metrics) {
        pr_err("System Monitor: Failed to allocate metrics structure.\n");
        netlink_kernel_release(nl_sk);
        return -ENOMEM;
    }

    // Initialize timer
    timer_setup(&metrics_timer, metrics_timer_callback, 0);
    mod_timer(&metrics_timer, jiffies + HZ);

    pr_info("System Monitor: Module loaded successfully\n");
    return 0;
}

// Module cleanup
static void __exit monitor_exit(void)
{
    del_timer(&metrics_timer);
    kfree(current_metrics);
    netlink_kernel_release(nl_sk);
    pr_info("System Monitor: Module unloaded successfully\n");
}

module_init(monitor_init);
module_exit(monitor_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("kuhleed");
MODULE_DESCRIPTION("System Monitor Kernel Module");
MODULE_VERSION("1.0");