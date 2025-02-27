import os
import magic
import base64
import asyncio
import aiofiles
from PIL import Image
from io import BytesIO
from utils.logger import Logger
from config.settings import Mode
from ui.popups import RadiolistPopup
from chatbot.deployer import ChatBotDeployer
from config.settings import SUPPORTED_EXTENSIONS, IGNORED_FOLDERS, MAX_FILE_SIZE, MAX_LINES, CHUNK_SIZE, PROCESS_IMAGES

logger = Logger.get_logger()

class FileUtils:
    def __init__(self, manager, safe_extensions=None, ignore_folders=None, scan_dot_folders=False):
    
        self.ui = manager.ui
        self.index_file = None
        self.add_folder = None

        self.default_safe_extensions = SUPPORTED_EXTENSIONS
        self.safe_extensions = safe_extensions or self.default_safe_extensions
        self.default_ignore_folders = IGNORED_FOLDERS       
        self.ignore_folders = ignore_folders or self.default_ignore_folders
        self.scan_dot_folders = scan_dot_folders
        self.max_file_size = MAX_FILE_SIZE
        self.max_lines = MAX_LINES
        self.chunk_size = CHUNK_SIZE
        self.file_locks = {}

        if PROCESS_IMAGES:
            deployer = ChatBotDeployer()
            self.image_processor, _ = deployer.deploy_chatbot(Mode.VISION)


    def set_index_functions(self, index_file, add_folder):
        self.index_file = index_file
        self.add_folder = add_folder
        
    async def process_file_or_folder(self, target):
        target = target.strip()
       
        if not os.path.exists(target):
            choice = await self.prompt_search(target)
            if not choice:
                await self._print_message("\n[yellow]Nothing found[/yellow]")
                return -1
            target = choice

        if os.path.isfile(target):
            content = await self.read_file(target)
            if self.index_file:
                await self.index_file(target, content)
        elif os.path.isdir(target):
            await self.read_folder(target)

        logger.info("File operations complete")
        await self._print_message("\n[cyan]System:[/cyan] File processing complete, submiting the input to the chatbot")


   
    async def read_file(self, file_path):
        try:
            if not self._is_safe_file(file_path):
                logger.info(f"Skipping file (unsupported): {file_path}")
                return

            # Create a lock for this file if it doesn't exist yet
            if file_path not in self.file_locks:
                self.file_locks[file_path] = asyncio.Lock()

            # Use the lock for this file
            async with self.file_locks[file_path]:
                if PROCESS_IMAGES:
                    if self._is_image(file_path):
                        await self._print_message(f"[green]\nProcessing the image: {file_path}[/green]")
                        return await self._process_image(file_path)
                else:
                    if self._is_image(file_path):
                        logger.info(f"Skipping image file {file_path}")

                await self._print_message(f"[green]\nReading {file_path}[/green]")

                if os.path.getsize(file_path) > self.max_file_size:
                    content = await self._read_last_n_lines(file_path, self.max_lines)
                else:
                    async with aiofiles.open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
                        content = await file.read()

                return content

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")


   
    def _is_safe_file(self, file_path):
        if os.path.getsize(file_path) == 0:
            logger.info(f"Skipping empty file: {file_path}")
            return False

        if any(file_path.lower().endswith(ext) for ext in self.safe_extensions):
            return True  

        if '.' not in os.path.basename(file_path):
            logger.info(f"File '{file_path}' has no extension. Checking if it's a text file...")
            return self._is_text_file(file_path)  

        return False

   
    def _is_text_file(self, file_path):
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(file_path)
            
            logger.info(f"Detected MIME type for '{file_path}': {mime_type}")
            
            return mime_type.startswith("text")
        
        except Exception as e:
            logger.error(f"Error detecting MIME type for '{file_path}': {e}")


    def _is_image(self, file_path):
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path).startswith("image")
        except Exception:
            return False

    async def _process_image(self, file_path):
        logger.info(f"Processing image: {file_path}")
        loop = asyncio.get_running_loop()
        try:
            def resize_and_encode():
                with Image.open(file_path) as img:
                    img.thumbnail((1120, 1120))
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    return base64.b64encode(buffer.getvalue()).decode('utf-8')

            encoded_image = await loop.run_in_executor(None, resize_and_encode)
            description =  await self.image_processor._describe_image(encoded_image)
            logger.info(f"Processed {file_path}")
            return f"Image description by the vision model: {description}"
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")

    async def _read_last_n_lines(self, file_path, num_lines):
        buffer = []
        loop = asyncio.get_running_loop()

        async with aiofiles.open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
            file_size = await loop.run_in_executor(None, lambda: self._get_file_size(file_path))
            pos = file_size
            data = ""

            while pos > 0 and len(buffer) < num_lines:
                pos = max(0, pos - self.chunk_size)
                await file.seek(pos)
                chunk = await file.read(self.chunk_size)
                data = chunk + data
                lines = data.splitlines()

                if len(lines) > num_lines:
                    buffer = lines[-num_lines:]
                    break
                else:
                    buffer = lines

            return "\n".join(buffer) if buffer else "[File is empty]"

    def _get_file_size(self, file_path):
        try:
            with open(file_path, "rb") as f:
                f.seek(0, 2)
                return f.tell()
        except Exception:
            return 0
  
    def generate_structure(self, folder_path, root_folder, prefix=""):
        """
        Generates a dictionary representation of the folder structure.
        All files within the folder are included, regardless of file type.
        """
        logger.info(f"Generating structure for {folder_path}")

        structure = {}
        folder_name = os.path.basename(folder_path)
        structure[folder_name] = {}

        try:
            items = sorted(os.listdir(folder_path))
        except Exception as e:
            logger.error(f"Error reading folder {folder_path}: {e}")
            return structure

        for item in items:
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path) and item not in self.ignore_folders and (self.scan_dot_folders or not item.startswith('.')):
                structure[folder_name][item] = self.generate_structure(item_path, root_folder, prefix + "--")
            elif os.path.isfile(item_path):
                relative_path = os.path.relpath(item_path, root_folder) if root_folder else item_path
                structure[folder_name][item] = relative_path

        logger.debug(f"Folder structure: {structure}")
        return structure
   
    async def read_folder(self, folder_path, root_folder=None):
        """Recursively scans and reads all files in a folder.
           The folder structure is generated for all files; however, only files with safe extensions
           are attempted to be read (others are skipped).
        """
        logger.info(f"Opening {folder_path}")
        await self._print_message(f"[green]\nOpening {folder_path}[/green]")

        if root_folder is None:
            root_folder = folder_path

        try:
            await self._print_message(f"\nGenerating structure for {folder_path}")
            generated_structure = self.generate_structure(folder_path,root_folder)
            if self.add_folder:
                self.add_folder(generated_structure)
                        # Collecting content of all files
            for root, _, files in os.walk(folder_path):
                if any(ignored in root.split(os.sep) for ignored in self.ignore_folders):
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    if not any(file.lower().endswith(ext) for ext in self.safe_extensions):
                        logger.info( f"\nSkipping file (unsupported): {file_path}\n")
                    else:
                        content = await self.read_file(file_path)
                        if self.index_file and content:
                            await self.index_file(file_path, content)
                        elif content:
                            file_contents = f"\n{content.strip()}\n"
                            if file_contents:
                                return file_contents
                        

            logger.info(f"Reading files in {folder_path} complete")

        except PermissionError:
            logger.error(f"Error: Permission denied to access '{folder_path}'.")


    async def search_files(self, missing_path, search_dir=None):
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
        logger.info(f"Found {len(results)} files")
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
                    return "cancel"
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
                    return "cancel"
                if choice_str.isdigit() and 1 <= int(choice_str) <= len(results):
                    choice = results[int(choice_str)-1]
                else:
                    print("Invalid input, try again.")
                    continue

            if choice == "cancel":
                return "cancel"
            return choice


    async def _print_message(self, message: str):
        """Print messages either through UI or terminal."""
        if self.ui:
            await self.ui.buffer.put(message)
        else:
            print(message)
