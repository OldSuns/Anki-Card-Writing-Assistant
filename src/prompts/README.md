# 提示词文件说明

本目录包含Anki写卡助手的提示词模板文件。

## 文件结构

每个提示词都以单独的markdown文件形式存储，文件名对应提示词的类型。

### 基础提示词

- `standard_qa.md` - 标准问答卡片提示词
- `cloze.md` - 填空卡片提示词

## 文件格式

每个markdown文件包含完整的提示词内容，使用以下变量占位符：

- `{card_count}` - 生成卡片数量
- `{language}` - 语言设置
- `{difficulty}` - 难度级别
- `{template_name}` - 模板名称
- `{content}` - 要处理的内容

## 添加新提示词

1. 创建新的markdown文件，文件名使用小写字母和下划线
2. 在文件中写入完整的提示词内容
3. 在 `src/prompts/base_prompts.py` 中的 `_load_prompts_from_files` 方法中添加配置
4. 更新 `config/prompts_config.json` 配置文件

## 示例

```markdown
你是一个专业的记忆卡片制作专家。请根据以下内容生成高质量的Anki记忆卡片。

要求：
1. 生成{card_count}张卡片
2. 每张卡片包含一个清晰的问题和详细的答案
3. 问题应该简洁明了，答案应该详细准确
4. 适合{language}语言学习者
5. 难度级别：{difficulty}
6. 使用{template_name}模板格式

内容：
{content}

请以JSON格式返回结果，格式如下：
{{
    "cards": [
        {{
            "front": "问题内容",
            "back": "答案内容",
            "deck": "牌组名称",
            "tags": ["标签1", "标签2"]
        }}
    ]
}}
```
