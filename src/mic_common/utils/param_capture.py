"""
Parameter capture utility.

This module provides a function that captures the input parameters of a function
and optionally saves them to an HDF5 file.

@author: yluo(grace227)
"""

import inspect
from typing import Any, Callable, Dict
import h5py
from pathlib import Path


def capture_params(func: Callable, *args, h5_file_path: str = None, 
                  group_name: str = "parameters", save_to_h5: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Capture function parameters and optionally save them to an HDF5 file.
    
    This function captures the parameters of a function call and can optionally write them to an HDF5 file.
    It's useful for logging function parameters for later analysis or debugging.
    
    Parameters
    ----------
    func : Callable
        The function to capture parameters from.
    *args : Any
        Positional arguments passed to the function.
    h5_file_path : str, optional
        Path to the HDF5 file. If None, a default name will be generated.
    group_name : str, optional
        Name of the HDF5 group to store parameters in. Default is "parameters".
    save_to_h5 : bool, optional
        Whether to save parameters to HDF5 file. Default is False.
    **kwargs : Any
        Keyword arguments passed to the function.
    
    Returns
    -------
    Dict[str, Any]
        Dictionary containing the captured parameters.
    
    Examples
    --------
    # Capture parameters only (no HDF5 saving)
    params = capture_params(
        fly2d,
        samplename="test_sample",
        width=10.0,
        height=5.0,
        save_to_h5=False
    )
    
    # Capture parameters and save to HDF5
    params = capture_params(
        fly2d,
        samplename="test_sample",
        width=10.0,
        height=5.0,
        h5_file_path="scan_parameters.h5",
        save_to_h5=True
    )
    
    # The parameters are returned as a dictionary
    print(params)
    """
    # Get function signature
    sig = inspect.signature(func)
    
    # Bind arguments to parameters
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()
    
    # Convert to dictionary
    params_dict = dict(bound_args.arguments)
    
    # Only save to HDF5 if requested
    if save_to_h5:
        # Generate default filename if none provided
        if h5_file_path is None:
            func_name = func.__name__
            h5_file_path = f"{func_name}_parameters.h5"
        
        # Ensure the file path is a Path object
        h5_path = Path(h5_file_path)
        
        try:
            # Write parameters to HDF5 file
            with h5py.File(h5_path, 'a') as f:
                # Create or get the parameters group
                if group_name in f:
                    del f[group_name]  # Remove existing group to overwrite
                
                param_group = f.create_group(group_name)
                
                # Add function metadata
                param_group.attrs['function_name'] = func.__name__
                param_group.attrs['module_name'] = func.__module__
                
                # Write each parameter
                for param_name, param_value in params_dict.items():
                    try:
                        # Handle different data types
                        if isinstance(param_value, (int, float, str, bool)):
                            param_group.attrs[param_name] = str(param_value)
                        elif param_value is None:
                            param_group.attrs[param_name] = "None"
                        else:
                            # For complex types, convert to string representation
                            param_group.attrs[param_name] = str(param_value)
                            
                    except Exception as e:
                        # If we can't write the parameter as an attribute, try as a dataset
                        try:
                            if isinstance(param_value, (list, tuple)):
                                param_group.create_dataset(param_name, data=param_value)
                            else:
                                param_group.attrs[param_name] = str(param_value)
                        except:
                            # Last resort: store as string
                            param_group.attrs[param_name] = str(param_value)
                
                # Add timestamp
                from datetime import datetime
                param_group.attrs['timestamp'] = datetime.now().isoformat()
                
            print(f"Parameters saved to HDF5 file: {h5_path}")
            
        except Exception as e:
            print(f"Warning: Could not save parameters to HDF5 file: {e}")
    else:
        print("Parameters captured (HDF5 saving disabled)")
    
    return params_dict
