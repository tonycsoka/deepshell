import os
import sys
import aiofiles
import asyncio
from ui.popups import RadiolistPopup


class FileUtils:
    def __init__(self, ui=None, safe_extensions=None, ignore_folders=None, scan_dot_folders=False):
        """
        Initializes the FileUtils with options.

        :param ui: A UI object (optional).
        :param safe_extensions: List of file extensions that are allowed.
               If not provided, a default whitelist is used.
        :param ignore_folders: List of folder names to ignore.
        :param scan_dot_folders: Whether to scan hidden folders (starting with a dot). Default is False.
        """
        self.ui = ui
       
        self.default_safe_extensions = [
            # General text formats
            '.txt', '.md', '.json', '.csv', '.ini', '.cfg', '.xml',  
            '.yaml', '.yml', '.toml', '.log', '.sql', '.html', '.htm',  
            '.css', '.js', '.conf', '.properties', '.rst',

            # Programming languages
            '.py', '.c', '.cpp', '.h', '.hpp', '.java', '.cs', '.rs', '.go',  
            '.rb', '.php', '.sh', '.bat', '.pl', '.lua', '.swift', '.kt', '.m',  
            '.r', '.jl', '.dart', '.ts', '.v', '.scala', '.fs', '.asm', '.s',  
            '.vbs', '.ps1', '.clj', '.groovy', '.perl', '.f90', '.f95', '.ml'
        ]

        self.safe_extensions = safe_extensions or self.default_safe_extensions

        self.default_ignore_folders = ['__pycache__', '.git', '.svn', '.hg']
        self.ignore_folders = ignore_folders or self.default_ignore_folders
        self.scan_dot_folders = scan_dot_folders

    async def read_pipe(self):
        """Read piped input asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sys.stdin.read)

    
    async def process_file_or_folder(self, target):
        """Handles file or folder operations.""" 
        target = target.strip()
       
        if not os.path.exists(target):
            choice = await self.prompt_search(target)
            if not choice:
                return None
            target = choice
        await self._print_message(f"\n\nAnalyzing {target}\n\n")

        if os.path.isfile(target):
            return await self.read_file(target)
        elif os.path.isdir(target):
            return await self.read_folder(target)

        return None

    async def read_file(self, file_path, root_folder=None):
        """Asynchronously reads content from a file if its extension is in the safe list.
           Uses a timeout to cancel if reading takes too long.
        """
        # Print status message
        await self._print_message(f"\n\nReading {file_path}\n\n")
        try:
            # If the file's extension is not in the whitelist, skip it.
            if not any(file_path.lower().endswith(ext) for ext in self.safe_extensions):
                return f"Skipping file (unsupported): {file_path}"
            
            relative_path = os.path.relpath(file_path, root_folder) if root_folder else file_path

            async with aiofiles.open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
                try:
                    # Set a timeout (e.g., 10 seconds) for reading the file.
                    content = await asyncio.wait_for(file.read(), timeout=10)
                except asyncio.TimeoutError:
                    return f"Skipping file (timeout): {file_path}"
            return f"--------- {relative_path} ---------\n" + content
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    def generate_structure(self, folder_path, root_folder, prefix=""):
        """
        Generates a textual representation of the folder structure.
        All files within the folder are included, regardless of file type.
        """
        structure = f"{prefix}{os.path.basename(folder_path)}/\n"
        try:
            items = sorted(os.listdir(folder_path))
        except Exception as e:
            return f"Error reading folder {folder_path}: {e}"

        for item in items:
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path) and item not in self.ignore_folders and (self.scan_dot_folders or not item.startswith('.')):
                structure += self.generate_structure(item_path, root_folder, prefix + "--")
            elif os.path.isfile(item_path):
                # All files are included in the structure, even if they are not safe.
                relative_path = os.path.relpath(item_path, root_folder) if root_folder else item_path
                structure += f"{prefix}-- {relative_path}\n"

        return structure

    async def read_folder(self, folder_path, root_folder=None):
        """Recursively scans and reads all files in a folder.
           The folder structure is generated for all files; however, only files with safe extensions
           are attempted to be read (others are skipped).
        """
        if root_folder is None:
            root_folder = folder_path

        try:
            await self._print_message(f"\n\nGenerating structure for {folder_path}\n\n")
            structure = self.generate_structure(folder_path, root_folder)
            file_contents = "\n\n### File Contents ###\n"
            
            for root, _, files in os.walk(folder_path):
                # Skip ignored folders.
                if any(ignored in root.split(os.sep) for ignored in self.ignore_folders):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    # Use the safe whitelist to decide whether to read the file.
                    if not any(file.lower().endswith(ext) for ext in self.safe_extensions):
                        file_contents += f"\n\nSkipping file (unsupported): {file_path}\n\n"
                    else:
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
            # Optionally skip hidden directories.
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            files = [f for f in files if not f.startswith(".")]

            for name in files + dirs:
                if missing_path.lower() in name.lower():
                    results.append(os.path.join(root, name))
                    if len(results) >= max_results:
                        return results
        return results

    async def prompt_search(self, missing_path):
        """
        Prompts the user to search for a file when the target is missing.
        Uses a popup with a radiolist if UI is available, falling back to terminal input.
        """
        while True:
            results = await self.search_files(missing_path)
            
            if not results:
                if hasattr(self, "ui") and self.ui is not None:
                    popup = RadiolistPopup(
                        title="No matches found",
                        text=f"No matches found for '{missing_path}'. Would you like to try again?",
                        options=[("yes", "Yes"), ("no", "No")]
                    )
                    self.ui.mount(popup)
                    retry = await popup.wait_for_choice()
                    popup.remove()
                else:
                    print(f"No matches found for '{missing_path}'.")
                    retry = input("Would you like to try again? (yes/no): ").strip().lower()
                if retry == "no":
                    return None
                if hasattr(self, "ui") and self.ui is not None:
                    missing_path = await self.ui.get_user_input("Modify search term:")
                else:
                    missing_path = input("Modify search term: ")
                continue

            options = [(res, res) for res in results] + [("cancel", "Cancel")]
            if hasattr(self, "ui") and self.ui is not None:
                popup = RadiolistPopup(
                    title="Select a file",
                    text=f"Multiple matches found for '{missing_path}'. Please choose one:",
                    options=options
                )
                self.ui.mount(popup)
                choice = await popup.wait_for_choice()
                popup.remove()
            else:
                print(f"Multiple matches found for '{missing_path}'. Please choose one:")
                for i, res in enumerate(results, start=1):
                    print(f"{i}. {res}")
                choice_str = input("Enter the number of your choice (or 'cancel'): ").strip()
                if choice_str.lower() == "cancel":
                    return None
                if choice_str.isdigit() and 1 <= int(choice_str) <= len(results):
                    choice = results[int(choice_str)-1]
                else:
                    print("Invalid input, try again.")
                    continue

            if choice == "cancel":
                return None
            return choice

    async def _print_message(self, message: str):
        """Print messages either through UI or terminal."""
        if self.ui is not None:
            await self.ui.fancy_print(message)
        else:
            print(message)

