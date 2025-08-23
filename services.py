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

PROMPT_STORYBOARD_V1 = """ROLE

You are a professional Storyboard Artist for short-form video. You are a master of visual storytelling and timing, and you structure sequences using a clear three‑act arc. You think in shots, blocking, and beats. You translate ideas into concise, visually-driven scenes that are easy to film and fast to understand.

TASK

Convert the {{SELECTED_CREATIVE_CONCEPT}} into a storyboard composed of exactly {{NUMBER_OF_SCENES}} scenes whose combined duration equals {{VIDEO_LENGTH_IN_SECONDS}} seconds. Each scene must specify its act role (HOOK, BUILD, or PAYOFF), a purely visual description of the action, a precise camera shot term, and an allocated pacing duration in seconds.

RULES

Three‑Act Requirement: Distribute scenes across HOOK, BUILD, and PAYOFF.
If {{NUMBER_OF_SCENES}} ≥ 3: first scene = HOOK, last scene = PAYOFF, all middle scenes = BUILD.
If {{NUMBER_OF_SCENES}} = 2: scene 1 = HOOK, scene 2 = PAYOFF.
If {{NUMBER_OF_SCENES}} = 1: single scene = PAYOFF (compress HOOK→BUILD→PAYOFF into one visual beat).
Text‑Free Visuals Only: The visual_description must be purely visual (actions, expressions, props, environment, blocking). Do NOT include sound, music, voiceover, dialogue, captions, on‑screen text, logos, or written characters.
Cinematography Terms: Use standard shot labels and movements for camera_shot (e.g., ECU, CU, MCU, MS, MLS, WS, EWS, OTS, POV, Static Tripod, Handheld, Tracking, Push‑in/Dolly‑in, Pull‑out, Crane Up/Down, Tilt Up/Down, Rack Focus). One concise phrase only.
Exact Timing: Ensure the sum of all pacing_seconds equals exactly {{VIDEO_LENGTH_IN_SECONDS}}. Use floats. If rounding causes drift, adjust the final scene’s pacing_seconds to make the total exact.
Output Format: Return ONLY a single, valid JSON object exactly matching the schema below—no commentary, no code fences, no trailing commas.

CONTEXT

SELECTED CREATIVE CONCEPT: {{SELECTED_CREATIVE_CONCEPT}}
TARGET VIDEO LENGTH (seconds): {{VIDEO_LENGTH_IN_SECONDS}}
REQUIRED NUMBER OF SCENES: {{NUMBER_OF_SCENES}}

OUTPUT SCHEMA

Return a JSON object with a single key "scenes" whose value is an array of scene objects. Each scene object must include:
scene_number (integer; starts at 1 and increments by 1)
act (string; one of "HOOK", "BUILD", "PAYOFF")
visual_description (string; 1–2 concise sentences; purely visual; present tense; no sound/text)
camera_shot (string; precise standard term as per Rule 3)
pacing_seconds (float; positive; totals across scenes must equal {{VIDEO_LENGTH_IN_SECONDS}})
"""

PROMPT_QA_CRITIC_V1 = """ROLE

You are a ruthless but fair QA Critic and storytelling expert. Your only mission is to ensure that every storyboard is excellent, coherent, and production-ready. You evaluate storytelling strength, pacing logic, clarity of the hook, and the effectiveness of the payoff. You do not flatter; you provide sharp, specific, and actionable feedback.

TASK

Review the provided storyboard ({{STORYBOARD_SCENES_JSON}}) based on the selected creative concept ({{SELECTED_CREATIVE_CONCEPT}}) and the target video length ({{VIDEO_LENGTH_IN_SECONDS}}). You must:
Score the storyboard on a strict 0.0–10.0 scale.
Decide if it is approved for production (true or false).
Provide detailed, actionable feedback to guide improvement.

RULES

Holistic Review: You must evaluate the storyboard as a whole — story clarity, pacing, balance of HOOK/BUILD/PAYOFF, visual flow, and satisfaction of the payoff.
Actionable Feedback: If the storyboard is not approved, your feedback must explain exactly what is wrong and what needs to change.
Honest Scoring: Do not inflate scores. If the overall_score is below 7.0, it must not be approved.
Output Format: The final response must be only a single valid JSON object, with no extra commentary, no code fences, and no trailing commas.

CONTEXT

SELECTED CREATIVE CONCEPT: {{SELECTED_CREATIVE_CONCEPT}}
TARGET VIDEO LENGTH (seconds): {{VIDEO_LENGTH_IN_SECONDS}}
STORYBOARD SCENES JSON: {{STORYBOARD_SCENES_JSON}}

OUTPUT SCHEMA

Your output must be a single JSON object with the following keys:
overall_score (float, 0.0–10.0)
is_approved (boolean)
feedback (string)
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
        with db_conn.cursor() as cur:
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

            prompt = PROMPT_CREATIVE_V1.replace("{{USER_INPUT_JSON}}", json.dumps(user_input, ensure_ascii=False))
            validated_output = call_gemini_with_validation(prompt, CreativeOutput)

            creative_options_to_return = []
            for i, option in enumerate(validated_output.creative_options):
                option_sql = """
                    INSERT INTO creative_options (project_id, option_index, title, logline, why_it_works)
                    VALUES (%s, %s, %s, %s, %s) RETURNING id;
                """
                cur.execute(option_sql, (project_id, i, option.title, option.logline, option.why_it_works))
                
                option_data = option.model_dump()
                option_data['id'] = str(cur.fetchone()[0])
                creative_options_to_return.append(option_data)
            
            db_conn.commit()
            log.info(f"Successfully saved 3 creative options for project {project_id}")
            
            return str(project_id), creative_options_to_return

    except Exception as e:
        log.error(f"Error in create_project_and_generate_creatives for user {user_id}: {e}", exc_info=True)
        if db_conn:
            db_conn.rollback()
        raise

def select_creative_and_generate_storyboard(db_conn, project_id: str, selected_creative_id: str):
    """
    步骤2: 用户选择创意后，调用故事板画师AI和QA裁判AI。
    """
    log.info(f"Starting storyboard generation for project {project_id}...")
    try:
        with db_conn.cursor() as cur:
            # 步骤 1: 将用户选中的创意选项在数据库中标记为 is_selected = TRUE
            cur.execute("UPDATE creative_options SET is_selected = TRUE WHERE id = %s;", (selected_creative_id,))
            log.info(f"Marked creative option {selected_creative_id} as selected.")

            # 步骤 2: 从数据库中获取项目核心信息和选定的创意文本
            sql = """
                SELECT p.video_length_sec, co.title, co.logline, co.why_it_works
                FROM projects p
                JOIN creative_options co ON p.id = co.project_id
                WHERE p.id = %s AND co.id = %s;
            """
            cur.execute(sql, (project_id, selected_creative_id))
            project_info = cur.fetchone()
            if not project_info:
                raise ValueError(f"Could not find project {project_id} or creative option {selected_creative_id}")
            
            video_length_sec, title, logline, why_it_works = project_info
            selected_creative_concept = f"Title: {title}\nLogline: {logline}\nWhy it works: {why_it_works}"

            # 步骤 3: 计算所需的场景数量 (一个简单的业务规则：每5秒一个场景，最少3个)
            num_scenes = max(3, video_length_sec // 5)
            log.info(f"Calculated {num_scenes} scenes for a {video_length_sec} second video.")

            # 步骤 4: 填充故事板Prompt模板
            storyboard_prompt = PROMPT_STORYBOARD_V1.replace("{{SELECTED_CREATIVE_CONCEPT}}", selected_creative_concept)
            storyboard_prompt = storyboard_prompt.replace("{{VIDEO_LENGTH_IN_SECONDS}}", str(video_length_sec))
            storyboard_prompt = storyboard_prompt.replace("{{NUMBER_OF_SCENES}}", str(num_scenes))

            # 步骤 5: 调用 "故事板画师" AI
            storyboard_output = call_gemini_with_validation(storyboard_prompt, StoryboardOutput)
            log.info(f"Storyboard generated successfully for project {project_id}")

            # 步骤 6: 填充QA裁判Prompt模板
            qa_prompt = PROMPT_QA_CRITIC_V1.replace("{{SELECTED_CREATIVE_CONCEPT}}", selected_creative_concept)
            qa_prompt = qa_prompt.replace("{{VIDEO_LENGTH_IN_SECONDS}}", str(video_length_sec))
            # 将生成的场景对象数组转换为JSON字符串，以便注入到Prompt中
            storyboard_json_string = storyboard_output.model_dump_json()
            qa_prompt = qa_prompt.replace("{{STORYBOARD_SCENES_JSON}}", storyboard_json_string)

            # 步骤 7: 调用 "QA裁判" AI
            qa_critique_output = call_gemini_with_validation(qa_prompt, QACritique)
            log.info(f"QA critique generated successfully for project {project_id}")
            
            # 步骤 8: 将故事板和QA结果存入 `storyboards` 表
            qa_status = 'passed' if qa_critique_output.is_approved else 'failed'
            storyboard_insert_sql = """
                INSERT INTO storyboards (project_id, creative_option_id, scenes, qa_status, qa_feedback)
                VALUES (%s, %s, %s::jsonb, %s, %s);
            """
            cur.execute(storyboard_insert_sql, (
                project_id,
                selected_creative_id,
                storyboard_json_string, # 存储完整的场景JSON
                qa_status,
                qa_critique_output.feedback
            ))

            db_conn.commit()
            log.info(f"Storyboard and QA results saved for project {project_id}")
            
            # 步骤 9: 返回故事板和QA结果
            return storyboard_output.model_dump(), qa_critique_output.model_dump()

    except Exception as e:
        log.error(f"Error in select_creative_and_generate_storyboard for project {project_id}: {e}", exc_info=True)
        if db_conn:
            db_conn.rollback()
        raise

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