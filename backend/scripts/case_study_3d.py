import os
import sys
import yaml
import numpy as np
import plotly.graph_objects as go

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

def run_3d_case_study():
    print("Initializing 3D NumPy Voxel Case Study...")
    
    # Material properties (using Bagasse/PLA for the case study)
    D_eff = 2.0e-12 # effective diffusivity (m2/s) - slightly elevated for visibility in fast simulation
    
    # Voxel Grid Parameters (Simulating a small tray section: 5cm x 5cm x 0.5cm)
    nx, ny, nz = 50, 50, 10
    Lx, Ly, Lz = 0.05, 0.05, 0.005
    dx, dy, dz = Lx/nx, Ly/ny, Lz/nz
    
    # Stability criterion for 3D FTCS
    dt_max = 0.5 / (D_eff * (1/(dx**2) + 1/(dy**2) + 1/(dz**2)))
    dt = dt_max * 0.9 # stable step size in seconds
    
    # Simulating 30 days
    total_days = 30
    total_steps = int((total_days * 86400) / dt)
    print(f"Running {total_steps} time steps (dt = {dt:.2f}s)...")
    
    # Initialize concentration field (Base Moisture Content, dry state)
    C = np.ones((nx, ny, nz)) * 0.05 
    
    # Define Geometry Mask (Prismatic Tray)
    # 1 = Material (Solid), 0 = Empty Space (Air)
    # Base of the tray is bottom 2 voxels. Walls are outer 5 voxels.
    geom = np.zeros((nx, ny, nz))
    geom[:, :, :2] = 1.0 # Flat base
    geom[:5, :, :] = 1.0 # Left wall
    geom[-5:, :, :] = 1.0 # Right wall
    geom[:, :5, :] = 1.0 # Front wall
    geom[:, -5:, :] = 1.0 # Back wall
    
    # Boundary Conditions Mask
    # Exterior environment is Tropical (RH ~ 0.85 -> equilibrium moisture ~ 0.15)
    # Interior is sealed food environment (RH ~ 0.5 -> equilibrium moisture ~ 0.05)
    C_ext = 0.15
    
    # Identify exterior boundary voxels
    boundary_mask = np.zeros((nx, ny, nz), dtype=bool)
    boundary_mask[0, :, :] = True
    boundary_mask[-1, :, :] = True
    boundary_mask[:, 0, :] = True
    boundary_mask[:, -1, :] = True
    boundary_mask[:, :, 0] = True # Bottom face exposed
    
    # Time Stepping (3D FTCS via NumPy slices)
    alpha_x = D_eff * dt / (dx**2)
    alpha_y = D_eff * dt / (dy**2)
    alpha_z = D_eff * dt / (dz**2)
    
    for step in range(total_steps):
        # Enforce Boundary Conditions
        C[boundary_mask] = C_ext
        
        # Compute Laplacian via slicing
        C_next = C[1:-1, 1:-1, 1:-1] + \
                 alpha_x * (C[2:, 1:-1, 1:-1] - 2*C[1:-1, 1:-1, 1:-1] + C[:-2, 1:-1, 1:-1]) + \
                 alpha_y * (C[1:-1, 2:, 1:-1] - 2*C[1:-1, 1:-1, 1:-1] + C[1:-1, :-2, 1:-1]) + \
                 alpha_z * (C[1:-1, 1:-1, 2:] - 2*C[1:-1, 1:-1, 1:-1] + C[1:-1, 1:-1, :-2])
        
        # Update field in place to save memory
        C[1:-1, 1:-1, 1:-1] = C_next
        
        # Enforce geometry (moisture only exists in the solid)
        C = C * geom
        
        if step % max(1, (total_steps // 10)) == 0:
            print(f"Progress: {step/total_steps * 100:.0f}%")
            
    # Output Visualization: Corner vs Center Slice
    # Take a mid-height slice across the tray base
    z_slice_idx = 1 # Bottom base is z=0 and z=1
    slice_2d = C[:, :, z_slice_idx]
    
    fig = go.Figure(data=go.Heatmap(
        z=slice_2d,
        colorscale='Viridis',
        colorbar=dict(title='Moisture Concentration')
    ))
    fig.update_layout(
        title=f"3D Case Study: Moisture Gradient in Tray Base (Day {total_days})<br>Notice accelerated edge/corner accumulation",
        xaxis_title="Width (Voxels)",
        yaxis_title="Length (Voxels)",
        width=800,
        height=800
    )
    
    out_path = os.path.join(os.path.dirname(__file__), "fig_3d_case_study.html")
    fig.write_html(out_path)
    print(f"3D Case study complete. High-impact plot saved to {out_path}")

if __name__ == "__main__":
    run_3d_case_study()
