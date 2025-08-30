#!/usr/bin/env python3
"""
修补index.html文件，添加卡片合并导航按钮
"""

import re

def patch_index_html():
    index_file = 'src/web/templates/index.html'
    
    # 读取原文件
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义要替换的内容
    old_nav = '''                    <!-- 历史记录按钮 -->
                    <button class="btn btn-outline-light btn-sm" id="history-btn" title="历史记录">
                        <i class="fas fa-history"></i>
                    </button>
                    
                    <!-- 设置按钮 -->
                    <button class="btn btn-outline-light btn-sm" id="settings-btn" title="设置">
                        <i class="fas fa-cog"></i>
                    </button>'''
    
    new_nav = '''                    <!-- 卡片合并按钮 -->
                    <a href="/card-merge" class="btn btn-outline-light btn-sm" title="卡片合并">
                        <i class="fas fa-layer-group me-2"></i>卡片合并
                    </a>
                    
                    <!-- 历史记录按钮 -->
                    <button class="btn btn-outline-light btn-sm" id="history-btn" title="历史记录">
                        <i class="fas fa-history"></i>
                    </button>
                    
                    <!-- 设置按钮 -->
                    <button class="btn btn-outline-light btn-sm" id="settings-btn" title="设置">
                        <i class="fas fa-cog"></i>
                    </button>'''
    
    # 执行替换
    if old_nav in content:
        content = content.replace(old_nav, new_nav)
        
        # 写回文件
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 成功添加卡片合并导航按钮到index.html")
        return True
    else:
        print("❌ 未找到要替换的导航栏内容")
        return False

if __name__ == '__main__':
    patch_index_html()