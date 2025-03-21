import os
import ast
import ollama

# Dynamically resolve config/settings.py relative to ensure_models.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
CONFIG_PATH = os.path.join(BASE_DIR, "..", "config", "settings.py") 

def extract_model_names(config_path=CONFIG_PATH):
    """ Extract values from all *_MODEL variables in settings.py """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"The configuration file '{config_path}' does not exist.")

    with open(config_path, 'r', encoding='utf-8') as file:
        config_content = file.read()

    try:
        parsed_content = ast.parse(config_content)
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in the configuration file: {e}")

    model_names = set()

    for node in ast.walk(parsed_content):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith('_MODEL'):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        model_names.add(node.value.value)  # Extract the assigned string value

    return model_names


def validate_models(config_path=CONFIG_PATH):
    """ Ensure that all required models are available in Ollama. """
    model_names = extract_model_names(config_path)

    available_model_names = set()


    try:
        available_models = ollama.list()
        available_models = available_models.models
        for Model in available_models:
            available_model_names.add(Model.model)

    except Exception as e:
        raise RuntimeError(f"Failed to list models using Ollama: {e}")


    missing_models = model_names - available_model_names

    if not missing_models:
        print("All required models are already available.")
        return

    for model in missing_models:
        try:
            print(f"Pulling missing model: {model}")
            ollama.pull(model)
        except Exception as e:
            print(f"Failed to pull model '{model}': {e}")

