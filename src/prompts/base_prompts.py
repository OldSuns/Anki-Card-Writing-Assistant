"""
提示词管理器模块
负责管理不同类型的提示词模板，支持多种语言和难度级别
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import re

@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    description: str
    template: str
    language: str
    difficulty: str
    category: str
    variables: List[str]

class BasePromptManager:
    """基础提示词管理器"""
    
    def __init__(self, prompts_directory: str = "src/prompts"):
        self.prompts: Dict[str, PromptTemplate] = {}
        self.logger = logging.getLogger(__name__)
        self.prompts_directory = Path(prompts_directory)
        self._load_prompts_from_files()
    
    def _load_prompts_from_files(self):
        """从markdown文件加载提示词"""
        # 确保提示词目录存在
        self.prompts_directory.mkdir(exist_ok=True)
        
        # 基础提示词配置
        base_prompts_config = {
            "standard_qa": {
                "name": "标准问答卡片",
                "description": "生成标准的前后问答卡片",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "standard",
                "variables": ["card_count", "language", "difficulty", "template_name", "content"]
            },
            "cloze": {
                "name": "填空卡片",
                "description": "生成填空类型的记忆卡片",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "cloze",
                "variables": ["card_count", "language", "difficulty", "template_name", "content"]
            }
        }
        
        # 加载每个基础提示词
        for prompt_key, config in base_prompts_config.items():
            prompt_file = self.prompts_directory / f"{prompt_key}.md"
            
            if prompt_file.exists():
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        template_content = f.read().strip()
                    
                    self.prompts[prompt_key] = PromptTemplate(
                        name=config["name"],
                        description=config["description"],
                        template=template_content,
                        language=config["language"],
                        difficulty=config["difficulty"],
                        category=config["category"],
                        variables=config["variables"]
                    )
                    self.logger.info(f"已加载提示词: {prompt_key}")
                except Exception as e:
                    self.logger.error(f"加载提示词 {prompt_key} 失败: {e}")
            else:
                self.logger.warning(f"提示词文件不存在: {prompt_file}")
        
        self.logger.info(f"总共加载了 {len(self.prompts)} 个提示词模板")
    
    def get_prompt(self, prompt_type: str, template=None, language: str = "zh-CN", 
                  difficulty: str = "medium") -> str:
        """获取提示词，优先读取用户文件"""
        # 直接使用提示词类型作为键
        prompt_key = prompt_type
        
        if prompt_key not in self.prompts:
            raise ValueError(f"未找到提示词类型: {prompt_type}")
        
        prompt_template = self.prompts[prompt_key]
        
        # 首先尝试读取用户文件
        user_prompt_file = self.prompts_directory / f"{prompt_type}_user.md"
        if user_prompt_file.exists():
            try:
                with open(user_prompt_file, 'r', encoding='utf-8') as f:
                    user_content = f.read().strip()
                self.logger.info(f"从用户文件读取提示词: {prompt_type}_user.md")
                return user_content
            except Exception as e:
                self.logger.warning(f"读取用户文件失败，使用原始内容: {e}")
        
        # 如果用户文件不存在或读取失败，返回原始模板
        return prompt_template.template
    
    def list_prompts(self, category: str = None, language: str = None) -> List[str]:
        """列出提示词"""
        prompts = []
        for key, prompt in self.prompts.items():
            if category and prompt.category != category:
                continue
            if language and prompt.language != language:
                continue
            prompts.append(key)
        return prompts
    
    def list_prompt_names(self, category: str = None, language: str = None) -> List[str]:
        """列出提示词名称（用于显示）"""
        prompt_names = []
        for key, prompt in self.prompts.items():
            if category and prompt.category != category:
                continue
            if language and prompt.language != language:
                continue
            prompt_names.append(prompt.name)
        return prompt_names
    
    def get_prompt_info(self, prompt_key: str) -> Dict[str, Any]:
        """获取提示词信息"""
        if prompt_key not in self.prompts:
            return {}
        
        prompt = self.prompts[prompt_key]
        return {
            "name": prompt.name,
            "description": prompt.description,
            "language": prompt.language,
            "difficulty": prompt.difficulty,
            "category": prompt.category,
            "variables": prompt.variables
        }
    
    def add_custom_prompt(self, name: str, description: str, template: str,
                         language: str, difficulty: str, category: str,
                         variables: List[str]) -> str:
        """添加自定义提示词"""
        prompt_key = f"custom_{name}"
        
        self.prompts[prompt_key] = PromptTemplate(
            name=name,
            description=description,
            template=template,
            language=language,
            difficulty=difficulty,
            category=category,
            variables=variables
        )
        
        self.logger.info(f"添加自定义提示词: {prompt_key}")
        return prompt_key
    
    def export_prompts(self, export_path: str, category: str = None):
        """导出提示词到文件"""
        export_data = {}
        
        for key, prompt in self.prompts.items():
            if category and prompt.category != category:
                continue
            
            export_data[key] = {
                "name": prompt.name,
                "description": prompt.description,
                "template": prompt.template,
                "language": prompt.language,
                "difficulty": prompt.difficulty,
                "category": prompt.category,
                "variables": prompt.variables
            }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"提示词已导出到: {export_path}")
    
    def import_prompts(self, import_path: str):
        """从文件导入提示词"""
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, prompt_data in data.items():
            self.prompts[key] = PromptTemplate(**prompt_data)
        
        self.logger.info(f"从 {import_path} 导入了 {len(data)} 个提示词")
    
    def get_prompt_categories(self) -> List[str]:
        """获取提示词分类列表"""
        categories = set()
        for prompt in self.prompts.values():
            categories.add(prompt.category)
        return list(categories)
    
    def get_prompt_languages(self) -> List[str]:
        """获取提示词支持的语言列表"""
        languages = set()
        for prompt in self.prompts.values():
            languages.add(prompt.language)
        return list(languages)
