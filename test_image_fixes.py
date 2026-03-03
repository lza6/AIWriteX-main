
import re
from bs4 import BeautifulSoup

def test_regex():
    # Test cases for regex relaxation
    test_cases = [
        "[图片解析: 提示词1 | 16:9]",
        "[图片解析: 提示词2]",
        "[IMG_PROMPT: prompt3 | 4:3]",
        "[IMG_PROMPT: prompt4]",
        "[图片解析： 提示词5 | 3:4]",
        "[图片解析: 提示词 带有空格 | 16:9]"
    ]
    
    # The new pattern from visual_assets.py
    pattern = r'\[(?:IMG_PROMPT|图片解析)[:：]\s*(.+?)\s*(?:\|\s*([\d\.:]+))?\s*\]'
    
    print("Testing Regex Relaxation:")
    for tc in test_cases:
        m = re.search(pattern, tc)
        if m:
            prompt = m.group(1).strip()
            ratio = m.group(2).strip() if m.group(2) else "16:9 (default)"
            print(f"MATCH: {tc} -> Prompt: {prompt}, Ratio: {ratio}")
        else:
            print(f"FAIL: {tc}")

def test_replacement_logic():
    print("\nTesting Robust Replacement Logic:")
    html_content = '''
    <div class="content">
        <p>Before image.</p>
        <div class="img-placeholder" data-img-prompt="A cat" data-aspect-ratio="16:9">
            Existing placeholder content (possibly reformatted by BS4)
        </div>
        <p>After image.</p>
    </div>
    '''
    
    soup = BeautifulSoup(html_content, 'html.parser')
    placeholders = soup.find_all(class_="img-placeholder")
    
    tasks = []
    for ph in placeholders:
        tasks.append({
            "prompt": ph.get("data-img-prompt"),
            "original_element": ph
        })
        
    img_url = "/images/cat.png"
    img_tag = f'<img src="{img_url}" style="width:100%" alt="cat">'
    
    for task in tasks:
        new_img_soup = BeautifulSoup(img_tag, 'html.parser')
        task["original_element"].replace_with(new_img_soup.contents[0])
        
    final_html = soup.decode(formatter=None)
    print("Final HTML Outcome:")
    print(final_html)
    
    if '<img src="/images/cat.png"' in final_html and 'img-placeholder' not in final_html:
        print("SUCCESS: Image tag replaced placeholder correctly.")
    else:
        print("FAILURE: Replacement did not work as expected.")

if __name__ == "__main__":
    test_regex()
    test_replacement_logic()
