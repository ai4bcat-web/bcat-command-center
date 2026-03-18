def generate_summary(architecture):
    summary = 'PROJECT ARCHITECTURE SUMMARY\n'\n    for category, files in architecture.items():
        summary += f'{category}: \n'
        for file in files:
            summary += f' - {file}\n'
    return summary