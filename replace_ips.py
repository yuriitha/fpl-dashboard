import os
import re

directory = r"e:\Documents\python\opt\fpl-dashboard-main"
comment_pattern = re.compile(r'^\s*#.*$')
count = 0

for root, _, files in os.walk(directory):
    for f in files:
        if f.endswith('.py') and f != "replace_ips.py":
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            new_lines = []
            modified = False
            for line in lines:
                original = line

                if "localhost" in line:
                    line = line.replace("localhost", "localhost")
                    modified = True


                if not comment_pattern.match(line):
                    new_lines.append(line)
                else:
                    modified = True

            if modified:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.writelines(new_lines)
                count += 1

print(f"Processed {count} files.")
