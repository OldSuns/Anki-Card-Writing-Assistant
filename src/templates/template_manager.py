"""
模板管理器模块
负责管理Anki卡片模板，包括Quizify和增强填空模板
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import re

@dataclass
class TemplateField:
    """模板字段定义"""
    name: str
    required: bool = True
    default_value: str = ""
    description: str = ""

@dataclass
class AnkiTemplate:
    """Anki模板定义"""
    name: str
    description: str
    fields: List[TemplateField]
    front_template: str
    back_template: str
    css: str
    is_cloze: bool = False
    cloze_fields: List[str] = None
    
    def is_cloze_template(self) -> bool:
        """判断是否为填空模板"""
        return self.is_cloze or "{{cloze:" in self.front_template

class TemplateManager:
    """模板管理器"""
    
    def __init__(self, template_dir: str = "Card Template"):
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, AnkiTemplate] = {}
        self.logger = logging.getLogger(__name__)
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板"""
        try:
            # 加载Quizify模板
            self._load_quizify_templates()
            
            # 加载增强填空模板
            self._load_enhanced_cloze_templates()
            
            self.logger.info(f"成功加载 {len(self.templates)} 个模板")
        except Exception as e:
            self.logger.error(f"加载模板失败: {e}")
            raise
    
    def _load_quizify_templates(self):
        """加载Quizify模板"""
        quizify_dir = self.template_dir / "Quizify"
        if not quizify_dir.exists():
            self.logger.warning(f"Quizify模板目录不存在: {quizify_dir}")
            return
        
        # 读取模板文件
        css_content = self._read_template_file(quizify_dir / "quizify.css")
        front_content = self._read_template_file(quizify_dir / "front1.html")
        back_content = self._read_template_file(quizify_dir / "back1.html")
        
        # 创建Quizify模板
        quizify_template = AnkiTemplate(
            name="Quizify",
            description="Quizify风格的问答卡片模板，支持多种交互功能",
            fields=[
                TemplateField("Front", True, "", "卡片正面内容"),
                TemplateField("Back", False, "", "卡片背面内容"),
                TemplateField("Deck", True, "", "牌组名称"),
                TemplateField("Tags", False, "", "标签")
            ],
            front_template=front_content,
            back_template=back_content,
            css=css_content,
            is_cloze=False
        )
        
        self.templates["Quizify"] = quizify_template
    
    def _load_enhanced_cloze_templates(self):
        """加载增强填空模板"""
        cloze_dir = self.template_dir / "Enhanced Cloze"
        if not cloze_dir.exists():
            self.logger.warning(f"增强填空模板目录不存在: {cloze_dir}")
            return
        
        # 读取模板文件
        css_content = self._read_template_file(cloze_dir / "quizify-with-enhanced-cloze.css")
        front_content = self._read_template_file(cloze_dir / "Front.html")
        back_content = self._read_template_file(cloze_dir / "Back.html")
        
        # 创建增强填空模板
        enhanced_cloze_template = AnkiTemplate(
            name="Enhanced Cloze",
            description="增强填空模板，支持提示、动画等高级功能",
            fields=[
                TemplateField("Content", True, "", "包含填空的内容"),
                TemplateField("Back Extra", False, "", "背面额外内容"),
                TemplateField("Deck", True, "", "牌组名称"),
                TemplateField("Tags", False, "", "标签"),
                TemplateField("Cloze99", False, "", "AnkiDroid兼容字段")
            ],
            front_template=front_content,
            back_template=back_content,
            css=css_content,
            is_cloze=True,
            cloze_fields=["Content"]
        )
        
        self.templates["Enhanced Cloze"] = enhanced_cloze_template
    
    def get_template(self, name: str) -> Optional[AnkiTemplate]:
        """获取模板"""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """列出所有模板名称"""
        return list(self.templates.keys())
    
    def get_template_info(self, name: str) -> Dict[str, Any]:
        """获取模板信息"""
        template = self.get_template(name)
        if not template:
            return {}
        
        return {
            "name": template.name,
            "description": template.description,
            "fields": [{"name": f.name, "required": f.required, "description": f.description} 
                      for f in template.fields],
            "is_cloze": template.is_cloze,
            "cloze_fields": template.cloze_fields
        }
    
    def validate_card_data(self, template_name: str, card_data: Dict[str, str]) -> bool:
        """验证卡片数据是否符合模板要求"""
        template = self.get_template(template_name)
        if not template:
            return False
        
        # 检查必需字段
        for field in template.fields:
            if field.required and not card_data.get(field.name):
                self.logger.warning(f"缺少必需字段: {field.name}")
                return False
        
        return True
    
    def get_template_fields(self, template_name: str) -> List[TemplateField]:
        """获取模板字段列表"""
        template = self.get_template(template_name)
        if not template:
            return []
        return template.fields
    
    def create_custom_template(self, name: str, description: str, 
                             fields: List[TemplateField], front_template: str,
                             back_template: str, css: str, is_cloze: bool = False) -> AnkiTemplate:
        """创建自定义模板"""
        template = AnkiTemplate(
            name=name,
            description=description,
            fields=fields,
            front_template=front_template,
            back_template=back_template,
            css=css,
            is_cloze=is_cloze
        )
        
        self.templates[name] = template
        self.logger.info(f"创建自定义模板: {name}")
        return template
    
    def export_template(self, template_name: str, export_path: str):
        """导出模板到文件"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")
        
        export_data = {
            "name": template.name,
            "description": template.description,
            "fields": [{"name": f.name, "required": f.required, "default_value": f.default_value, 
                       "description": f.description} for f in template.fields],
            "front_template": template.front_template,
            "back_template": template.back_template,
            "css": template.css,
            "is_cloze": template.is_cloze,
            "cloze_fields": template.cloze_fields
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"模板已导出到: {export_path}")
    
    def import_template(self, import_path: str) -> AnkiTemplate:
        """从文件导入模板"""
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        fields = [TemplateField(**field_data) for field_data in data["fields"]]
        
        template = AnkiTemplate(
            name=data["name"],
            description=data["description"],
            fields=fields,
            front_template=data["front_template"],
            back_template=data["back_template"],
            css=data["css"],
            is_cloze=data.get("is_cloze", False),
            cloze_fields=data.get("cloze_fields")
        )
        
        self.templates[template.name] = template
        self.logger.info(f"导入模板: {template.name}")
        return template
    
    def get_template_preview(self, template_name: str, sample_data: Dict[str, str]) -> Dict[str, str]:
        """获取模板预览"""
        template = self.get_template(template_name)
        if not template:
            return {}
        
        # 替换模板中的字段
        front_preview = template.front_template
        back_preview = template.back_template
        
        for field in template.fields:
            value = sample_data.get(field.name, field.default_value)
            field_placeholder = f"{{{{{field.name}}}}}"
            front_preview = front_preview.replace(field_placeholder, value)
            back_preview = back_preview.replace(field_placeholder, value)
        
        return {
            "front": front_preview,
            "back": back_preview,
            "css": template.css
        }
    
    def validate_cloze_content(self, content: str) -> bool:
        """验证填空内容格式"""
        # 检查填空格式是否正确
        cloze_pattern = r'\{\{c\d+::[^}]+\}\}'
        matches = re.findall(cloze_pattern, content)
        
        if not matches:
            return False
        
        # 检查填空ID是否连续
        cloze_ids = []
        for match in matches:
            id_match = re.search(r'c(\d+)', match)
            if id_match:
                cloze_ids.append(int(id_match.group(1)))
        
        # 检查ID是否从1开始连续
        if cloze_ids:
            expected_ids = list(range(1, max(cloze_ids) + 1))
            return sorted(cloze_ids) == expected_ids
        
        return False
    
    def _read_template_file(self, file_path: Path) -> str:
        """读取模板文件内容"""
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
