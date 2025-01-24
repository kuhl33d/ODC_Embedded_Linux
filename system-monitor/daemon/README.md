# Daemon Service

1. Connects to the kernel module via Netlink
2. Parses binary metrics data
3. Maintains metrics history
4. Provides WebSocket server for UI clients
5. Handles client connections/disconnections
6. Implements error handling and logging

## Key features:

- Asynchronous operation
- Real-time data broadcasting
- Historical data maintenance
- Robust error handling
- Efficient binary data parsing
- Clean client management

## Communication Methods Between Kernel and User Space

When developing kernel-user space communication mechanisms, there are several approaches available, each with its own strengths and trade-offs. Here's an analysis of the main methods and why we chose Netlink sockets for our system monitor.

### Available Approaches

#### 1. procfs (/proc)
The process filesystem is one of the traditional methods for kernel-user space communication.

**Advantages:**
- Simple text-based interface
- Human-readable format
- Easy to read and write
- No special libraries needed
- Good for configuration data
- Well-documented

**Limitations:**
- Polling required for updates
- Performance overhead for large datasets
- No real-time notification mechanism
- Limited to text-based format
- File I/O overhead

#### 2. sysfs
A more structured interface typically used for device drivers and kernel subsystems.

**Advantages:**
- Well-structured hierarchy
- Automatic attribute management
- Good for device attributes
- Self-documenting
- Type-safe attributes

**Limitations:**
- More complex than procfs
- Still requires polling
- Limited to simple value types
- Not suitable for high-frequency updates
- Overhead from VFS layer

#### 3. Netlink Sockets
A socket-based, asynchronous communication mechanism.

**Advantages:**
- Asynchronous communication
- Event-driven updates
- Multicast support
- Efficient for real-time data
- Bidirectional communication
- Native support for multiple consumers
- Low latency
- No polling required

**Limitations:**
- More complex implementation
- Requires socket programming
- Protocol design needed
- Message format handling

#### 4. Character Devices
Traditional character device interface for kernel-user space communication.

**Advantages:**
- Full control over data format
- Good for large data transfers
- Direct communication channel
- Efficient for streaming data
- Traditional UNIX-like interface

**Limitations:**
- Complex implementation
- No built-in multicast
- Manual protocol implementation
- Limited to single reader/writer
- No native event notification

### Why We Chose Netlink Sockets

For our system monitor implementation, we chose Netlink sockets for several key reasons:

1. **Real-Time Requirements**
   - System monitoring requires real-time updates
   - Netlink provides immediate notification of changes
   - No polling overhead
   - Low latency communication

2. **Multiple Consumers**
   - Both TUI and Web UI need system metrics
   - Netlink's multicast capability allows multiple clients
   - Efficient broadcast of updates to all listeners

3. **Efficient Data Transfer**
   - Binary protocol for efficient data transmission
   - No text parsing overhead
   - Structured message format
   - Optimized for system metrics

4. **Event-Driven Architecture**
   - Asynchronous updates when data changes
   - Natural fit for monitoring applications
   - Better resource utilization
   - Reduced system load

5. **Scalability**
   - Easy to add new monitoring clients
   - Efficient handling of multiple connections
   - Built-in support for message queuing
   - Good performance under load

6. **Modern Approach**
   - Widely used in modern kernel modules
   - Good community support
   - Well-documented in kernel
   - Active development and improvements

While other approaches like procfs or sysfs might be simpler to implement, they would require polling and introduce unnecessary overhead. Character devices, while flexible, would require more complex protocol design and lack native multicast support.

Netlink sockets provide the perfect balance of:
- Real-time updates
- Efficient communication
- Multiple client support
- Structured data transfer
- Event-driven architecture

This makes them ideal for system monitoring applications where real-time performance and multiple consumers are key requirements.

### Implementation Impact

Our choice of Netlink sockets influenced the architecture in several ways:

1. **Kernel Module**
   - Implements Netlink message sender
   - Efficient metric collection
   - Binary data formatting
   - Event-based updates

2. **Daemon Service**
   - Acts as Netlink message receiver
   - Converts binary data to JSON
   - Provides WebSocket interface
   - Handles multiple clients

3. **Client Applications**
   - Connect via WebSocket
   - Receive real-time updates
   - No polling required
   - Efficient data processing

This architecture provides a robust, efficient, and scalable solution for real-time system monitoring.