#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path
import datetime
import re

# ANSI color codes
YELLOW = "\033[93m"
RESET = "\033[0m"

def get_git_info(directory):
    """Get git tracked files and check if files are ignored by .gitignore"""
    try:
        # Get the root directory of the git repository
        git_root_result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True
        )
        git_root = Path(git_root_result.stdout.strip())

        # Get all tracked files in the repository
        tracked_result = subprocess.run(
            ['git', 'ls-files'],
            cwd=git_root,
            capture_output=True, text=True, check=True
        )

        # Convert relative paths to absolute paths for tracked files
        tracked_files = {git_root / line for line in tracked_result.stdout.strip().split('\n') if line}

        def is_ignored(file_path):
            """Check if a file is ignored by git"""
            rel_path = file_path.relative_to(git_root)
            result = subprocess.run(
                ['git', 'check-ignore', '-q', str(rel_path)],
                cwd=git_root
            )
            # Return code 0 means the file is ignored, 1 means it's not ignored
            return result.returncode == 0
            
        def get_git_last_modified(file_path):
            """Get the last modified date of a file from git"""
            try:
                rel_path = file_path.relative_to(git_root)
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%cd', '--date=iso', '--', str(rel_path)],
                    cwd=git_root,
                    capture_output=True, text=True, check=True
                )
                if result.stdout.strip():
                    # Parse the git date format
                    git_date = datetime.datetime.strptime(
                        result.stdout.strip(), '%Y-%m-%d %H:%M:%S %z'
                    )
                    return git_date.strftime('%Y-%m-%d %H:%M:%S')
                return None
            except (subprocess.CalledProcessError, ValueError):
                return None

        return tracked_files, is_ignored, git_root, get_git_last_modified
    except subprocess.CalledProcessError:
        print(f"{YELLOW}Warning: Error running git commands in {directory}. Not a git repository or git not installed.{RESET}")
        return set(), lambda path: False, Path(directory)
    except Exception as e:
        print(f"{YELLOW}Warning: Unexpected error getting git information: {e}{RESET}")
        return set(), lambda path: False, Path(directory)

def generate_index(directory):
    """Generate an index.html file for the given directory."""
    path = Path(directory).resolve()

    # Get git information: tracked files and function to check if files are ignored
    all_git_tracked_files, is_git_ignored, git_root, get_git_last_modified = get_git_info(os.getcwd())

    # Get all files and directories in the current directory
    all_items = [p for p in path.iterdir() if p.name != '.git' and not p.name.endswith('~')]

    # Filter items based on git tracking status and .gitignore
    tracked_items = []
    warnings = []

    for item in all_items:
        # Skip items that are ignored by .gitignore
        try:
            if is_git_ignored(item):
                continue
        except (ValueError, Exception):
            # If the file can't be checked (e.g., it's outside the git repo), don't skip it
            pass

        if item.is_dir():
            # For directories, check if any files inside are tracked
            dir_has_tracked_files = any(
                tracked_file.is_relative_to(item)
                for tracked_file in all_git_tracked_files
            )
            if dir_has_tracked_files:
                tracked_items.append(item)
        else:
            # For files, check if it's tracked
            if item.resolve() in all_git_tracked_files:
                tracked_items.append(item)
            else:
                # Don't warn about index.html files since we're generating them
                if item.name != 'index.html':
                    warnings.append(f"Warning: {item.name} is not tracked by git")

    # Sort items (directories first, then files)
    items = sorted(tracked_items, key=lambda p: (p.is_file(), p.name.lower()))

    # HTML template for the index page
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Index of {path.name or path}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{
            padding: 20px;
        }}
        .directory {{
            font-weight: bold;
            color: #0d6efd;
        }}
        .file {{
            color: #212529;
        }}
        .file-size {{
            color: #6c757d;
            text-align: right;
        }}
        .last-modified {{
            color: #6c757d;
        }}
        .table-hover tbody tr:hover {{
            background-color: rgba(13, 110, 253, 0.1);
        }}
        /* GitHub markdown styles */
        .markdown-body {{
            font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji";
            font-size: 16px;
            line-height: 1.5;
            word-wrap: break-word;
            padding: 15px;
        }}
        .markdown-body pre {{
            border-radius: 3px;
            background-color: #f6f8fa;
            padding: 16px;
            overflow: auto;
        }}
        .markdown-body code {{
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 85%;
            background-color: rgba(175, 184, 193, 0.2);
            border-radius: 6px;
        }}
        .markdown-body pre code {{
            background-color: transparent;
            padding: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Index of {path.name or path}</h1>

        <div class="mb-3">
            <a href="../" class="btn btn-outline-primary btn-sm">&laquo; Parent Directory</a>
        </div>

        <table class="table table-hover">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Last Modified</th>
                </tr>
            </thead>
            <tbody>
'''

    # Add entries for each item
    for item in items:
        if item.name == 'index.html':
            continue  # Skip the index file itself

        is_dir = item.is_dir()
        name = f"{item.name}/"  if is_dir else item.name
        size = "-" if is_dir else format_size(item.stat().st_size)
        
        # Get last modified date from git if available, otherwise use filesystem
        git_last_modified = get_git_last_modified(item)
        if git_last_modified:
            last_modified = git_last_modified
        else:
            last_modified = datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')

        item_class = "directory" if is_dir else "file"

        html += f'''                <tr>
                    <td><a href="{item.name}{"/" if is_dir else ""}" class="{item_class}">{name}</a></td>
                    <td class="file-size">{size}</td>
                    <td class="last-modified">{last_modified}</td>
                </tr>
'''

    html += '''            </tbody>
        </table>
'''

    # Print warnings about untracked files to console in yellow
    if warnings:
        print(f"\nIn directory '{path}':")
        for warning in warnings:
            print(f"  {YELLOW}{warning}{RESET}")

    # Check if README.md exists and add its content
    readme_path = path / 'README.md'
    if readme_path.exists():
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
        except UnicodeDecodeError:
            try:
                # Try another common encoding if utf-8 fails
                with open(readme_path, 'r', encoding='latin-1') as f:
                    readme_content = f.read()
            except Exception:
                readme_content = "Error: Could not read README.md file due to encoding issues."

        # Properly escape content for JavaScript
        escaped_content = (
            readme_content
            .replace('\\', '\\\\')
            .replace('`', '\\`')
            .replace('${', '\\${')
            .replace('\r\n', '\\n')
            .replace('\n', '\\n')
        )

        html += f'''
        <div class="card mt-4">
            <div class="card-header py-2">
                <h5 class="card-title mb-0">README.md</h5>
            </div>
            <div class="card-body">
                <div id="readme-content" class="markdown-body">
                    <!-- Content will be rendered by marked.js -->
                </div>
            </div>
        </div>

        <!-- GitHub-style markdown rendering -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5.2.0/github-markdown-light.css">
        <script src="https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const readmeContent = document.getElementById('readme-content');
                if (readmeContent) {{
                    // Configure marked for GitHub-flavored markdown
                    marked.setOptions({{
                        gfm: true,
                        breaks: true,
                        headerIds: true,
                        highlight: function(code, lang) {{
                            if (window.hljs) {{
                                try {{
                                    return hljs.highlightAuto(code).value;
                                }} catch(e) {{}}
                            }}
                            return code;
                        }}
                    }});

                    // Render the markdown
                    readmeContent.innerHTML = marked.parse(`{escaped_content}`);
                }}
            }});
        </script>
        <script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.7.0/build/highlight.min.js"></script>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.7.0/build/styles/github.min.css">
'''

    html += '''
    </div>
</body>
</html>'''

    # Write the index.html file
    index_path = path / 'index.html'
    with open(index_path, 'w') as f:
        f.write(html)

    # Add the generated index.html file to git
    try:
        subprocess.run(
            ['git', 'add', str(index_path)],
            check=True, capture_output=True
        )
        print(f"Generated and git-added {index_path}")
    except subprocess.CalledProcessError as e:
        print(f"{YELLOW}Generated {index_path} but failed to git add: {e}{RESET}")

def format_size(size):
    """Format file size in a human-readable way."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024 or unit == 'TB':
            return f"{size:.2f} {unit}".rstrip('0').rstrip('.') + ' ' + unit
        size /= 1024.0

def process_directory(root_dir):
    """Process the root directory and all its subdirectories recursively."""
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip .git directory - remove it from dirnames to prevent os.walk from traversing it
        if '.git' in dirnames:
            dirnames.remove('.git')
        generate_index(dirpath)

def main():
    root_dir = os.getcwd()

    if len(sys.argv) > 1:
        root_dir = sys.argv[1]

    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a directory")
        sys.exit(1)

    process_directory(root_dir)
    print(f"Index generation completed for {root_dir} and its subdirectories")

if __name__ == "__main__":
    main()
