# schemas.py
# 这个文件定义了我们系统中所有重要的数据结构。
# 它使用Pydantic来确保数据的一致性和有效性。

from pydantic import BaseModel, Field, conint, constr
from typing import List, Literal, Optional

# --- Creative Agent Schemas ---

class CreativeConcept(BaseModel):
    """定义单个创意概念的结构"""
    title: constr(min_length=3, max_length=100) = Field(
        ...,
        description="一个引人入胜、简短的创意标题"
    )
    logline: constr(min_length=10) = Field(
        ...,
        description="对核心创意的简短描述（一到两句话）"
    )
    why_it_works: str = Field(
        ...,
        description="简要解释为什么这个创意具有病毒式传播的潜力或吸引力"
    )

class CreativeOutput(BaseModel):
    """定义创意总监AI必须返回的最终JSON结构"""
    creative_options: List[CreativeConcept] = Field(
        ...,
        min_items=3,
        max_items=3,
        description="一个必须恰好包含三个不同创意概念的列表"
    )

# --- Storyboard Agent Schemas ---

class Scene(BaseModel):
    """定义故事板中单个场景的结构"""
    scene_number: int = Field(..., description="场景的顺序编号，从1开始")
    act: Literal['HOOK', 'BUILD', 'PAYOFF'] = Field(
        ...,
        description="该场景在三幕式结构中所处的位置"
    )
    visual_description: str = Field(
        ...,
        description="纯视觉画面描述，无文字。详细描述镜头内容、角色动作和环境。"
    )
    camera_shot: str = Field(
        ...,
        description="具体的镜头语言，例如 'Medium shot', 'Extreme close-up', 'Wide establishing shot'"
    )
    pacing_seconds: float = Field(
        ...,
        gt=0,
        description="这个场景预计的持续秒数"
    )

class StoryboardOutput(BaseModel):
    """定义故事板画师AI必须返回的最终JSON结构"""
    scenes: List[Scene]

# --- QA/Critic Agent Schemas ---

class QACritique(BaseModel):
    """定义QA裁判AI对故事板的评估结构"""
    overall_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="对故事板的总体质量评分（0-10分）"
    )
    is_approved: bool = Field(
        ...,
        description="裁判是否批准此故事板进入下一步"
    )
    feedback: str = Field(
        ...,
        description="具体的、可操作的修改建议或赞扬。如果不批准，必须清晰说明原因。"
    )