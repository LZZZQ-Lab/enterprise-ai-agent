"""
内置示例插件：Search / Git / Database（Task 6.6）。
"""

from app.plugins.builtin.database_plugin import DatabasePlugin
from app.plugins.builtin.git_plugin import GitPlugin
from app.plugins.builtin.search_plugin import SearchAgentPlugin
from app.plugins.builtin.search_plugin import SearchPlugin
from app.plugins.builtin.search_workflow_plugin import SearchWorkflowPlugin

__all__ = [
    "SearchPlugin",
    "GitPlugin",
    "DatabasePlugin",
    "SearchWorkflowPlugin",
]


def get_plugins():
    return [
        SearchPlugin(),
        SearchAgentPlugin(),
        GitPlugin(),
        DatabasePlugin(),
        SearchWorkflowPlugin(),
    ]
