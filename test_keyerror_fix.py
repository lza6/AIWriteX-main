
import re
from bs4 import BeautifulSoup

def test_fix_keyerror():
    # Simulate the data structure causing the KeyError
    # One task has 'original' (Markdown), the other has 'original_element' (HTML)
    
    tasks = [
        {
            "prompt": "Markdown Prompt",
            "ratio": "16:9",
            "original": "[IMG_PROMPT: Markdown Prompt | 16:9]"
        },
        {
            "prompt": "HTML Prompt",
            "ratio": "4:3",
            "original_element": BeautifulSoup('<div class="img-placeholder"></div>', 'html.parser').div
        }
    ]
    
    print("Simulating Loop Fix:")
    for idx, task in enumerate(tasks):
        # The line that caused the error was: original = task["original"]
        # The fix uses task.get("original", "")
        original_marker = task.get("original", "")
        print(f"Task {idx}: Prompt='{task['prompt']}', Marker='{original_marker}'")
        
        # Test replace logic
        if "original_element" in task and task["original_element"]:
            print(f"  -> Path: HTML replacement")
        elif "original" in task and task["original"]:
            print(f"  -> Path: Markdown string replacement")
        else:
            print(f"  -> Path: Error/Skip")

if __name__ == "__main__":
    test_fix_keyerror()
