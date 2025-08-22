# services.py
import logging
import json
import os
from schemas import CreativeOutput, StoryboardOutput, QACritique # 从我们的数据契约中导入模型
import google.generativeai as genai
from pydantic import ValidationError

# 配置日志
log = logging.getLogger("pf.api.services")

# --- 核心 Gemini 调用函数 (带验证与修复) ---

def call_gemini_with_validation(prompt: str, output_schema, model_name='gemini-1.5-pro'):
    """
    调用 Gemini API，并使用指定的 Pydantic schema 对其 JSON 输出进行验证。
    如果验证失败，它会尝试自动修复最多2次。
    """
    MAX_RETRIES = 3
    # 确保API Key已在环境中配置
    # 注意：在Cloud Run等环境中，推荐使用环境变量来管理API密钥
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.error("GEMINI_API_KEY environment variable not set.")
        raise ValueError("Gemini API Key is not configured.")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(model_name)
    
    # 完整的prompt，用于最后的修复步骤
    current_prompt = prompt

    for attempt in range(MAX_RETRIES):
        try:
            log.info(f"Calling Gemini (Attempt {attempt + 1}/{MAX_RETRIES})...")
            response = model.generate_content(
                current_prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # 1. 解析 JSON
            # response.text 可能为空或不包含有效内容，需要检查
            if not response.text:
                raise ValueError("Received an empty response from Gemini API.")

            parsed_json = json.loads(response.text)
            
            # 2. 使用 Pydantic 模型进行验证
            validated_output = output_schema.model_validate(parsed_json)
            log.info("Gemini output validated successfully.")
            return validated_output

        except (json.JSONDecodeError, ValidationError) as e:
            log.warning(f"Validation failed on attempt {attempt + 1}: {e}")
            if attempt == MAX_RETRIES - 1:
                log.error("Max retries reached. Failing operation.")
                raise e # 最终失败，向上抛出异常
            
            # 3. 构建修复 Prompt
            # 我们将原始prompt和失败信息一起发送，要求AI修正
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

    # 如果循环结束仍未成功，抛出异常
    raise RuntimeError("Gemini call failed after maximum retries.")


# --- 工作流服务函数 ---
# 注意：这些是框架函数。我们将在后续步骤中实现它们的内部逻辑。

def create_project_and_generate_creatives(db_conn, user_id: str, user_input: dict):
    """
    步骤1: 创建项目并调用创意总监AI生成3个创意。
    """
    # 伪代码:
    # 1. 在 `projects` 表中插入一条新记录。获取 project_id。
    # 2. 从 prompts/v1/prompt_creative.v1.0.txt 加载模板。
    # 3. 将 user_input 填充到模板中。
    # 4. 调用 call_gemini_with_validation(prompt, CreativeOutput)。
    # 5. 如果成功，将返回的3个创意存入 `creative_options` 表，关联 project_id。
    # 6. 返回 project_id 和生成的创意选项。
    log.info(f"Creating project for user {user_id}...")
    # ... 在此处将添加完整的数据库和AI调用逻辑 ...
    pass # 占位符

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