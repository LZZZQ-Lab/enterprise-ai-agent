"""
Prompt 管理系统入口。

Task 1.4：PromptBuilder + PromptContext + templates。
"""

from app.prompts.builder import PromptBuilder
from app.prompts.context import PromptContext
from app.prompts.context import load_template
from app.prompts.manager import PromptManager
from app.prompts.manager import get_default_prompt_manager
from app.prompts.manager import DEVELOPER_PROMPT_ID
from app.prompts.manager import REVIEWER_PROMPT_ID
from app.prompts.manager import TESTER_PROMPT_ID
from app.prompts.repository import PromptRepository
from app.prompts.repository import get_default_prompt_repository
from app.prompts.version import PromptVersion

__all__ = [
    "PromptBuilder",
    "PromptContext",
    "PromptManager",
    "PromptRepository",
    "PromptVersion",
    "load_template",
    "get_default_prompt_manager",
    "get_default_prompt_repository",
    "DEVELOPER_PROMPT_ID",
    "REVIEWER_PROMPT_ID",
    "TESTER_PROMPT_ID",
]
