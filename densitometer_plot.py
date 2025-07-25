import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import linregress

def calculate_log_e(ev, exposure_time):
    """Calculate Log E from EV and exposure time"""
    lux = 2.5 * (2 ** ev)
    return np.log10(lux * 1000 * exposure_time)

def calculate_contrast_index(x_values, y_values, window_size=11):
    """Calculate contrast index using sliding window to find most linear portion in log scale"""
    if len(x_values) < window_size or len(y_values) < window_size:
        print(f"Warning: Not enough data points. Need at least {window_size} points")
        return None, None
        
    best_r_value = 0
    best_points = None
    
    # Convert to numpy arrays and ensure they're sorted by x values
    x = np.array(x_values)
    y = np.array(y_values)
    sort_idx = np.argsort(x)
    x = x[sort_idx]
    y = y[sort_idx]
    
    # Convert x values to log scale for finding linear portion
    log_x = np.log10(x)
    
    for i in range(len(x) - window_size + 1):
        window_log_x = log_x[i:i+window_size]
        window_y = y[i:i+window_size]
        
        # Calculate linear regression in log space
        _, _, r_value, _, _ = linregress(window_log_x, window_y)
        
        # Update if this window has better linearity
        if abs(r_value) > abs(best_r_value):
            best_r_value = r_value
            best_points = (x[i], y[i], x[i+window_size-1], y[i+window_size-1])
    
    if best_points and abs(best_r_value) > 0.98:
        logexp_a, density_a = best_points[0], best_points[1]
        logexp_b, density_b = best_points[2], best_points[3]
        # Calculate contrast index using the log difference
        contrast_index = (density_b - density_a) / (logexp_b - logexp_a)
        print(f"R² value for contrast index calculation: {best_r_value**2:.4f}")
        return contrast_index, best_points
    
    print("Could not find a suitable linear region with 5 points (R² > 0.98)")
    return None, None

def calculate_average_gradient(x_values, y_values, dmin):
    """Calculate average gradient between Dmin+0.1 and Dmin+0.6"""
    lower_density = dmin + 0.1
    upper_density = dmin + 0.6

    # Find closest indices
    idx1 = np.abs(y_values - lower_density).argmin()
    idx2 = np.abs(y_values - upper_density).argmin()

    if idx1 == idx2:
        print("Warning: Could not find two distinct points for average gradient.")
        return None

    log_e1 = x_values[idx1]
    log_e2 = x_values[idx2]

    grad = (y_values[idx2] - y_values[idx1]) / (log_e2 - log_e1)

    return grad

def plot_densitometry(step_wedge_file, test_film_file, ev, exposure_time, name, dmin, dmax):
    # Read the CSV files
    step_wedge = pd.read_csv(step_wedge_file)
    test_film = pd.read_csv(test_film_file)
    
    # Calculate Log E
    log_e = calculate_log_e(ev, exposure_time)
    
    # Ensure we only use the minimum number of measurements between both files
    min_measurements = min(len(step_wedge), len(test_film))
    
    # Calculate x-axis values (Log E - step wedge measurements)
    x_values = log_e - step_wedge['density'].iloc[:min_measurements]
    y_values = test_film['density'].iloc[:min_measurements]
    
    # Calculate contrast index
    contrast_index, best_points = calculate_contrast_index(x_values, y_values)

    # Print info about measurements
    print(f"Step wedge measurements: {len(step_wedge)}")
    print(f"Test film measurements: {len(test_film)}")
    print(f"Using first {min_measurements} measurements")
    # Calculate ISO speed
    if dmin:
        min_density = dmin
    else:
        min_density = min(y_values)
    target_density = min_density + 0.1
    
    above = np.where(y_values >= target_density)[0]
    below = np.where(y_values < target_density)[0]

    if len(above) > 0 and len(below) > 0:
        idx_above = above[0]
        idx_below = below[-1]
        # Linear interpolation
        x1, y1 = x_values[idx_below], y_values[idx_below]
        x2, y2 = x_values[idx_above], y_values[idx_above]
        if x2 != x1:
            log_e_at_target = x1 + (target_density - y1) * (x2 - x1) / (y2 - y1)
        else:
            log_e_at_target = x1  # fallback if points are the same
    else:
        # Fallback to closest if interpolation is not possible
        closest_idx = np.abs(y_values - target_density).argmin()
        log_e_at_target = x_values[closest_idx]
    
    # Calculate ISO speed: 800/10^LogE
    iso_speed = int(800 / (10 ** log_e_at_target))
    
    # Calculate average gradient
    avg_grad = calculate_average_gradient(x_values, y_values, min_density)

    if avg_grad:
        iso_ok = 0.62 <= avg_grad <= 0.70
        print(f"Average Gradient: {avg_grad:.3f} ({'OK' if iso_ok else 'Out of ISO Range 0.62-0.70'})")
    else:
        print("Could not calculate average gradient.")

    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Add a marker for the ISO speed point (speed point)
    ax.scatter([log_e_at_target], [target_density], color='orange', s=100, zorder=5, label='ISO Speed Point')
    ax.annotate(f"Speed Point\n(LogE={log_e_at_target:.2f}, D={target_density:.2f})",
                (log_e_at_target, target_density),
                textcoords="offset points", xytext=(10,-20), ha='left', color='orange', fontsize=7,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

    # Plot the characteristic curve
    ax.plot(x_values, y_values, 'bo-', label='Film Response')
    min_grad = 0.62
    max_grad = 0.70

    if avg_grad < min_grad:
        grad_status = "Too Low"
    elif avg_grad > max_grad:
        grad_status = "Too High"
    else:
        grad_status = "OK"

    # Add contrast index and ISO speed values below the graph
    if contrast_index and best_points:
        plt.figtext(0.5, 0.05, 
                    f'Contrast Index: {contrast_index:.2f}    ISO Speed: {iso_speed}    Avg. Gradient: {avg_grad:.2f} ({grad_status})', 
                    ha='center', va='center',
                    bbox=dict(facecolor='white', alpha=0.8))
        # Plot the line segment used for contrast index
        ax.plot([best_points[0], best_points[2]], 
                [best_points[1], best_points[3]], 
                'r-', linewidth=2, label='Contrast Index Region')
    else:
        plt.figtext(0.5, 0.05, 
                   f'ISO Speed: {iso_speed}', 
                   ha='center', va='center',
                   bbox=dict(facecolor='white', alpha=0.8))



    # Set logarithmic scale for x-axis
    plt.semilogx()
    ax.xaxis.set_major_formatter(plt.ScalarFormatter())
    ax.xaxis.set_minor_formatter(plt.ScalarFormatter())
    ax.xaxis.set_major_locator(plt.LogLocator(base=10.0))
    ax.xaxis.set_minor_locator(plt.LogLocator(base=10.0, subs=np.arange(2, 10)))
    ax.xaxis.set_tick_params(which='minor', labelsize=8)

    # Ensure all tick labels are visible
    plt.setp(ax.get_xticklabels(), rotation=15, ha='right')

    # Customize the plot
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.xlabel('Log E (lux-seconds)')
    plt.ylabel('Density')
    plt.title(f'Film Characteristic Curve\nEV: {ev}, Exposure Time: {exposure_time}s\n{name}')
    plt.legend()
    
    # Add density reference lines
    plt.axhline(y=min_density, color='gray', linestyle='--', alpha=0.5, label='Toe')
    if (dmax):
        max_density = dmax
    else:
        max_density = max(y_values)
    plt.axhline(y=max_density, color='gray', linestyle='--', alpha=0.5, label='Shoulder')

    # Adjust layout to make room for contrast index text
    plt.subplots_adjust(bottom=0.15)

    plt.show()

def main():
    parser = argparse.ArgumentParser(description='Film Densitometry Plot Generator')
    parser.add_argument('-ev', type=float, help='Exposure Value (EV)', required=True)
    parser.add_argument('-t', '--exposure_time', type=float, help='Exposure time in seconds', required=True)
    parser.add_argument('-s', '--step_wedge', type=str, help='Path to step wedge CSV file', required=True)
    parser.add_argument('-f', '--film', type=str, help='Path to test film CSV file', required=True)
    parser.add_argument('-n', '--name', type=str, help='Name of the test film', required=True)
    parser.add_argument('-d', '--dmin', type=float, help='Minimum density value for the film', required=True)
    parser.add_argument('-dx', '--dmax', type=float, help='Minimum density value for the film', required=False)

    args = parser.parse_args()
    
    plot_densitometry(args.step_wedge, args.film, 
                     args.ev, args.exposure_time, args.name, args.dmin, args.dmax)
    print(f"Plot generated for {args.name} with EV: {args.ev} and exposure time: {args.exposure_time}s")

if __name__ == "__main__":
    main()