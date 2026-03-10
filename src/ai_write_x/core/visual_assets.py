import re
from typing import Optional
from src.ai_write_x.core.llm_client import LLMClient
import src.ai_write_x.utils.log as lg
import threading
import time

class HeartbeatLogger:
    def __init__(self, message="[Pulse] 仍在阅读文章并构思绘画分镜中...", interval=5.0):
        self.interval = interval
        self.message = message
        self._stop_event = threading.Event()
        self._thread = None
        self._start_time = 0

    def start(self):
        self._start_time = time.time()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def _run(self):
        while not self._stop_event.wait(self.interval):
            elapsed = int(time.time() - self._start_time)
            lg.print_log(f"{self.message} (已耗时 {elapsed}s)", "info")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()

class VisualAssetsManager:
    """视觉资产管理器：负责文本到图像的自动化提示词生成与后台同步渲染链路"""
    
    @classmethod
    def inject_image_prompts(cls, markdown_text: str) -> str:
        """根据正文内容，自动分析并在适当位置插入 [IMG_PROMPT: prompt | ratio] 标签"""
        client = LLMClient()
        
        # 长度检查：如果文章太长，只取摘要/分段标题，防止 LLM 超时或 Context 爆炸
        # 提高阈值到 15000 字符，并允许更长的处理长度
        if len(markdown_text) > 1500000:
            lg.print_log(f"[VisualAssets] 文章长度 ({len(markdown_text)} 字符) 超过阈值，切换至分段场景抽离...")
            # 提取前 3000 字和后 3000 字，以及中间的所有标题
            lines = markdown_text.split('\n')
            headers = [line for line in lines if line.strip().startswith('#')]
            sample_text = markdown_text[:3000] + "\n\n" + "\n".join(headers) + "\n\n" + markdown_text[-3000:]
            processing_text = sample_text
        else:
            processing_text = markdown_text

        # 艺术化动态策略：从“机械字数配给”转向“叙事呼吸感分析”
        content_len = len(markdown_text)
        # 根据字数动态约束图片数量区间（放宽限制，增加插图数量）
        safe_min = max(3, content_len // 600)
        safe_max = max(5, content_len // 300)
        if safe_max > 15: safe_max = 15 # 硬上限，防止过度生成
        
        system_prompt = f'''你现在是顶级 **AI 视觉逆向工程师 (AI Vision Reverse-Engineer)**，负责将文章的叙事瞬间解构为像素级的绘画提示词。
你的目标是生成 **生产级提示词集 (Production-Ready Prompt Set)**，实现 1:1 的视觉还原，彻底杜绝“脸部畸变、文字乱码、人物重复”。

## 核心协议：精准扫描 (Strict Protocols)
1. **WYSIWYG & 空间扫描 (Center-to-Edge)**：
   - 必须描述主体人物的相对位置，避免多主体时出现“双生脸”。
   - 扫描背景边际细节（如：数据中心的布线、砖块纹理、光网络纤维）。
2. **术语精确化 (Terminology Precision)**：
   - **服装剪裁**：禁止使用模糊词汇。必须指定：`cap sleeves`, `sleeveless`, `off-shoulder`, `mandarin collar`, `business suit with notched lapel`。
   - **发型与特征**：精确到 `wispy air bangs`, `almond eyes`, `pore-level skin texture`。
3. **物理与材质映射 (Physics Mapping)**：
   - 区分材质：`silk` vs `matte cotton` vs `brushed metal`。
   - 光影交互：引入 `Subsurface Scattering` (皮肤透光), `Rim light` (轮廓光), `Volumetric lighting` (体积光)。

## 视觉纠偏策略 (V19.5 Core)
- **防止文字畸变**：针对仪表盘或显示器，要求 AI 描述 `sharp digital typography`, `legible financial charts`, `clear UI elements`。
- **防止人物重复**：明确主次，使用描述性差异化词汇（如：一位年长的引导者与一位年轻的记录者）。
- **人脸保底**：强制加入 `detailed facial features`, `symmetrical face`, `soulful gaze`。

## 占位符格式 (必须严格遵守)
严格遵循：[[V-SCENE: <Part 1: Positive Prompt> (中文说明) | <Part 2: Negative Prompt> | <比例>]]

【Part 1: Positive Prompt 要求】：
[Medium/Style], [Camera/Framing], [Subject Attributes], [Clothing Precise Cuts], [Environment Details], [Lighting & Atmosphere], [Technical Specs: 8k, Unreal Engine 5 render style]

【Part 2: Negative Prompt 要求】：
必须包含：bad anatomy, blurry face, text distortion, watermark, headless, duplicate features, distorted text.

## 约束准则
- **数量限制**：正文插图数量在 **{safe_min} 到 {safe_max} 张之间**。
- **首图强制**：必须插入 2.35:1 的封面大图。
- **构图**：16:9 (全景), 3:4 (人物), 4:3 (标准)。

直接输出文章全貌，包括正文与占位符，不要任何解释。
【特别注意】：占位符格式 [[V-SCENE: ...]] 左右严禁出现 ** 或其他符号。'''

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"文章长度约为 {content_len} 字符。请为以下内容插入配图占位符：\n\n{processing_text}"}
        ]
        
        try:
            lg.print_log("[PROGRESS:VISUAL:START]", "internal")
            lg.print_log(f"[PROGRESS:VISUAL:DETAIL] 模型: {client.current_model}<br>模式: 叙事呼吸感分析", "internal")
            lg.print_log(f"[VisualAssets] 🧠 正在分析全文信息密度与叙事节奏 (智能限制 {safe_min}-{safe_max} 张图)...")
            lg.print_log("[VisualAssets] 正在测算“视觉缓冲区”并植入绘画提示词...")
            
            heartbeat = HeartbeatLogger(interval=8.0)
            heartbeat.start()
            try:
                # 增加 60 秒硬超时防止假死
                enhanced_text = client.chat(messages=messages, temperature=0.7, timeout=60.0)
            finally:
                heartbeat.stop()
                
            # 清理代码块包裹
            enhanced_text = re.sub(r'^```markdown\s*', '', enhanced_text)
            enhanced_text = re.sub(r'^```\s*', '', enhanced_text)
            enhanced_text = re.sub(r'```$', '', enhanced_text)
            
            # 如果是摘要模式处理的结果，且结果远短于原文，说明只输出了带标记的片段，需要合回原文
            if len(enhanced_text) < len(markdown_text) * 0.7 and 'V-SCENE:' in enhanced_text:
                lg.print_log("[VisualAssets] 检测到片段式输出，正在将提示词合并回原长文...")
                prompts = re.findall(r'\[\[V-SCENE:\s*.+?\s*\|\s*.+?\]\]', enhanced_text)
                if prompts:
                    lines = markdown_text.split('\n')
                    # 封面插入第一段后
                    for i, line in enumerate(lines):
                        if line.strip() and not line.strip().startswith('#'):
                            lines.insert(i+1, "\n" + prompts[0])
                            break
                    # 其余均衡分布
                    if len(prompts) > 1:
                        chunk_size = len(lines) // len(prompts)
                        for i in range(1, len(prompts)):
                            pos = min((i + 1) * chunk_size, len(lines)-1)
                            lines.insert(pos, "\n" + prompts[i])
                    return "\n".join(lines).strip()
                
            return enhanced_text.strip()
        except Exception as e:
            lg.print_log(f"[Warning] 视觉资产提示词植入失败，使用原文跳过: {str(e)}")
            return markdown_text

    @classmethod
    def sync_trigger_image_generation(cls, text_with_prompts: str) -> str:
        """扫描文本中的提示词标记（Markdown 或 HTML 占位符），调用图像 API 生成图片并替换"""
        from bs4 import BeautifulSoup
        all_tasks = []
        
        # 1. 扫描提示词标记 
        # 优先级 A: 标准双中括号 [[V-SCENE: prompt | ratio]]
        # 优先级 B: 旧版 [IMG_PROMPT: prompt | ratio] 或 [图片解析: prompt]
        # 优先级 C: 捕捉自然语言出现的圆括号描述 (prompt)
        
        # 模式 A & B
        # 模式 A & B (V19.5 升级版：支持三段式格式 & 鲁棒性 Markdown 兼容)
        # [[V-SCENE: positive (comment) | negative | ratio]]
        # 兼容可能有 ** 包裹的情况: **[[V-SCENE: ...]]**
        pattern = r'(?:\*\*)?\[\[V-SCENE:\s*(.+?)\s*(?:\((.*?)\))?\s*(?:\|\s*(.+?)\s*)?\|\s*([\d\.:]+)\s*\]\](?:\*\*)?'
        for m in re.finditer(pattern, text_with_prompts):
            pos_prompt = m.group(1).strip()
            comment = m.group(2).strip() if m.group(2) else ""
            neg_prompt = m.group(3).strip() if m.group(3) else "bad anatomy, text, watermark, blurry face"
            actual_ratio = m.group(4).strip() if m.group(4) else "16:9"
            
            # 整合提示词
            full_prompt = f"{pos_prompt} --no {neg_prompt}" if neg_prompt else pos_prompt
            
            all_tasks.append({
                "prompt": full_prompt,
                "pos_prompt": pos_prompt,
                "neg_prompt": neg_prompt,
                "comment": comment,
                "ratio": actual_ratio,
                "original": m.group(0)
            })
            
        # 模式 C (仅当没有 A/B 且看起来像提示词时才尝试)
        if not all_tasks:
            # 扫描类似 (月偏食阶段对比图...) 的圆括号格式，通常出现在段落之后
            bracket_pattern = r'\n\s*\(([^)\n]{10,100})\)\s*\n' # 10-100字符的圆括号行
            for m in re.finditer(bracket_pattern, text_with_prompts):
                all_tasks.append({
                    "prompt": m.group(1).strip(),
                    "ratio": "16:9",
                    "original": m.group(0)
                })
            
        # 2. 扫描 HTML 格式的占位符 <div class="img-placeholder" ...>...</div>
        try:
            soup = BeautifulSoup(text_with_prompts, "html.parser")
            placeholders = soup.find_all(class_="img-placeholder")
            for ph in placeholders:
                prompt = ph.get("data-img-prompt", "").strip()
                ratio = ph.get("data-aspect-ratio", "16:9").strip()
                if prompt:
                    # 使用 BeautifulSoup 的 replace_with 方法进行更稳定的替换
                    all_tasks.append({
                        "prompt": prompt,
                        "ratio": ratio,
                        "original_element": ph # 保存元素对象
                    })
        except Exception as e:
            lg.print_log(f"[VisualAssets] BS 解析失败，降级使用正则: {e}", "warning")
            html_blocks = re.finditer(r'<div[^>]*class="img-placeholder"[^>]*>.*?</div>', text_with_prompts, re.DOTALL)
            for m in html_blocks:
                block = m.group(0)
                prompt_match = re.search(r'data-img-prompt=["\']([^"\']+)["\']', block)
                ratio_match = re.search(r'data-aspect-ratio=["\']([^"\']+)["\']', block)
                if prompt_match:
                    all_tasks.append({
                        "prompt": prompt_match.group(1).strip(),
                        "ratio": (ratio_match.group(1).strip() if ratio_match else "16:9"),
                        "original": block
                    })
            
            # 模式 E: 扫描 <img> 标签 (鲁棒性加强)
            img_tags = re.finditer(r'<img[^>]*data-img-prompt=["\']([^"\']+)["\']([^>]*)>', text_with_prompts, re.IGNORECASE)
            for m in img_tags:
                prompt = m.group(1).strip()
                tag_body = m.group(0)
                ratio_match = re.search(r'data-aspect-ratio=["\']([^"\']+)["\']', tag_body)
                all_tasks.append({
                    "prompt": prompt,
                    "ratio": (ratio_match.group(1).strip() if ratio_match else "16:9"),
                    "original": tag_body
                })

        if not all_tasks:
            return text_with_prompts
            
        lg.print_log(f"\n[VisualAssets] 共检测到 {len(all_tasks)} 张图片需要生成")
        
        from src.ai_write_x.config.config import Config
        from src.ai_write_x.utils.path_manager import PathManager
        import os, requests as req_lib
        
        config = Config.get_instance()
        img_api_type = config.img_api_type
        # 获取所有可用 Key 列表
        img_api_keys = config.get_img_api_keys()
        img_api_model = config.img_api_model
        
        # 初始化 Key 指针
        current_img_key_idx = 0
        if not img_api_keys:
            img_api_keys = [config.img_api_key]
        
        img_api_key = img_api_keys[current_img_key_idx]
        image_dir = PathManager.get_image_dir()
        
        # 获取 API base
        img_config = config.config.get("img_api", {})
        api_bases = {
            "modelscope": "https://api-inference.modelscope.cn/v1",
            "ali": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }
        
        # 智能提取当前选中的配置
        img_type_cfg = img_config.get(img_api_type, {})
        if img_api_type == "custom" and isinstance(img_type_cfg, list):
            custom_index = int(img_config.get("custom_index", 0) or 0)
            if 0 <= custom_index < len(img_type_cfg):
                img_type_cfg = img_type_cfg[custom_index]
            else:
                img_type_cfg = img_type_cfg[0] if img_type_cfg else {}
        elif not isinstance(img_type_cfg, dict):
            img_type_cfg = {}
            
        api_base = img_type_cfg.get("api_base", api_bases.get(img_api_type, ""))
        # 兼容性补充：如果全局 config 没拿到 key/model，尝试从局部提取
        if img_api_type == "custom":
            extracted_key = img_type_cfg.get("api_key")
            if extracted_key:
                img_api_key = extracted_key
            extracted_model = img_type_cfg.get("model")
            if extracted_model:
                img_api_model = extracted_model
            
        result_text = text_with_prompts
        generated_count = 0
        total_images = len(all_tasks)
        
        for idx, task in enumerate(all_tasks):
            prompt = task["prompt"]
            ratio = task["ratio"]
            # 'original' 仅在非 HTML 模式任务中存在，HTML 模式使用 'original_element'
            original_marker = task.get("original", "")
            
            lg.print_log(f"[VisualAssets] 🎨 正在生成第 {idx+1}/{len(all_tasks)} 张图片...")
            lg.print_log(f"  提示词: {prompt[:80]}...")
            lg.print_log(f"  比例: {ratio}, API: {img_api_type}, 模型: {img_api_model}")
            lg.print_log(f"[PROGRESS:VISUAL:DETAIL] 图片 {idx+1}/{len(all_tasks)} | {img_api_type} / {img_api_model}", "internal")
            
            # 根据比例计算尺寸
            size = cls._ratio_to_size(ratio.strip())
            
            img_path = None
            try:
                if img_api_type == "picsum":
                    # Picsum 随机图片
                    w_h = size.split("*")
                    download_url = f"https://picsum.photos/{w_h[0]}/{w_h[1]}?random={idx+1}"
                    from src.ai_write_x.utils import utils as u
                    img_path = u.download_and_save_image(download_url, str(image_dir))
                    
                elif img_api_type in ("modelscope", "ali", "custom") and (api_base or img_api_type == "custom") and img_api_key:
                    # OpenAI 兼容的图像 API
                    #对于 custom 类型，我们直接从配置中拿基准地址, 上方已经正确提取
                    actual_api_base = api_base
                    
                    if not actual_api_base:
                        lg.print_log(f"  [跳过] {img_api_type} API未配置 api_base", "warning")
                        continue
                    is_modelscope = img_api_type == "modelscope" or "modelscope" in actual_api_base.lower()
                    is_ali = img_api_type == "ali" or "dashscope" in actual_api_base.lower()

                    if idx > 0 and (is_modelscope or is_ali):
                         lg.print_log("  [等待] 为避免并发限制，稍作停顿 (5秒)...")
                         time.sleep(5)

                    if is_modelscope or is_ali:
                        import requests
                        headers = {
                            "Authorization": f"Bearer {img_api_key}",
                            "Content-Type": "application/json",
                        }
                        if is_modelscope:
                            headers["X-ModelScope-Async-Mode"] = "true"
                        if is_ali:
                            headers["X-DashScope-Async"] = "enable"
                        
                        endpoint = actual_api_base.rstrip('/')
                        if not endpoint.endswith('images/generations') and not endpoint.endswith('image-synthesis'):
                            # append standard openai path
                            endpoint = f"{endpoint}/images/generations"
                            
                        payload = {
                            "model": img_api_model,
                            "prompt": prompt,
                            "n": 1,
                            "size": size.replace("*", "x")
                        }
                        
                        # 获取全局代理
                        proxy = config.proxy
                        proxies = {"http": proxy, "https": proxy} if proxy else None
                        
                        res = req_lib.post(endpoint, headers=headers, json=payload, timeout=30, proxies=proxies)
                        
                        # --- 多 Key 自动容灾逻辑 (V19.0) ---
                        if (res.status_code == 429 or res.status_code == 401) and len(img_api_keys) > 1:
                            # 如果当前 Key 限流或失效，尝试切换下一个
                            current_img_key_idx = (current_img_key_idx + 1) % len(img_api_keys)
                            img_api_key = img_api_keys[current_img_key_idx]
                            lg.print_log(f"  [Failover] 图片 API {res.status_code}，切换至 Key {current_img_key_idx} 重试...", "warning")
                            # 重新执行当前任务循环 (通过继续外部循环的一个微调逻辑)
                            # 为了简单起见，我们在这里直接进行一次内部递归或重发请求
                            # 这里采用重发请求以保持逻辑线性
                            headers["Authorization"] = f"Bearer {img_api_key}"
                            res = req_lib.post(endpoint, headers=headers, json=payload, timeout=30, proxies=proxies)
                        
                        res_json = res.json()
                        
                        if res.status_code == 429:
                            lg.print_log(f"  [跳过] {img_api_type} API 触发限流 (429) 且备用 Key 已耗尽。保留原文空位。", "warning")
                            continue
                            
                        elif res.status_code != 200:
                            raise Exception(f"图像生成请求失败: {res.status_code} - {res.text}")
                            
                        if not img_path: # IF not already fulfilled by fallback
                            task_id = None
                            # 灵活获取 task_id
                            if "task_id" in res_json:
                                task_id = res_json["task_id"]
                            elif "output" in res_json and "task_id" in res_json["output"]:
                                task_id = res_json["output"]["task_id"]
                            elif "id" in res_json: # 部分通用 API
                                task_id = res_json["id"]
                                
                            img_url = None
                            if not task_id:
                                # 尝试直接获取 url
                                if "data" in res_json and len(res_json["data"]) > 0:
                                    img_url = res_json["data"][0].get("url")
                                elif "output" in res_json and "url" in res_json["output"]:
                                    img_url = res_json["output"]["url"]
                                else:
                                    raise Exception(f"未能获取 task_id 或直接的 img_url: {res.text}")
                            else:
                                lg.print_log(f"  获取到任务ID: {task_id}, 开始轮询任务状态...")
                                # 构建任务查询地址
                                # 如果 api_base 包含 v1/images/generations, 尝试转换为 v1/tasks/task_id
                                base_task_url = actual_api_base.rstrip('/')
                                if "/images/generations" in base_task_url:
                                    base_task_url = base_task_url.replace("/images/generations", "")
                                
                                # 支持 ModelScope 和 DashScope 的任务端点
                                if is_ali:
                                    task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
                                else:
                                    task_url = f"{base_task_url}/tasks/{task_id}"
                                
                                poll_headers = {
                                    "Authorization": f"Bearer {img_api_key}"
                                }
                                if is_modelscope:
                                    poll_headers["X-ModelScope-Task-Type"] = "image_generation"
                                    
                                # 通用轮询逻辑
                                for poll_idx in range(150): # 约 7-8 分钟
                                    time.sleep(5)
                                    try:
                                        # 获取全局代理
                                        proxy = config.proxy
                                        proxies = {"http": proxy, "https": proxy} if proxy else None
                                        task_res = req_lib.get(task_url, headers=poll_headers, timeout=10, proxies=proxies)
                                        t_json = task_res.json()
                                        
                                        # 兼容多种状态字段
                                        status = ""
                                        output = t_json.get("output", {}) if isinstance(t_json.get("output"), dict) else t_json
                                        status = t_json.get("task_status") or output.get("task_status") or t_json.get("status") or output.get("status")
                                        
                                        if not status and "task" in t_json: # 部分 API 嵌套在 task 中
                                            status = t_json["task"].get("status")
                                            
                                        if status in ("SUCCEEDED", "SUCCEED", "COMPLETED", "success"):
                                            lg.print_log(f"  ✅ 任务生成成功 (耗时 ~{poll_idx*5}s)")
                                            # 获取结果 URL
                                            if "output_images" in t_json and len(t_json["output_images"]) > 0:
                                                img_url = t_json["output_images"][0]
                                            elif "results" in output and len(output["results"]) > 0:
                                                img_url = output["results"][0].get("url")
                                            elif "data" in t_json and len(t_json["data"]) > 0:
                                                img_url = t_json["data"][0].get("url")
                                            elif "url" in output:
                                                img_url = output["url"]
                                            break
                                        elif status in ("FAILED", "CANCELED", "failed", "error"):
                                            raise Exception(f"生成任务失败: {status} - {t_json}")
                                        
                                        if poll_idx % 4 == 0:
                                            lg.print_log(f"  ⏳ 正在排队或渲染中... ({status})")
                                    except Exception as poll_e:
                                        lg.print_log(f"  [轮询警告] {str(poll_e)}", "warning")
                                        
                                if not img_url:
                                    raise Exception("轮询获取图片超时")
                                    
                            if img_url:
                                file_name = f"{img_api_type}_{int(time.time()*1000)}_{idx}.png"
                                file_path = os.path.join(str(image_dir), file_name)
                                # 获取全局代理
                                proxy = config.proxy
                                proxies = {"http": proxy, "https": proxy} if proxy else None
                                with open(file_path, "wb") as f:
                                    f.write(req_lib.get(img_url, timeout=30, proxies=proxies).content)
                                img_path = file_path
                            
                    else:
                        from openai import OpenAI
                        # 获取全局代理
                        proxy = config.proxy
                        proxies = {"http": proxy, "https": proxy} if proxy else None
                        
                        # OpenAI 客户端目前主要通过 HTTP 代理
                        http_client = None
                        if proxy:
                            import httpx
                            http_client = httpx.Client(proxy=proxy)
                            
                            client = OpenAI(api_key=img_api_key, base_url=actual_api_base, http_client=http_client)
                            try:
                                response = client.images.generate(
                                    model=img_api_model,
                                    prompt=prompt,
                                    n=1,
                                    size=size.replace("*", "x")  # OpenAI format: 1024x1024
                                )
                            except Exception as oai_err:
                                # OpenAI SDK 错误捕捉与多 Key 容灾
                                if ("429" in str(oai_err) or "401" in str(oai_err)) and len(img_api_keys) > 1:
                                    current_img_key_idx = (current_img_key_idx + 1) % len(img_api_keys)
                                    img_api_key = img_api_keys[current_img_key_idx]
                                    lg.print_log(f"  [Failover] OpenAI 图像接口故障，切换 Key {current_img_key_idx}...", "warning")
                                    client = OpenAI(api_key=img_api_key, base_url=actual_api_base, http_client=http_client)
                                    response = client.images.generate(
                                        model=img_api_model,
                                        prompt=prompt,
                                        n=1,
                                        size=size.replace("*", "x")
                                    )
                                else:
                                    raise oai_err

                            if response.data and len(response.data) > 0:
                                img_url = response.data[0].url
                                file_name = f"{img_api_type}_{int(time.time()*1000)}_{idx}.png"
                                file_path = os.path.join(str(image_dir), file_name)
                                # 获取全局代理
                                proxy = config.proxy
                                proxies = {"http": proxy, "https": proxy} if proxy else None
                                with open(file_path, "wb") as f:
                                    f.write(req_lib.get(img_url, timeout=30, proxies=proxies).content)
                                img_path = file_path

                elif img_api_type == "comfyui":
                    # 通用 ComfyUI 支持 - 端口从用户配置中读取，不硬编码默认值
                    if not api_base:
                        lg.print_log("  [跳过] ComfyUI API地址未配置，请在设置中配置 API 地址", "error")
                        continue
                    comfy_base_url = api_base.rstrip('/')
                    
                    # 1. 尝试加载用户放在主目录的自定 z-image 专用配置文件
                    comfy_workflow_path = os.path.join(str(PathManager.get_app_data_dir()), "z-image专用nf4快速备份.json")
                    if not os.path.exists(comfy_workflow_path):
                        raise Exception(f"找不到 ComfyUI API 工作流配置文件: {comfy_workflow_path}")
                        
                    import json
                    with open(comfy_workflow_path, 'r', encoding='utf-8') as f:
                        workflow_data = json.load(f)
                        
                    # 2. 动态替换长宽和提示词参数
                    w_str, h_str = size.split("*")
                    
                    # 节点 34 是 CLIPTextEncode 提示词节点
                    if "34" in workflow_data and "inputs" in workflow_data["34"]:
                        workflow_data["34"]["inputs"]["text"] = prompt
                        
                    # 节点 37 是 EmptyLatentImage 空白画布节点
                    if "37" in workflow_data and "inputs" in workflow_data["37"]:
                        workflow_data["37"]["inputs"]["width"] = int(w_str)
                        workflow_data["37"]["inputs"]["height"] = int(h_str)
                        # 给模型每次不同的 noise seed
                        import random
                        if "35" in workflow_data and "inputs" in workflow_data["35"]:
                            workflow_data["35"]["inputs"]["seed"] = random.randint(1000000000, 99999999999999)
                        
                        # V19.5 Revision: 自动注入负向提示词 (Negative Prompt Injection)
                        neg_prompt = task.get("neg_prompt", "bad anatomy, blurry face, text distortion, watermark, duplicate features")
                        # 启发式识别负向提示词节点：寻找 class_type 为 CLIPTextEncode 的节点，且 ID 不是 34
                        for node_id, node_info in workflow_data.items():
                            if node_info.get("class_type") == "CLIPTextEncode" and node_id != "34":
                                if "inputs" in node_info and "text" in node_info["inputs"]:
                                    node_info["inputs"]["text"] = neg_prompt
                                    lg.print_log(f"  [Negative] 已将负面提示词注入节点 {node_id}")
                                    break

                        # V7.0 特有：NF4 优化 - 如果检测到是 NF4 工作流，注入质量增强词
                        if "z_image_turbo_nvfp4" in str(workflow_data):
                            if "34" in workflow_data and "inputs" in workflow_data["34"]:
                                prompt = f"{prompt}, high quality, high resolution, masterpiece, detailed, cinematic lighting"
                                workflow_data["34"]["inputs"]["text"] = prompt

                    # 3. 先建立 WebSocket 连接，再提交任务（确保不丢消息）
                    img_filename = None
                    try:
                        import websocket as ws_client  # websocket-client 库
                        import uuid
                        
                        ws_url = comfy_base_url.replace("http://", "ws://").replace("https://", "wss://")
                        client_id = str(uuid.uuid4())
                        
                        lg.print_log(f"  🔗 正在连接 ComfyUI WebSocket...")
                        ws = ws_client.WebSocket()
                        ws.settimeout(99999)  # 用户禁用超时限制
                        ws.connect(f"{ws_url}/ws?clientId={client_id}", timeout=60)
                        lg.print_log(f"  ✅ WebSocket 连接已建立 (clientId: {client_id[:8]})")
                        
                        # 提交任务时必须带上 client_id，让 WS 只收到自己任务的消息
                        prompt_payload = {"prompt": workflow_data, "client_id": client_id}
                        res = req_lib.post(f"{comfy_base_url}/prompt", json=prompt_payload, timeout=10)
                        if res.status_code != 200:
                            ws.close()
                            raise Exception(f"提交 ComfyUI 任务失败: {res.text}")
                            
                        res_json = res.json()
                        prompt_id = res_json.get("prompt_id")
                        if not prompt_id:
                            ws.close()
                            raise Exception(f"未能在返回体中找到 prompt_id: {res_json}")
                            
                        lg.print_log(f"  📤 任务已提交 (prompt_id: {prompt_id}), 实时跟踪进度中...")
                        
                        # 4. 实时监听 WebSocket 消息
                        try:
                            while True:
                                raw = ws.recv()
                                if isinstance(raw, bytes):
                                    continue  # 跳过二进制预览帧
                                msg = json.loads(raw)
                                msg_type = msg.get("type", "")
                                data = msg.get("data", {})
                                
                                if msg_type == "execution_start":
                                    lg.print_log(f"  ⚡ ComfyUI 开始执行工作流...")
                                    
                                elif msg_type == "execution_cached":
                                    cached_nodes = data.get("nodes", [])
                                    if cached_nodes:
                                        lg.print_log(f"  ⏩ 已缓存节点 (跳过): {', '.join(cached_nodes)}")
                                        
                                elif msg_type == "executing":
                                    node_id = data.get("node")
                                    if node_id is None:
                                        # node=None 表示该 prompt 执行完毕
                                        lg.print_log(f"  ✅ ComfyUI 工作流执行完毕!")
                                        break
                                    # 优先读 _meta.title（人性化名称），其次 class_type
                                    node_info = workflow_data.get(str(node_id), {})
                                    node_title = node_info.get("_meta", {}).get("title") or node_info.get("class_type", f"Node-{node_id}")
                                    lg.print_log(f"  🔄 正在执行节点 [{node_id}] {node_title}")
                                    lg.print_log(f"[PROGRESS:VISUAL:DETAIL] 图片 {idx+1}/{len(all_tasks)} | 节点 {node_title}", "internal")
                                    
                                elif msg_type == "progress":
                                    step = data.get("value", 0)
                                    max_step = data.get("max", 0)
                                    if max_step > 0:
                                        pct = int(step / max_step * 100)
                                        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                                        lg.print_log(f"  📊 采样进度: [{bar}] {step}/{max_step} ({pct}%)")
                                        lg.print_log(f"[PROGRESS:VISUAL:DETAIL] 图片 {idx+1}/{len(all_tasks)} | 采样 {step}/{max_step} ({pct}%)", "internal")
                                        
                                elif msg_type == "executed":
                                    output_data = data.get("output", {})
                                    if "images" in output_data and len(output_data["images"]) > 0:
                                        img_filename = output_data["images"][0].get("filename")
                                        lg.print_log(f"  🖼️ 节点输出图片: {img_filename}")
                                        
                                elif msg_type == "execution_error":
                                    err_msg = data.get("exception_message", "未知错误")
                                    err_node_id = data.get("node_id", "?")
                                    err_node_type = data.get("node_type", "?")
                                    err_traceback = data.get("traceback", [])
                                    # 从工作流中获取出错节点的人性化名称
                                    err_node_info = workflow_data.get(str(err_node_id), {})
                                    err_node_title = err_node_info.get("_meta", {}).get("title") or err_node_type
                                    
                                    lg.print_log(f"  ❌ ComfyUI 执行错误!", "error")
                                    lg.print_log(f"  ❌ 出错节点: [{err_node_id}] {err_node_title} (类型: {err_node_type})", "error")
                                    lg.print_log(f"  ❌ 错误信息: {err_msg}", "error")
                                    if err_traceback:
                                        # 只显示 traceback 的最后几行（最关键的部分）
                                        tb_text = "\n".join(err_traceback) if isinstance(err_traceback, list) else str(err_traceback)
                                        tb_lines = tb_text.strip().split("\n")
                                        # 最多显示最后5行
                                        relevant_lines = tb_lines[-5:] if len(tb_lines) > 5 else tb_lines
                                        for line in relevant_lines:
                                            lg.print_log(f"  ❌ {line.strip()}", "error")
                                    raise Exception(f"ComfyUI 节点 [{err_node_id}] {err_node_title} 执行错误: {err_msg}")
                        finally:
                            ws.close()
                            
                        # WebSocket 完成后，如果没从 executed 消息拿到文件名，从 history 兜底获取
                        if not img_filename:
                            hist_res = req_lib.get(f"{comfy_base_url}/history/{prompt_id}", timeout=10)
                            if hist_res.status_code == 200:
                                hist_data = hist_res.json()
                                if prompt_id in hist_data:
                                    outputs = hist_data[prompt_id].get("outputs", {})
                                    for node_id_str, output_info in outputs.items():
                                        if "images" in output_info and len(output_info["images"]) > 0:
                                            img_filename = output_info["images"][0].get("filename")
                                            break
                                            
                    except ImportError:
                        # websocket-client 未安装，降级回 HTTP 轮询
                        lg.print_log("  ⚠️ websocket-client 未安装，降级为 HTTP 轮询 (pip install websocket-client 可启用实时进度)", "warning")
                        
                        # 降级模式下独立提交任务
                        prompt_payload = {"prompt": workflow_data}
                        res = req_lib.post(f"{comfy_base_url}/prompt", json=prompt_payload, timeout=10)
                        if res.status_code != 200:
                            raise Exception(f"提交 ComfyUI 任务失败: {res.text}")
                        res_json = res.json()
                        prompt_id = res_json.get("prompt_id")
                        if not prompt_id:
                            raise Exception(f"未能在返回体中找到 prompt_id: {res_json}")
                        lg.print_log(f"  📤 任务已提交 (prompt_id: {prompt_id}), 开始轮询...")
                        
                        for poll_round in range(100):
                            time.sleep(3)
                            hist_res = req_lib.get(f"{comfy_base_url}/history/{prompt_id}", timeout=10)
                            if hist_res.status_code == 200:
                                hist_data = hist_res.json()
                                if prompt_id in hist_data:
                                    outputs = hist_data[prompt_id].get("outputs", {})
                                    for node_id_str, output_info in outputs.items():
                                        if "images" in output_info and len(output_info["images"]) > 0:
                                            img_filename = output_info["images"][0].get("filename")
                                            break
                                    if img_filename:
                                        break
                            if (poll_round + 1) % 5 == 0:
                                lg.print_log(f"  ⏳ 仍在等待 ComfyUI 生成... ({(poll_round+1)*3}s)")
                    
                    if not img_filename:
                        raise Exception("ComfyUI 生成图片超时或失败 (无输出文件)")
                        
                    # 5. 下载图片并保存到本项目 images 对应目录
                    view_url = f"{comfy_base_url}/view?filename={img_filename}&type=output"
                    file_name = f"comfyui_{int(time.time()*1000)}_{idx}.png"
                    file_path = os.path.join(str(image_dir), file_name)
                    with open(file_path, "wb") as f:
                        f.write(req_lib.get(view_url, timeout=30).content)
                    img_path = file_path
                    
                    # 6. 防止 OOM：显式调用 ComfyUI 清理显存和卸载模型的接口
                    try:
                        req_lib.post(f"{comfy_base_url}/free", json={"unload_models": True, "free_memory": True}, timeout=5)
                        lg.print_log("  [清理] 已发送 ComfyUI 显存释放指令，防止连续生成 OOM")
                    except Exception as clean_e:
                        lg.print_log(f"  [清理] 尝试发送清理指令失败 (可忽略): {str(clean_e)}", "warning")
                        
                else:
                    lg.print_log(f"  [跳过] 图像API未配置或不支持 (type={img_api_type})", "warning")
                    
            except Exception as e:
                lg.print_log(f"  [失败] 图片 {idx+1} 生成异常: {e}", "error")
            
            # 替换占位符
            if not img_path:
                continue
            generated_count += 1
            img_tag = f'<img src="/images/{os.path.basename(img_path)}" alt="{prompt[:50]}" style="max-width:100%;border-radius:12px;margin:16px 0;box-shadow:0 10px 30px rgba(0,0,0,0.1);display:block;">'
            
            if "original_element" in task and task["original_element"]:
                # HTML 模式：使用 BeautifulSoup 对象直接替换
                try:
                    new_img_soup = BeautifulSoup(img_tag, 'html.parser')
                    task["original_element"].replace_with(new_img_soup.contents[0])
                    lg.print_log(f"  ✅ HTML 图片 {idx+1} 替换成功")
                except Exception as replace_e:
                    lg.print_log(f"  ⚠️ HTML 替换失败，降级使用字符串替换: {replace_e}", "warning")
                    result_text = result_text.replace(str(task["original_element"]), img_tag)
            elif "original" in task and task["original"]:
                # Markdown 或正则降级模式：暴力字符串替换
                result_text = result_text.replace(task["original"], img_tag)
                lg.print_log(f"  ✅ 标记图片 {idx+1} 替换成功")

        # 如果有解析过 BeautifulSoup，并且有任务是通过对象替换的，则需要同步回字符串
        if 'soup' in locals() and any("original_element" in t for t in all_tasks):
            # 使用 formatter=None 避免转义字符（如 URL 中的 &）
            result_text = soup.decode(formatter=None)
            
        # 计算失败数量
        failed_count = total_images - generated_count
        
        if failed_count > 0:
            lg.print_log(f"[VisualAssets] ⚠️ 图片生成部分失败：成功 {generated_count} 张，失败 {failed_count} 张", "warning")
            lg.print_log(f"[VisualAssets] 💡 提示：请检查 ComfyUI 是否正在运行，或图片API配置是否正确", "warning")
            
            # 对于失败的占位符，用占位图片替换（而不是直接删除）
            def replace_failed_placeholder(match):
                placeholder_text = match.group(0)
                # 提取提示词（如果有）
                prompt_match = re.search(r'\[\[V-SCENE:\s*(.+?)\s*\]\]', placeholder_text)
                alt_text = prompt_match.group(1)[:50] if prompt_match else "图片生成失败"
                # 返回一个占位图片标签
                return f'<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:12px;padding:40px 20px;margin:16px 0;text-align:center;color:#fff;box-shadow:0 10px 30px rgba(0,0,0,0.1);"><div style="font-size:24px;margin-bottom:10px;">🖼️</div><div style="font-size:14px;opacity:0.9;">图片待生成</div><div style="font-size:12px;opacity:0.7;margin-top:8px;max-width:80%;word-wrap:break-word;">{alt_text}</div></div>'
            
            # 替换 V-SCENE 占位符为占位图片
            result_text = re.sub(r'\[\[V-SCENE:.*?\]\]', replace_failed_placeholder, result_text, flags=re.DOTALL)
            # 移除其他类型的占位符标记（这些通常不包含重要信息）
            result_text = re.sub(r'\[IMG_PROMPT:.*?\]', '', result_text)
            result_text = re.sub(r'\[图片解析[:：].*?\]', '', result_text)
        else:
            lg.print_log(f"[VisualAssets] ✅ 生成完成：成功生成并替换了 {generated_count} 张图片")
            # 全部成功时，清理残留标记
            result_text = re.sub(r'\[\[V-SCENE:.*?\]\]', '', result_text)
            result_text = re.sub(r'\[IMG_PROMPT:.*?\]', '', result_text)
            result_text = re.sub(r'\[图片解析[:：].*?\]', '', result_text)
        
        # 清理后可能产生的连续空行
        result_text = re.sub(r'\n{3,}', '\n\n', result_text)
        
        return result_text

    @classmethod
    def auto_fix_article_images(cls, article_path_str: str) -> dict:
        """自动化补图：扫描文章中的图片占位符并调用图片API生成图片"""
        from pathlib import Path
        import os
        
        file_path = Path(article_path_str)
        if not file_path.exists():
            msg = f"文章路径不存在: {article_path_str}"
            lg.print_log(msg, "error")
            return {"status": "error", "message": msg}

        try:
            lg.print_log(f"开始自动修复文章图片: {article_path_str}", "info")
            content = file_path.read_text(encoding="utf-8")
            
            # V4: 短路检测 — 如果工作流 Step 5 已经完成了所有图片替换，直接跳过
            has_vscene = bool(re.search(r'\[\[V-SCENE:', content))
            has_img_prompt = bool(re.search(r'\[(?:IMG_PROMPT|图片解析)[:：]', content))
            has_empty_placeholder = bool(re.search(r'<div[^>]*class="img-placeholder"[^>]*>(?!.*data-img-prompt)', content))
            
            if not has_vscene and not has_img_prompt and not has_empty_placeholder:
                lg.print_log(f"[VisualAssets] 文章 {file_path.name} 中无未替换的占位符，跳过自动补图 ✅", "success")
                return {"status": "skipped", "message": "所有图片占位符已在工作流中替换完毕"}
            
            # 1. 扫描是否已有提示词 (避免对已包含 prompts 的 HTML 重复注入)
            # 如果文章已经有提示词标记（[IMG_PROMPT]）或者 placeholder 已包含数据属性，说明 LLM 已经完成了分析
            has_explicit_prompts = re.search(r'\[(?:IMG_PROMPT|图片解析)[:：]\s*.+?\s*\|', content)
            has_data_prompts = 'data-img-prompt="' in content and 'img-placeholder' in content
            
            if (not has_explicit_prompts and not has_data_prompts) and ('<div class="img-placeholder"' in content or '[图片解析：]' in content):
                lg.print_log(f"[VisualAssets] 文章 {file_path.name} 包含空位，启动智能分析进程...", "info")
                content = cls.inject_image_prompts(content)
                file_path.write_text(content, encoding="utf-8")
            
            # 2. 触发预览与后台生成
            updated_content = cls.sync_trigger_image_generation(content)
            
            # 保存更新后的内容 (包含 <img> 标签)
            if updated_content != content:
                file_path.write_text(updated_content, encoding="utf-8")
                lg.print_log("文章图片占位符已成功替换为生成的图片。", "success")
            
            lg.print_log(f"自动补图流程结束。", "success")
            return {"status": "success", "message": "文章图片占位符已成功替换为生成的图片。"}
            
        except Exception as e:
            msg = f"自动修复文章图片遇到异常: {str(e)}"
            lg.print_log(msg, "error")
            import traceback
            lg.print_log(traceback.format_exc(), "error")
            return {"status": "error", "message": msg}

    @classmethod
    def _handle_single_generation(cls, prompt, ratio, size, image_dir, idx):
        """内部辅助方法：处理单张图片的生成逻辑 (提取自原有庞大的 sync_trigger_image_generation)"""
        try:
            from src.ai_write_x.config.config import Config
            import os, time, requests as req_lib
            
            config = Config.get_instance()
            img_api_type = config.img_api_type
            img_api_key = config.img_api_key
            img_api_model = config.img_api_model
            
            # 获取 api_base
            img_config = config.config.get("img_api", {})
            api_bases = {
                "modelscope": "https://api-inference.modelscope.cn/v1",
                "ali": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            }
            img_type_cfg = img_config.get(img_api_type, {})
            if img_api_type == "custom" and isinstance(img_type_cfg, list):
                custom_index = int(img_config.get("custom_index", 0) or 0)
                if 0 <= custom_index < len(img_type_cfg):
                    img_type_cfg = img_type_cfg[custom_index]
                else:
                    img_type_cfg = img_type_cfg[0] if img_type_cfg else {}
            elif not isinstance(img_type_cfg, dict):
                img_type_cfg = {}
            api_base = img_type_cfg.get("api_base", api_bases.get(img_api_type, ""))
            
            # 同步更新当前使用的 key/model
            if img_api_type == "custom":
                img_api_key = img_type_cfg.get("api_key", img_api_key)
                img_api_model = img_type_cfg.get("model", img_api_model)
            
            # --- 核心生成逻辑 ---
            img_path = None
            
            if img_api_type == "picsum":
                w_h = size.split("*")
                download_url = f"https://picsum.photos/{w_h[0]}/{w_h[1]}?random={int(time.time())+idx}"
                from src.ai_write_x.utils import utils as u
                img_path = u.download_and_save_image(download_url, str(image_dir))
                
            elif img_api_type in ("modelscope", "ali", "custom") and (api_base or img_api_type == "custom") and img_api_key:
                # 复用原有 API 调用逻辑 (简化版，确保核心可用)
                # ... (由于长度限制，这里通常应该调用一个更通用的 generate_image_sync 方法)
                # 为了保持代码简洁且不破坏原有复杂逻辑，我们在这里直接声明一个 generate_image_sync 的代理调用
                # 实际上 sync_trigger_image_generation(str) 原本就包含了这些。
                # 我们可以通过临时构建一个带有该标记的字符串来复用原有方法。
                marker = f"[IMG_PROMPT: {prompt} | {ratio}]"
                result_content = cls.sync_trigger_image_generation(marker)
                # 如果成功，result_content 应该包含了图片的 markdown 链接或者已经被处理
                # 我们通过正则搜寻结果中的文件名
                match = re.search(r'\((images/[^)]+)\)', result_content)
                if match:
                    rel_path = match.group(1)
                    # 转换回绝对路径
                    from src.ai_write_x.utils.path_manager import PathManager
                    img_path = os.path.join(str(PathManager.get_image_dir()), os.path.basename(rel_path))

            elif img_api_type == "comfyui":
                # ComfyUI 的逻辑也可以通过同样的方式复用
                marker = f"[IMG_PROMPT: {prompt} | {ratio}]"
                result_content = cls.sync_trigger_image_generation(marker)
                match = re.search(r'\((images/[^)]+)\)', result_content)
                if match:
                    rel_path = match.group(1)
                    from src.ai_write_x.utils.path_manager import PathManager
                    img_path = os.path.join(str(PathManager.get_image_dir()), os.path.basename(rel_path))
            
            return img_path
        except Exception as e:
            lg.print_log(f"单张图片生成核心失败: {e}", "error")
            return None

    @staticmethod
    def _ratio_to_size(ratio: str) -> str:
        """将比例字符串转换为像素尺寸"""
        ratio_map = {
            "16:9": "1024*576",
            "2.35:1": "1024*436",
            "4:3": "1024*768",
            "3:4": "768*1024",
            "1:1": "1024*1024",
        }
        return ratio_map.get(ratio, "1024*1024")
