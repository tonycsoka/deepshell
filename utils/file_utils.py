import os
from sre_compile import NOT_LITERAL_LOC_IGNORE
import sys
import aiofiles
import asyncio
from chat.streamer import rich_print


class FileUtils:
    def __init__(self, ignore_files=None, ignore_folders=None, scan_dot_folders=False):
        """
        Initializes the FileUtils with customizable options to ignore certain files and folders.

        :param ignore_files: List of file extensions to ignore.
        :param ignore_folders: List of folder names to ignore.
        :param scan_dot_folders: Whether to scan hidden folders (those starting with a dot). Default is False.
        """
        self.default_ignore_files = [
            '.pyc', '.pyo', '.log', '.bak', '.exe', '.bin', '.dll', '.so', '.app', '.zip',
            '.tar', '.gz', '.bz2', '.xz', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            '.mp3', '.wav', '.flac', '.mp4', '.avi', '.mkv', '.mov', '.apk', '.ipa', '.DS_Store'
        ]
        self.default_ignore_folders = ['__pycache__', '.git', '.svn', '.hg']
        
        self.ignore_files = ignore_files or self.default_ignore_files
        self.ignore_folders = ignore_folders or self.default_ignore_folders
        self.scan_dot_folders = scan_dot_folders

    async def read_pipe(self):
        """Read piped input asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sys.stdin.read)

    async def read_file(self, file_path, root_folder=None):
        """Asynchronously reads content from a file, skipping ignored files."""
        if not root_folder:
            await rich_print(f"Reading {file_path}") 
        try:
            if any(file_path.endswith(ext) for ext in self.ignore_files):
                return f"Skipping file (ignored): {file_path}"
            
            relative_path = os.path.relpath(file_path, root_folder) if root_folder else file_path
            
            async with aiofiles.open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
                return f"--------- {relative_path} ---------\n" + await file.read()
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    async def generate_structure(self, folder_path, root_folder, prefix=""):
        """Generates a textual representation of the folder structure."""
        structure = f"{prefix}{os.path.basename(folder_path)}/\n"
        items = sorted(os.listdir(folder_path))
        
        for item in items:
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path) and item not in self.ignore_folders and (self.scan_dot_folders or not item.startswith('.')):
                structure += await self.generate_structure(item_path, root_folder, prefix + "--")
            elif os.path.isfile(item_path) and not any(item.endswith(ext) for ext in self.ignore_files):
                relative_path = os.path.relpath(item_path, root_folder) if root_folder else item_path
                structure += f"{prefix}-- {relative_path}\n"
        
        return structure

    async def read_folder(self, folder_path, root_folder=None):
        """Recursively scans and reads all files in a folder, respecting ignore lists."""
        await rich_print(f"Reading {folder_path}")
        if root_folder is None:
            root_folder = folder_path
        
        try:
            await rich_print(f"Generating structure for {folder_path}")
            structure = await self.generate_structure(folder_path, root_folder)
            file_contents = "\n\n### File Contents ###\n"
            
            for root, _, files in os.walk(folder_path):
                if any(ignored in root.split(os.sep) for ignored in self.ignore_folders):
                    continue  # Skip ignored folders
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if not any(file.endswith(ext) for ext in self.ignore_files):
                        content = await self.read_file(file_path, root_folder)
                        file_contents += f"\n{content.strip()}\n"
            
            return structure + file_contents
        
        except PermissionError:
            return f"Error: Permission denied to access '{folder_path}'."

    async def search_files(self, missing_path, search_dir=None, max_results=10):
        """
        Searches for a missing file or folder in the specified directory.
        Defaults to the home directory if none is provided.
        """
        if not search_dir:
            search_dir = os.path.expanduser("~")

        results = []
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]

            for name in files + dirs:
                if missing_path.lower() in name.lower():
                    results.append(os.path.join(root, name))
                    if len(results) >= max_results:
                        return results  # Stop searching if max results reached

        return results
