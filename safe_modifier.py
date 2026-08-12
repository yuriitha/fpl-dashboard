import os
import io
import tokenize

def remove_comments_and_replace_ip(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source_code = f.read()

    # 1. Replace IP
    source_code = source_code.replace("194.99.22.193", "localhost")

    # 2. Remove comments safely using Python's tokenizer
    io_obj = io.StringIO(source_code)
    out = ""
    last_lineno = -1
    last_col = 0
    
    try:
        for tok in tokenize.generate_tokens(io_obj.readline):
            token_type = tok[0]
            token_string = tok[1]
            start_line, start_col = tok[2]
            end_line, end_col = tok[3]
            
            if start_line > last_lineno:
                last_col = 0
            
            # Add whitespace to preserve exact indentation and formatting
            if start_col > last_col:
                out += (" " * (start_col - last_col))
            
            if token_type == tokenize.COMMENT:
                pass # skip comment
            else:
                out += token_string
                
            last_lineno = end_line
            last_col = end_col
    except Exception as e:
        print(f"Failed to parse {filepath}: {e}")
        out = source_code # fallback to original if parsing fails
        
    # Optional: remove trailing whitespaces on lines
    clean_lines = [line.rstrip() for line in out.split('\n')]
    
    # Optional: remove multiple consecutive empty lines resulting from comment removal
    final_lines = []
    empty_count = 0
    for line in clean_lines:
        if line.strip() == "":
            empty_count += 1
            if empty_count <= 2: # allow at most 2 consecutive empty lines
                final_lines.append(line)
        else:
            empty_count = 0
            final_lines.append(line)
            
    final_out = '\n'.join(final_lines)

    # Write back safely
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_out)
    return True

directory = r"e:\Documents\python\opt\fpl-dashboard-main"
processed = 0

for root, _, files in os.walk(directory):
    for f in files:
        if f.endswith('.py') and f != "safe_modifier.py":
            filepath = os.path.join(root, f)
            remove_comments_and_replace_ip(filepath)
            processed += 1

print(f"Processed {processed} files successfully.")
