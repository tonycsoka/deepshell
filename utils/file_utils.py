import os

def read_file(file_path):
    """
    Reads content from a file and returns it.
    """
    if not file_path or not os.path.exists(file_path):
        return ""
    with open(file_path, "r") as file:
        return file.read()
