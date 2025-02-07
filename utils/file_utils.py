import os
import sys
import aiofiles
import asyncio

async def read_pipe():
    """Read piped input asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sys.stdin.read)

async def read_file(file_path):
    """
    Asynchronously reads content from a file.
    """
    try:
        async with aiofiles.open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
            file_content = await file.read()
            print(f"Reading file {file_path}:")
            return file_content
    except Exception as e:
        return f"Error reading file {file_path}: {e}"

async def read_folder(folder_path):
    """
    Asynchronously reads all files in a folder and returns their contents along with the folder structure.
    """
    print(f"Analyzing folder {folder_path}:")
    try:
        # List files and folders synchronously using os
        files = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]
        folders = [
            f for f in os.listdir(folder_path)
            if os.path.isdir(os.path.join(folder_path, f))
        ]

        if not files and not folders:
            return f"The folder '{folder_path}' is empty."

        structure = f"Folder Structure of '{folder_path}':\n"
        if folders:
            structure += "\nSubfolders:\n" + "\n".join(folders)
        if files:
            structure += "\n\nFiles:\n" + "\n".join(files)

        # Read content from each file asynchronously
        file_contents = "\n\n### File Contents ###\n"
        for file in files:
            file_path = os.path.join(folder_path, file)
            try:
                async with aiofiles.open(file_path, 'r', encoding="utf-8", errors="ignore") as f:
                    content = await f.read()
                file_contents += f"\n--- {file} ---\n{content.strip()}\n"
            except Exception as e:
                file_contents += f"\n--- {file} ---\nError reading file: {e}\n"

        return structure + file_contents

    except PermissionError:
        return f"Error: Permission denied to access '{folder_path}'."

