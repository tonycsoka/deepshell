import os
import sys
import aiofiles
import asyncio


class FileUtils:
    def __init__(self, ui=None,  ignore_files=None, ignore_folders=None, scan_dot_folders=False):
        """
        Initializes the FileUtils with customizable options to ignore certain files and folders.

        :param ignore_files: List of file extensions to ignore.
        :param ignore_folders: List of folder names to ignore.
        :param scan_dot_folders: Whether to scan hidden folders (those starting with a dot). Default is False.
        """
        self.ui = ui
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
      
       # await self.ui.buffer.put(f"\nReading {file_path}") 
        try:
            if any(file_path.endswith(ext) for ext in self.ignore_files):
                return f"Skipping file (ignored): {file_path}"
            
            relative_path = os.path.relpath(file_path, root_folder) if root_folder else file_path
            
            async with aiofiles.open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
                return f"--------- {relative_path} ---------\n" + await file.read()
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    def generate_structure(self, folder_path, root_folder, prefix=""):
        """Generates a textual representation of the folder structure."""
        structure = f"{prefix}{os.path.basename(folder_path)}/\n"
        items = sorted(os.listdir(folder_path))

        for item in items:
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path) and item not in self.ignore_folders and (self.scan_dot_folders or not item.startswith('.')):
                structure += self.generate_structure(item_path, root_folder, prefix + "--")  # No await needed here
            elif os.path.isfile(item_path) and not any(item.endswith(ext) for ext in self.ignore_files):
                relative_path = os.path.relpath(item_path, root_folder) if root_folder else item_path
                structure += f"{prefix}-- {relative_path}\n"

        return structure


    async def read_folder(self, folder_path, root_folder=None):
        """Recursively scans and reads all files in a folder, respecting ignore lists."""
      #  await self.ui.buffer.put(f"\nReading {folder_path}")
        if root_folder is None:
            root_folder = folder_path
        
        try:
          #  await self.ui.rich_print(f"\nGenerating structure for {folder_path}")
            structure = self.generate_structure(folder_path, root_folder)
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


    async def process_file_or_folder(self, target):
        """Handles file or folder operations."""
        # Clean up the target path
        target = target.strip()
       
        # Check if target exists; if not, prompt search until a valid result is found or cancel is chosen
        if not os.path.exists(target):
            choice = await self.prompt_search(target)
            if not choice:
                return None
            target = choice.strip()


      #  await self.ui.buffer.put("\nAnalyzing the target")
        # Now process based on whether target is a file or a folder
        if os.path.isfile(target):
            return await self.read_file(target)
        elif os.path.isdir(target):
            return await self.read_folder(target)

        return None

    #
    # async def prompt_search(self, missing_path):
    #     while True:
    #         results = await self.search_files(missing_path)
    #         if not results:
    #             retry = await self.ui.run_dialog(
    #                 lambda: radiolist_dialog(
    #                     title="No matches found",
    #                     text=f"No matches found for '{missing_path}'. Would you like to try again?",
    #                     values=[("yes", "Yes"), ("no", "No")]
    #                 ).run_async()
    #             )
    #             if retry == "no":
    #                 return None
    #             missing_path = await self.ui.get_user_input("Modify search term: ")
    #             continue
    #
    #         choice = await self.ui.run_dialog(
    #             lambda: radiolist_dialog(
    #                 title="Select a file",
    #                 text=f"Multiple matches found for '{missing_path}'. Please choose one:",
    #                 values=[(res, res) for res in results] + [("cancel", "Cancel")]
    #             ).run_async()
    #         )
    #         if choice == "cancel":
    #             return None
    #         return choice
    #
    async def prompt_search(self, missing_path):
        while True:
            # Search for files based on the missing_path
            results = await self.search_files(missing_path)
            
            if not results:
                # No results found, prompt user to modify the search term
                await self._print_message(f"No matches found for '{missing_path}'.")
                missing_path = await self._get_user_input("Modify search term: ")
                continue

            # Results found, prompt user to select one
            await self._print_message(f"Multiple matches found for '{missing_path}'. Please select one:")
            for i, res in enumerate(results):
                await self._print_message(f"{i + 1}. {res}")

            # Wait for user to input a number corresponding to the selection
            number = await self._get_user_input("Enter the number of your choice: ")
            
            if number.isdigit() and 1 <= int(number) <= len(results):
                return results[int(number) - 1]  # Return the selected result

            # If invalid input, notify user
            await self._print_message("**Invalid input. Please enter a valid number.**")


    async def _get_user_input(self, prompt_text: str = "Enter input:"):
        """Get user input asynchronously, either through UI or terminal."""
        if self.ui is not None:
            return await self.ui.get_user_input(prompt_text)
        else:
            # Fallback to classic terminal input
            return input(prompt_text)


    async def _print_message(self, message: str):
        """Print messages either through UI or terminal."""
        if self.ui is not None:
            await self.ui.fancy_print(message)
        else:
            print(message)
