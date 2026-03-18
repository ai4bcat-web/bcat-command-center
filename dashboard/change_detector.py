import json
import os


def detect_changes(new_architecture, old_architecture_path='architecture_snapshot.json'):
    if os.path.exists(old_architecture_path):
        with open(old_architecture_path, 'r') as f:
            old_architecture = json.load(f)
    else:
        old_architecture = {}

    changes = {
        "new_modules": [],
        "removed_modules": [],
        "renamed_modules": []
    }

    # Compare architectures
    for key, items in new_architecture.items():
        new_set = set(items)
        old_set = set(old_architecture.get(key, []))

        changes['new_modules'].extend(new_set - old_set)
        changes['removed_modules'].extend(old_set - new_set)

    with open(old_architecture_path, 'w') as f:
        json.dump(new_architecture, f)

    return changes