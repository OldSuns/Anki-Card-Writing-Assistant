"""
提示词管理器模块
负责管理不同类型的提示词模板，支持多种语言和难度级别
按模板（如 Quizify / Quizify Enhanced Cloze）从子目录读取与保存。
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
    """基础提示词管理器（支持按模板的子目录）"""
    
    def __init__(self, prompts_directory: str = "src/prompts"):
        self.prompts: Dict[str, PromptTemplate] = {}
        self.logger = logging.getLogger(__name__)
        self.prompts_directory = Path(prompts_directory)
        self._load_prompts_from_files()
        # 模板与文件夹名映射
        self.template_dir_map: Dict[str, str] = {
            "Quizify": "quizify",
            "Quizify Enhanced Cloze": "enhanced_cloze"
        }
        # 每个模板允许的提示词键
        self.allowed_prompts_for_template: Dict[str, List[str]] = {
            "Quizify": ["cloze", "multiple_choice"],
            "Quizify Enhanced Cloze": ["enhanced_cloze"]
        }
    
    def _load_prompts_from_files(self):
        """从markdown文件加载提示词模板"""
        # 确保提示词目录存在
        self.prompts_directory.mkdir(exist_ok=True)
        
        # 基础提示词配置（元数据）
        base_prompts_config = {
            "cloze": {
                "name": "填空卡片",
                "description": "生成填空类型的记忆卡片",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "cloze",
                "variables": ["card_count", "template_name", "content"]
            },
            "enhanced_cloze": {
                "name": "增强填空卡片",
                "description": "生成增强填空类型的记忆卡片",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "cloze",
                "variables": ["card_count", "template_name", "content"]
            },
            "multiple_choice": {
                "name": "选择题卡片",
                "description": "生成包含选项与解析的选择题卡片（支持多选）",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "standard",
                "variables": ["card_count", "template_name", "content"]
            }
        }
        
        # 先遍历目录（最多两层）加载模板
        loaded_keys = set()
        loaded_sources = 0
        try:
            for path in self.prompts_directory.rglob('*.md'):
                # 控制深度：最多两层子目录
                rel_parts = path.relative_to(self.prompts_directory).parts
                if len(rel_parts) > 3:  # 最多两层：目录/目录/文件
                    continue
                
                key = path.stem
                if key not in base_prompts_config:
                    continue
                
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        template_content = f.read().strip()
                    
                    cfg = base_prompts_config[key]
                    self.prompts[key] = PromptTemplate(
                        name=cfg["name"],
                        description=cfg["description"],
                        template=template_content,
                        language=cfg["language"],
                        difficulty=cfg["difficulty"],
                        category=cfg["category"],
                        variables=cfg["variables"]
                    )
                    loaded_keys.add(key)
                    loaded_sources += 1
                    self.logger.info(f"已加载提示词: {key} <- {path}")
                except Exception as e:
                    self.logger.error(f"加载提示词失败: {path} | {e}")
        except Exception as e:
            self.logger.error(f"遍历提示词目录失败: {e}")
        
        # 对未加载成功的键，尝试顶层兜底文件
        for prompt_key, cfg in base_prompts_config.items():
            if prompt_key in loaded_keys:
                continue
            
            prompt_file = self.prompts_directory / f"{prompt_key}.md"
            if not prompt_file.exists():
                self.logger.debug(f"未找到顶层提示词文件：{prompt_file}")
                continue
            
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    template_content = f.read().strip()
                
                self.prompts[prompt_key] = PromptTemplate(
                    name=cfg["name"],
                    description=cfg["description"],
                    template=template_content,
                    language=cfg["language"],
                    difficulty=cfg["difficulty"],
                    category=cfg["category"],
                    variables=cfg["variables"]
                )
                loaded_sources += 1
                self.logger.info(f"已加载提示词(顶层): {prompt_key}")
            except Exception as e:
                self.logger.error(f"加载顶层提示词 {prompt_key} 失败: {e}")
        
        self.logger.info(f"总共加载了 {loaded_sources} 个提示词模板来源")
    
    def _get_template_subdir(self, template_name: Optional[str]) -> Optional[Path]:
        if not template_name:
            return None
        folder = self.template_dir_map.get(template_name)
        if not folder:
            return None
        return self.prompts_directory / folder

    def get_prompt(self, prompt_type: str, template_name: Optional[str] = None, language: str = "zh-CN",
                  difficulty: str = "medium") -> str:
        """获取提示词，优先读取用户文件，按模板子目录优先，其次全局。"""
        # 按优先级尝试读取提示词
        read_attempts = [
            # 1) 模板子目录中的用户覆盖
            lambda: self._read_prompt_file(self._get_template_subdir(template_name) / f"{prompt_type}_user.md",
                                          f"模板目录用户文件: {prompt_type}_user.md"),
            # 2) 模板子目录中的原始文件
            lambda: self._read_prompt_file(self._get_template_subdir(template_name) / f"{prompt_type}.md",
                                          f"模板目录原始文件: {prompt_type}.md"),
            # 3) 全局用户覆盖
            lambda: self._read_prompt_file(self.prompts_directory / f"{prompt_type}_user.md",
                                          f"全局用户文件: {prompt_type}_user.md"),
        ]
        
        # 尝试所有读取方式
        for attempt in read_attempts:
            content = attempt()
            if content is not None:
                return content
        
        # 4) 全局默认（预加载）
        if prompt_type in self.prompts:
            return self.prompts[prompt_type].template
        
        # 5) 如果都不存在，抛出错误
        raise ValueError(f"未找到提示词类型: {prompt_type}")
    
    def _read_prompt_file(self, file_path: Path, description: str) -> Optional[str]:
        """读取提示词文件"""
        if file_path and file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                self.logger.info(f"从{description}读取提示词")
                return content
            except Exception as e:
                self.logger.warning(f"读取{description}失败: {e}")
        return None
    
    def list_prompts(self, category: str = None, language: str = None, template_name: Optional[str] = None) -> List[str]:
        """列出提示词键；若提供 template_name，则仅返回该模板允许的提示词。"""
        if template_name and template_name in self.allowed_prompts_for_template:
            return self.allowed_prompts_for_template[template_name][:]
        
        prompts = []
        for key, prompt in self.prompts.items():
            if category and prompt.category != category:
                continue
            if language and prompt.language != language:
                continue
            prompts.append(key)
        return prompts
    
    def list_prompt_names(self, category: str = None, language: str = None, template_name: Optional[str] = None) -> List[str]:
        """列出提示词名称（用于显示）；支持按模板过滤。"""
        keys = self.list_prompts(category=category, language=language, template_name=template_name)
        names: List[str] = []
        
        # 基础提示词配置（元数据）用于名称映射
        base_prompts_config = {
            "cloze": {
                "name": "填空卡片",
                "description": "生成填空类型的记忆卡片",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "cloze",
                "variables": ["card_count", "template_name", "content"]
            },
            "enhanced_cloze": {
                "name": "增强填空卡片",
                "description": "生成增强填空类型的记忆卡片",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "cloze",
                "variables": ["card_count", "template_name", "content"]
            },
            "multiple_choice": {
                "name": "选择题卡片",
                "description": "生成包含选项与解析的选择题卡片（支持多选）",
                "language": "zh-CN",
                "difficulty": "medium",
                "category": "standard",
                "variables": ["card_count", "template_name", "content"]
            }
        }
        
        for key in keys:
            if key in self.prompts:
                names.append(self.prompts[key].name)
            elif key in base_prompts_config:
                # 使用基础配置中的名称
                names.append(base_prompts_config[key]["name"])
            else:
                # 若未在全局预加载（极少），回退显示键名
                names.append(key)
        return names
    
    def get_prompt_info(self, prompt_key: str) -> Dict[str, Any]:
        """获取提示词信息（全局默认元数据）"""
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
        """添加自定义提示词（全局级别）"""
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
        """导出全局提示词到文件"""
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
        """从文件导入全局提示词"""
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, prompt_data in data.items():
            self.prompts[key] = PromptTemplate(**prompt_data)
        
        self.logger.info(f"从 {import_path} 导入了 {len(data)} 个提示词")
    
    def get_prompt_categories(self) -> List[str]:
        """获取提示词分类列表（全局元数据）"""
        categories = set()
        for prompt in self.prompts.values():
            categories.add(prompt.category)
        return list(categories)
    
    def get_prompt_languages(self) -> List[str]:
        """获取提示词支持的语言列表（全局元数据）"""
        languages = set()
        for prompt in self.prompts.values():
            languages.add(prompt.language)
        return list(languages)
