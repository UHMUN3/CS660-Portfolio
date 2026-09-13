public class SampleFibonacci {

    // Global variable to prevent race condition: Note incrementCounter()
    static int counter = 0;

    // Recursive Fibonacci function
    public static int fibonacci(int n) {
        if (n < 0) {
            // Note: Fibonacci numbers cannot be implemented for negative numbers.
            throw new IllegalArgumentException("Fibonacci is not defined for negative numbers");
        }
        if (n == 0) {
            return 0;
        } else if (n == 1) {
            return 1;
        }
        return fibonacci(n - 1) + fibonacci(n - 2);
    }

    static class Worker implements Runnable {
        private int threadId;
        private int n;

        public Worker(int threadId, int n) {
            this.threadId = threadId;
            this.n = n;
        }

        @Override
        public void run() {
            int result = fibonacci(n);

            incrementCounter();
            // Java implementation of f strings for Python
            System.out.printf("Thread %d: fibonacci(%d) = %d | Counter = %d%n", 
            threadId, n, result, counter);
        }
    }

    // Note: What is the intent of the incrementCounter()?
    public static synchronized void incrementCounter() {
        counter++;
    }

    // Main method to run the threads
    public static void main(String[] args) {
        // Create multiple threads calling fibonacci(2)
        Thread thread1 = new Thread(new Worker(1, 2));
        Thread thread2 = new Thread(new Worker(2, 2));
        Thread thread3 = new Thread(new Worker(3, 2));

        thread1.start();
        thread2.start();
        thread3.start();

        // Wait for threads to finish
        try {
            thread1.join();
            thread2.join();
            thread3.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        System.out.println("Final Counter Value: " + counter);
    }
}