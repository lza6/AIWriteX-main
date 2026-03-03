import sys

file_path = r"c:\Users\Administrator.DESKTOP-EGNE9ND\Desktop\AIxs\AIWriteX-main\src\ai_write_x\web\api\generate.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "def batch_generate_worker(" in line:
        start_idx = i - 1 # include the comment above
    if "sys.exit(1)" in line and start_idx != -1:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    worker_lines = lines[start_idx:end_idx+1]
    # Unindent worker_lines by 8 spaces
    worker_lines = [line[8:] if line.startswith('        ') else line for line in worker_lines]
    
    # Find where to put it: above @router.post("/generate")
    insert_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('@router.post("/generate")'):
            insert_idx = i
            break
            
    if insert_idx != -1:
        new_lines = lines[:insert_idx] + worker_lines + ['\n'] + lines[insert_idx:start_idx] + lines[end_idx+1:]
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("Successfully moved batch_generate_worker")
    else:
        print("Could not find @router.post('/generate')")
else:
    print("Could not find batch_generate_worker")
