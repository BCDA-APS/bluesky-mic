"""
Timer decorators and utilities for timing function execution and loop iterations.

This module provides decorators and utilities to measure execution time of functions
and individual iterations within loops.
"""

import time
import functools
from typing import Callable, Any, Optional, Union
from contextlib import contextmanager


def timer(func: Callable) -> Callable:
    """
    Basic timer decorator that measures total execution time of a function.
    
    Args:
        func: The function to time
        
    Returns:
        Wrapped function that prints execution time
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__} took {execution_time:.4f} seconds to execute")
        return result
    return wrapper


def loop_timer(description: str = "Iteration", print_every: int = 1) -> Callable:
    """
    Decorator for timing individual iterations in a loop.
    
    This decorator is designed to be used on functions that are called within loops.
    It tracks timing for each call and provides summary statistics.
    
    Args:
        description: Description prefix for timing output
        print_every: Print timing info every N iterations (default: 1)
        
    Returns:
        Decorated function that tracks timing
    """
    def decorator(func: Callable) -> Callable:
        # Store timing data in the function object
        if not hasattr(func, '_timing_data'):
            func._timing_data = {
                'total_calls': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'start_time': None
            }
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Start timing
            start_time = time.time()
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # End timing
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Update timing data
            timing_data = func._timing_data
            timing_data['total_calls'] += 1
            timing_data['total_time'] += execution_time
            timing_data['min_time'] = min(timing_data['min_time'], execution_time)
            timing_data['max_time'] = max(timing_data['max_time'], execution_time)
            
            # Print timing info based on print_every setting
            if timing_data['total_calls'] % print_every == 0:
                avg_time = timing_data['total_time'] / timing_data['total_calls']
                print(f"{description} {timing_data['total_calls']}: "
                      f"Current: {execution_time:.4f}s, "
                      f"Avg: {avg_time:.4f}s, "
                      f"Min: {timing_data['min_time']:.4f}s, "
                      f"Max: {timing_data['max_time']:.4f}s")
            
            return result
        
        # Add method to get timing summary
        def get_timing_summary():
            """Get a summary of all timing data."""
            timing_data = func._timing_data
            if timing_data['total_calls'] == 0:
                return "No timing data available"
            
            avg_time = timing_data['total_time'] / timing_data['total_calls']
            return {
                'total_calls': timing_data['total_calls'],
                'total_time': timing_data['total_time'],
                'average_time': avg_time,
                'min_time': timing_data['min_time'],
                'max_time': timing_data['max_time']
            }
        
        def reset_timing():
            """Reset all timing data."""
            func._timing_data = {
                'total_calls': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'start_time': None
            }
        
        # Attach utility methods to the wrapper
        wrapper.get_timing_summary = get_timing_summary
        wrapper.reset_timing = reset_timing
        
        return wrapper
    
    return decorator


@contextmanager
def loop_timer_context(description: str = "Loop", total_iterations: Optional[int] = None):
    """
    Context manager for timing entire loops with progress tracking.
    
    Args:
        description: Description for the loop being timed
        total_iterations: Total number of iterations (for progress calculation)
        
    Yields:
        Timer object with methods to track individual iterations
    """
    class LoopTimer:
        def __init__(self):
            self.start_time = time.time()
            self.iteration_times = []
            self.current_iteration = 0
            self.samy = None
            
        def iteration(self, iteration_num: Optional[int] = None, samy: Optional[float] = None):
            """Mark the start of an iteration."""
            if iteration_num is not None:
                self.current_iteration = iteration_num
            else:
                self.current_iteration += 1

            if samy is not None:
                self.samy = samy
            
            # Store start time for this iteration
            self.iteration_start = time.time()
            
        def end_iteration(self):
            """Mark the end of an iteration and record timing."""
            if hasattr(self, 'iteration_start'):
                iteration_time = time.time() - self.iteration_start
                self.iteration_times.append(iteration_time)
                
                # Calculate progress if total iterations provided
                if total_iterations:
                    progress = (self.current_iteration / total_iterations) * 100
                    avg_time = sum(self.iteration_times) / len(self.iteration_times)
                    remaining_iterations = total_iterations - self.current_iteration
                    eta = remaining_iterations * avg_time
                    if self.samy is not None:
                        samy_str = f"samy position: {self.samy:.2f}um"
                    else:
                        samy_str = f"samy position: {self.samy}"
                    
                    print(f"{description}: Line {self.current_iteration}/{total_iterations} "
                          f"({progress:.1f}%) - Remaining: {eta:.1f}s, "
                          f"Per line: {iteration_time:.2f}s, "
                          f"{samy_str}")
                else:
                    avg_time = sum(self.iteration_times) / len(self.iteration_times)
                    print(f"{description}: Line {self.current_iteration} - "
                          f"Time: {iteration_time:.4f}s, Avg: {avg_time:.4f}s")
        
        def get_summary(self):
            """Get timing summary for the entire loop."""
            if not self.iteration_times:
                return "No iterations completed"
            
            total_time = time.time() - self.start_time
            avg_time = sum(self.iteration_times) / len(self.iteration_times)
            min_time = min(self.iteration_times)
            max_time = max(self.iteration_times)
            
            return {
                'total_iterations': len(self.iteration_times),
                'total_time': total_time,
                'average_iteration_time': avg_time,
                'min_iteration_time': min_time,
                'max_iteration_time': max_time,
                'total_overhead': total_time - sum(self.iteration_times)
            }
    
    timer = LoopTimer()
    try:
        yield timer
    finally:
        # Print final summary
        summary = timer.get_summary()
        if isinstance(summary, dict):
            print(f"\n{description} completed:")
            print(f"  Total lines: {summary['total_iterations']}")
            print(f"  Total time: {summary['total_time']:.4f}s")
            print(f"  Average time per line: {summary['average_iteration_time']:.4f}s")
            print(f"  Min time per line: {summary['min_iteration_time']:.4f}s")
            print(f"  Max time per line: {summary['max_iteration_time']:.4f}s")
            if summary['total_overhead'] > 0:
                print(f"  Total overhead: {summary['total_overhead']:.4f}s")


# Example usage functions for demonstration
def example_basic_timer():
    """Example of using the basic timer decorator."""
    
    @timer
    def slow_function():
        time.sleep(0.1)
        return "Done"
    
    result = slow_function()
    return result


def example_loop_timer():
    """Example of using the loop timer decorator."""
    
    @loop_timer("Processing item", print_every=2)
    def process_item(item):
        time.sleep(0.05)  # Simulate processing
        return f"Processed {item}"
    
    # Simulate a loop
    for i in range(10):
        result = process_item(i)
    
    # Get timing summary
    summary = process_item.get_timing_summary()
    print(f"\nFinal summary: {summary}")
    
    # Reset timing
    process_item.reset_timing()


def example_context_manager():
    """Example of using the loop timer context manager."""
    
    # Simulate a loop with known total iterations
    with loop_timer_context("Data processing", total_iterations=5) as timer:
        for i in range(5):
            timer.iteration(i + 1)
            time.sleep(0.1)  # Simulate work
            timer.end_iteration()


if __name__ == "__main__":
    print("Basic timer example:")
    example_basic_timer()
    
    print("\nLoop timer example:")
    example_loop_timer()
    
    print("\nContext manager example:")
    example_context_manager()
