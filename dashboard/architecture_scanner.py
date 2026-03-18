import os
import fnmatch
import json


def scan_project_structure(base_path):
    architecture = {
        "Frontend": [],
        "Backend": [],
        "Agents": [],
        "Services": [],
        "Data": [],
        "APIs": [],
        "Automations": [],
        "Integrations": [],
        "Infrastructure": []
    }

    for root, dirs, files in os.walk(base_path):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")  # Ignore cache directories

        for filename in fnmatch.filter(files, "*.py"):
            if "dashboard" in filename:
                architecture["Frontend"].append(os.path.join(root, filename))
            elif "agent" in filename or "service" in filename:
                architecture["Agents"].append(os.path.join(root, filename))
            else:
                architecture["Backend"].append(os.path.join(root, filename))

    return architecture