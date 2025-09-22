/******************************************************
 * Program: Recursive Fibonacci Sequence in Java
 * Author: Miroslaw Staron
 * Generated with the assistance of ChatGPT
 * 
 * Description:
 *   This program computes Fibonacci numbers using
 *   a recursive implementation. The user provides
 *   how many terms should be generated, and the
 *   program prints the sequence to the console.
 * 
 * Notes:
 *   - Recursive implementation is elegant but may
 *     be inefficient for large inputs.
 *   - For performance, memoization or iteration
 *     should be considered in real-world systems.
 * 
 * Additional Information:
 *   This code was generated with ChatGPT and is 
 *   shared in the context of research and teaching.
 *   For more information about software engineering 
 *   research and industry collaboration, please visit:
 *   https://software-center.se
 ******************************************************/

import java.util.Scanner;  

public class RecursiveFibonacci {  

    // Recursive function to calculate Fibonacci number at position n
    public static int fibonacci(int n) {  

        // Base case: if n is 0, return 0
        if (n == 0)  
            return 0;  

        // Base case: if n is 1, return 1
        else if (n == 1)  
            return 1;  

        // Recursive case: sum of previous two terms
        else  
            return fibonacci(n - 1) + fibonacci(n - 2);  
    }  

    public static void main(String[] args) {  

        // Create scanner object to read input
        Scanner scanner = new Scanner(System.in);  

        // Ask user for input
        System.out.print("Enter the number of terms: ");  

        // Read input from user
        int terms = scanner.nextInt();  

        // Check if input is valid
        if (terms <= 0) {  

            // Error message if not valid
            System.out.println("Please enter a positive integer.");  
        }  
        else {  

            // Print header message
            System.out.println("Fibonacci Sequence up to " + terms + " terms:");  

            // Loop through and print each Fibonacci number
            for (int i = 0; i < terms; i++) {  

                // Call recursive function and print result
                System.out.print(fibonacci(i) + " ");  
            }  

            // Print newline after sequence
            System.out.println();  
        }  

        // Close scanner
        scanner.close();  
    }  
}
