# services.py
import logging
import json
import os
from schemas import CreativeOutput, StoryboardOutput, QACritique # 从我们的数据契约中导入模型
import google.generativeai as genai
from pydantic import ValidationError

# 配置日志
log = logging.getLogger("pf.api.services")

# --- Prompt Templates (Stored in code) ---
PROMPT_CREATIVE_V1 = """# ROLE: Creative Director

You are an expert Creative Director at a top-tier viral marketing agency. Your specialty is generating short-form video concepts (TikTok, YouTube Shorts, Instagram Reels) that are highly engaging with strong hooks, tight emotional arcs, and satisfying payoffs. You think fast, write concisely, and propose ideas that are simple to execute.

# TASK

Take the user's raw brief and transform it into THREE distinct, compelling, and actionable short-form video concepts. Each concept must be a unique angle on the user's request.

# HARD RULES (FOLLOW EXACTLY)

1) Three Options Mandatory
- You MUST return exactly 3 concepts. No more, no less.

2) Concise and Punchy
- Keep everything brief. Titles ≤ 8 words. Loglines 1–2 sentences. Why_it_works ≤ 1–2 sentences.

3) Obey User Constraints
- Respect any constraints in the user input (topic, length, tone, platform, style, target audience, region/language, compliance).

4) JSON Output Only
- OUTPUT MUST be a single valid JSON object matching the schema below.
- Do NOT include any extra text, explanations, comments, or markdown formatting (no backticks, no ```json).
- Do NOT include trailing commas.
- Escape special characters properly.

5) Originality & Practicality
- Each concept should be clearly different in angle/format.
- Avoid generic clichés; each idea should be immediately shootable on a phone.

6) No Disallowed Content
- Do not output illegal, harmful, hateful, or NSFW content. Keep brand-safe and platform-compliant.

# INPUT FORMAT (PASSED IN AS JSON)

The user will provide a JSON brief. You will receive it here:

{{USER_INPUT_JSON}}

# OUTPUT SCHEMA (STRICT)

Your output MUST be a JSON object with one key "creative_options", which is a list of exactly 3 concept objects. 
Each concept object MUST have:
- title (string): Catchy, ≤ 8 words.
- logline (string): 1–2 sentences summarizing the idea.
- why_it_works (string): 1–2 sentences on the psychological/marketing lever.

# VALIDATION CHECK BEFORE YOU OUTPUT

Before emitting your final JSON:
- Confirm exactly 3 concepts exist.
- Confirm all required keys exist and are strings.
- Confirm lengths (titles ≤ 8 words; each field concise).
- Confirm no extra keys, no comments, no markdown, no trailing commas.
- If user constraints conflict, prefer compliance and keep ideas safe.

# FAILURE MODE

If the user input is missing critical info (e.g., product or audience), infer sensible defaults and proceed. Never ask follow-up questions in the output. Always return valid JSON in the required schema.
"""

# --- 核心 Gemini 调用函数 (带验证与修复) ---

def call_gemini_with_validation(prompt: str, output_schema, model_name='gemini-1.5-pro'):
    """
    调用 Gemini API，并使用指定的 Pydantic schema 对其 JSON 输出进行验证。
    如果验证失败，它会尝试自动修复最多2次。
    """
    MAX_RETRIES = 3
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY environment variable not set.")
        raise ValueError("Gemini API Key is not configured.")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(model_name)
    
    current_prompt = prompt

    for attempt in range(MAX_RETRIES):
        try:
            log.info(f"Calling Gemini (Attempt {attempt + 1}/{MAX_RETRIES})...")
            response = model.generate_content(
                current_prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            if not response.text:
                raise ValueError("Received an empty response from Gemini API.")

            parsed_json = json.loads(response.text)
            
            validated_output = output_schema.model_validate(parsed_json)
            log.info("Gemini output validated successfully.")
            return validated_output

        except (json.JSONDecodeError, ValidationError) as e:
            log.warning(f"Validation failed on attempt {attempt + 1}: {e}")
            if attempt == MAX_RETRIES - 1:
                log.error("Max retries reached. Failing operation.")
                raise e
            
            error_feedback = f"""
[SYSTEM NOTE]: Your previous JSON output failed validation.
Error details: {e}
Please review the expected JSON schema and your last output, then provide a corrected and complete JSON response.
Do not repeat the same mistake. Output ONLY the valid JSON.
The original prompt was:
---
{prompt}
---
"""
            current_prompt = error_feedback

        except Exception as e:
            log.error(f"An unexpected error occurred while calling Gemini: {e}")
            raise e

    raise RuntimeError("Gemini call failed after maximum retries.")


# --- 工作流服务函数 ---

def create_project_and_generate_creatives(db_conn, user_id: str, user_input: dict):
    """
    步骤1: 创建项目并调用创意总监AI生成3个创意。
    """
    log.info(f"Starting creative generation for user {user_id}...")
    project_id = None
    try:
        # 使用 with 语句确保游标在使用后被关闭
        with db_conn.cursor() as cur:
            # 步骤 1: 在 `projects` 表中插入一条新记录，并取回新生成的 project_id
            sql = """
                INSERT INTO projects (user_id, project_title, user_input, video_length_sec)
                VALUES (%s, %s, %s::jsonb, %s) RETURNING id;
            """
            cur.execute(sql, (
                user_id,
                user_input.get('project_title'),
                json.dumps(user_input),
                user_input.get('video_length_sec')
            ))
            project_id = cur.fetchone()[0]
            log.info(f"Project created with ID: {project_id}")

            # 步骤 2 & 3: 使用用户的输入填充Prompt模板
            prompt = PROMPT_CREATIVE_V1.replace("{{USER_INPUT_JSON}}", json.dumps(user_input, ensure_ascii=False))

            # 步骤 4: 调用我们的验证函数来执行Gemini API调用
            validated_output = call_gemini_with_validation(prompt, CreativeOutput)

            # 步骤 5: 将AI返回的3个创意选项循环写入数据库
            creative_options_to_return = []
            for i, option in enumerate(validated_output.creative_options):
                option_sql = """
                    INSERT INTO creative_options (project_id, option_index, title, logline, why_it_works)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id;
                """
                cur.execute(option_sql, (project_id, i, option.title, option.logline, option.why_it_works))
                
                # 将完整数据添加到返回列表中，包括新生成的ID
                option_data = option.model_dump()
                option_data['id'] = str(cur.fetchone()[0])
                creative_options_to_return.append(option_data)
            
            # 如果所有操作都成功，提交数据库事务
            db_conn.commit()
            log.info(f"Successfully saved 3 creative options for project {project_id}")
            
            # 步骤 6: 返回project_id和生成的创意选项的完整列表
            return str(project_id), creative_options_to_return

    except Exception as e:
        log.error(f"Error in create_project_and_generate_creatives for user {user_id}: {e}", exc_info=True)
        if db_conn:
            db_conn.rollback() # 如果过程中发生任何错误，回滚所有数据库更改，保证数据一致性
        raise # 将异常向上抛出，让 main.py 中的API路由来处理并返回500错误

def select_creative_and_generate_storyboard(db_conn, project_id: str, selected_creative_id: str):
    """
    步骤2: 用户选择创意后，调用故事板画师AI和QA裁判AI。
    """
    # 伪代码:
    # 1. 将 `creative_options` 表中对应的选项标记为 is_selected = TRUE。
    # 2. 从数据库中获取项目信息（如 video_length）和选定的创意文本。
    # 3. 计算所需的场景数量 (e.g., video_length / 4)。
    # 4. 加载 prompt_storyboard.v1.0.txt 模板并填充数据。
    # 5. 调用 call_gemini_with_validation(prompt, StoryboardOutput) 生成故事板。
    # 6. 【QA步骤】加载 prompt_qa_critic.v1.0.txt 并将生成的故事板传入。
    # 7. 调用 call_gemini_with_validation(qa_prompt, QACritique) 获取QA结果。
    # 8. 将故事板、QA结果存入 `storyboards` 表。
    # 9. 返回故事板和QA结果。
    log.info(f"Generating storyboard for project {project_id}...")
    # ... 在此处将添加完整的数据库和AI调用逻辑 ...
    pass # 占位符

def generate_blueprints_for_storyboard(db_conn, project_id: str, storyboard_id: str):
    """
    步骤3: 为已批准的故事板生成所有VEO Blueprints。
    """
    # 伪代码:
    # 1. 从 `storyboards` 表中获取场景数组。
    # 2. 【批处理优先】加载 prompt_technical.v1.0.txt。设计一个能处理整个场景数组的Prompt。
    # 3. 调用 Gemini 一次，要求它为所有场景返回一个Blueprints数组。
    # 4. 【如果批处理失败，回退到循环】
    #    - 遍历每个场景。
    #    - 为每个场景填充 technical prompt 模板。
    #    - 单独调用 Gemini API。
    # 5. 将所有生成的 blueprints 存入 `blueprints` 表。
    # 6. 更新 `projects` 表的状态为 'complete'。
    # 7. 返回所有生成的blueprints。
    log.info(f"Generating blueprints for storyboard {storyboard_id}...")
    # ... 在此处将添加完整的数据库和AI调用逻辑 ...
    pass # 占位符