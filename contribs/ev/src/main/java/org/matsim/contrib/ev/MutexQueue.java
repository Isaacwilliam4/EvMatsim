package org.matsim.contrib.ev;

import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.locks.Lock;
import java.util.Queue;

public class MutexQueue {
    private static final Lock lock = new ReentrantLock();

    private static Queue<String> queue;

    public static void criticalSection() {
        lock.lock();  // Lock the mutex (this is the equivalent of acquiring a lock)
        try {
            // Critical section code goes here
            System.out.println(Thread.currentThread().getName() + " is executing the critical section");
        } finally {
            lock.unlock();  // Always unlock the mutex (this is equivalent to releasing the lock)
        }
    }

    public static void runMatsimInstance(String configPath) {
        // This method simulates running a Matsim instance
        System.out.println(Thread.currentThread().getName() + " is running a Matsim instance");
    }

    public static void main(String[] args) {
        Runnable task = () -> {
            criticalSection();
        };

        Thread t1 = new Thread(task);
        Thread t2 = new Thread(task);
        t1.start();
        t2.start();
    }
    
}
