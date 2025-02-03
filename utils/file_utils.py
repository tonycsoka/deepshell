import os

def read_file(file_path):
    """
    Reads content from a file or lists and reads files in a folder.
    If a folder is detected, it provides a structured list of its contents along with file data.
    """
    if not os.path.exists(file_path):
        file_path = prompt_search(file_path)
        if not file_path:
            print(f"Error: File '{file_path}' does not exist.")
            return None

    if os.path.isdir(file_path):
            return read_folder(file_path)  # Handle folders separately

    else:
        with open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
            file_content = file.read()
            print(f"Reading file {file_path}:")
            return file_content
    
    	     		
def read_folder(folder_path):
    """
    Reads all files in a folder and returns their contents along with the folder structure.
    """

    print(f"Analyzing folder {folder_path}:")
    try:
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

        # Read content from each file in the folder
        file_contents = "\n\n### File Contents ###\n"
        for file in files:
            file_path = os.path.join(folder_path, file)
            try:
                with open(file_path, 'r', encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                file_contents += f"\n--- {file} ---\n{content}\n"
            except Exception as e:
                file_contents += f"\n--- {file} ---\nError reading file: {e}\n"

        return structure + file_contents

    except PermissionError:
        return f"Error: Permission denied to access '{folder_path}'."

def prompt_search(missing_path):
    """
    Searches for a missing file or folder in the home directory and prompts the user to select one.
    """
    home_dir = os.path.expanduser("~")
    results = []

    for root, dirs, files in os.walk(home_dir):
        # Exclude hidden folders and files
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        files = [f for f in files if not f.startswith(".")]

        # Search for matching files and directories
        for name in files + dirs:
            if missing_path.lower() in name.lower():
                results.append(os.path.join(root, name))

    if not results:
        print(f"No matches found for '{missing_path}'.")
        return None

    # Display search results to the user
    print(f"Multiple matches found for '{missing_path}'. Please choose one:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result}")

    # Get user selection
    while True:
        choice = input("Enter the number of your choice, or 'cancel' to abort: ").strip().lower()

        if choice == "cancel":
            return None

        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(results):
                return results[index]

        print("Invalid selection. Please enter a valid number or 'cancel'.")

