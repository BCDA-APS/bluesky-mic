import os
import h5py

def write_master_h5(master_filename:str,
                    basedir:str,
                    sample_name:str,
                    master_path:str = None,
                    det_names:list = ["xspress3", "tetramm", "positions"],
                    det_file_ext:list = [".h5", ".nc", '.h5'],
                    det_key:list = ["/entry", None, "/stream"]):
    
    if master_path is None:
        master_path = os.path.join(os.path.join(basedir, sample_name), f"{sample_name}_{master_filename}")

    with h5py.File(master_path, 'w') as f:
        for det_name, file_ext, det_k in zip(det_names, det_file_ext, det_key):
            group = f.create_group(det_name)
            det_dir = os.path.join(*[basedir, sample_name, det_name])
            files = [fn for fn in os.listdir(det_dir) if file_ext in fn]
            if all([file_ext != ".nc", file_ext != ".mda"]):
                for i, fn in enumerate(files):
                    group[f'{fn}'] = h5py.ExternalLink(os.path.join(*[basedir, sample_name, det_name, fn]), det_k)
            else:
                for i, fn in enumerate(files):
                    group[f'{fn}'] = os.path.join(*[basedir, sample_name, det_name, fn])

    print(f"Master file ({master_path}) has been created successfully")
    

# ## Example to call the function
# write_master_h5(master_filename="master_2.h5", basedir=basedir, sample_name=sample_name)

# ## Example to view the content
# mpath = "/mnt/micdata1/save_dev/test_sam/test_sam_master_2.h5"
# with h5py.File(mpath, 'r') as f:
#     keys = f.keys()
#     # print(f"{keys=}")
#     for k in keys:
#         print(f"{k}: {f[k].keys()}")
#         k1 = f[k].keys()
#         for k_ in k1:
#             try:
#                 print(f"{k}-{k_}: {f[k][k_].keys()}")
#                 k2 = f[k][k_].keys()
#                 for k__ in k2:
#                     try:
#                         print(f"{k}-{k_}-{k__}: {f[k][k_][k__][:]}")
#                     except:
#                         print(f"{k}-{k_}-{k__}: {f[k][k_][k__].keys()}")
#             except:
#                 print(f"{k}-{k_}: {f[k][k_][()]}")