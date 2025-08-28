/**
 * Anki写卡助手Web界面JavaScript - 现代化重构版
 * 支持拖拽上传、主题切换、进度显示、吐司通知等现代化功能
 */

class AnkiCardAssistant {
    constructor() {
        this.socket = null;
        this.currentCards = [];
        this.currentCardIndex = 0;
        this.isGenerating = false;

        
        // DOM元素缓存
        this.elements = {};
        this.modals = {};
        this.toasts = {};
        
        this.init();
    }

    async testApiConnection() {
        try {
            const payload = { prompt: 'Hi,Who are you?' };
            const response = await fetch('/api/test-llm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            // 状态显示元素
            const statusWrap = document.getElementById('api-test-status');
            const statusDot = document.getElementById('api-test-status-dot');
            const statusText = document.getElementById('api-test-status-text');

            if (statusWrap) statusWrap.classList.remove('d-none');
            if (statusDot) statusDot.className = `fas fa-circle me-2 ${response.ok ? 'text-success' : 'text-danger'}`;
            if (statusText) statusText.textContent = `HTTP ${response.status}`;

            const result = await response.json();
            if (result.success) {
                if (this.elements.apiTestResult) this.elements.apiTestResult.textContent = result.data.reply || '';
                this.modals.apiTest?.show();
            } else {
                if (this.elements.apiTestResult) this.elements.apiTestResult.textContent = `错误: ${result.error || 'API测试失败'}`;
                this.modals.apiTest?.show();
            }
        } catch (error) {
            console.error('API测试失败:', error);
            const statusWrap = document.getElementById('api-test-status');
            const statusDot = document.getElementById('api-test-status-dot');
            const statusText = document.getElementById('api-test-status-text');
            if (statusWrap) statusWrap.classList.remove('d-none');
            if (statusDot) statusDot.className = 'fas fa-circle me-2 text-danger';
            if (statusText) statusText.textContent = '请求失败';
            if (this.elements.apiTestResult) this.elements.apiTestResult.textContent = 'API测试过程中发生错误';
            this.modals.apiTest?.show();
        }
    }

    init() {
        this.cacheElements();
        this.initSocket();
        this.initEventListeners();
        this.loadInitialData();
        
        console.log('Anki Card Assistant initialized successfully');
    }

    cacheElements() {
        // 表单元素
        this.elements.form = document.getElementById('generation-form');
        this.elements.contentInput = document.getElementById('content-input');
        
        // 设置选择器
        this.elements.templateSelect = document.getElementById('template-select');
        this.elements.promptSelect = document.getElementById('prompt-select');
        this.elements.difficultySelect = document.getElementById('difficulty-select');
        this.elements.cardCount = document.getElementById('card-count');
        
        // 提示词编辑器
        this.elements.promptEditorCard = document.getElementById('prompt-editor-card');
        this.elements.promptEditor = document.getElementById('prompt-editor');
        this.elements.savePromptBtn = document.getElementById('save-prompt-btn');
        this.elements.resetPromptBtn = document.getElementById('reset-prompt-btn');
        this.elements.promptInfo = document.getElementById('prompt-info');
        this.elements.promptInfoText = document.getElementById('prompt-info-text');
        
        // 按钮
        this.elements.generateBtn = document.getElementById('generate-btn');
        this.elements.btnContent = this.elements.generateBtn?.querySelector('.btn-content');
        this.elements.btnLoading = this.elements.generateBtn?.querySelector('.btn-loading');
        this.elements.prevCard = document.getElementById('prev-card');
        this.elements.nextCard = document.getElementById('next-card');
        this.elements.exportApkgBtn = document.getElementById('export-apkg-btn');
        this.elements.confirmApkgExport = document.getElementById('confirm-apkg-export');

        
        // 显示区域
        this.elements.welcomeCard = document.getElementById('welcome-card');
        this.elements.statusAlert = document.getElementById('status-alert');
        this.elements.statusMessage = document.getElementById('status-message');
        this.elements.summaryCard = document.getElementById('summary-card');
        this.elements.summaryContent = document.getElementById('summary-content');
        this.elements.cardsCard = document.getElementById('cards-card');
        this.elements.cardPreview = document.getElementById('card-preview');
        this.elements.cardCounter = document.getElementById('card-counter');
        this.elements.exportCard = document.getElementById('export-card');
        this.elements.exportLinks = document.getElementById('export-links');
        
        // 进度显示
        this.elements.generationProgress = document.getElementById('generation-progress');
        this.elements.progressBar = document.getElementById('progress-bar');
        this.elements.progressText = document.getElementById('progress-text');
        this.elements.progressPercent = document.getElementById('progress-percent');
        
        // 连接状态
        this.elements.connectionStatus = document.getElementById('connection-status');
        
        // 设置相关元素
        this.elements.settingsBtn = document.getElementById('settings-btn');
        this.elements.settingsModal = new bootstrap.Modal(document.getElementById('settings-modal'));
        this.elements.settingsForm = document.getElementById('settings-form');
        this.elements.saveSettingsBtn = document.getElementById('save-settings-btn');
        
        // 设置表单元素
        this.elements.apiKey = document.getElementById('api-key');
        this.elements.baseUrl = document.getElementById('base-url');
        this.elements.modelName = document.getElementById('model-name');
        this.elements.temperature = document.getElementById('temperature');
        this.elements.maxTokens = document.getElementById('max-tokens');
        this.elements.timeout = document.getElementById('timeout');
        this.elements.testApiBtn = document.getElementById('test-api-btn');
        this.modals.apiTest = new bootstrap.Modal(document.getElementById('api-test-modal'));
        this.elements.apiTestResult = document.getElementById('api-test-result');
        
        // 模态框
        this.modals.loading = new bootstrap.Modal(document.getElementById('loading-modal'));
        this.modals.apkgExport = new bootstrap.Modal(document.getElementById('apkg-export-modal'));
        
        // 吐司通知
        this.toasts.error = new bootstrap.Toast(document.getElementById('error-toast'));
        this.toasts.success = new bootstrap.Toast(document.getElementById('success-toast'));
    }

    initSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            this.showToast('success', '已连接到服务器');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            this.showToast('error', '与服务器的连接已断开');
        });

        this.socket.on('status', (data) => {
            this.showStatus(data.message, 'info');
        });

        this.socket.on('generation_start', (data) => {
            this.showStatus(data.message, 'info');
            this.showLoadingModal();
            this.updateProgress(10, '开始分析内容...');
        });

        this.socket.on('generation_progress', (data) => {
            this.updateLoadingMessage(data.message);
            // 模拟进度更新
            const progress = Math.min(90, Math.random() * 50 + 40);
            this.updateProgress(progress, data.message);
        });

        this.socket.on('generation_complete', (data) => {
            this.hideLoadingModal();
            this.updateProgress(100, '生成完成！');
            this.showStatus('卡片生成完成！', 'success');
            this.showToast('success', `成功生成 ${data.cards?.length || 0} 张卡片`);
            this.displayResults(data);
            this.hideWelcomeCard();
        });

        this.socket.on('generation_error', (data) => {
            this.hideLoadingModal();
            this.showStatus(data.error, 'danger');
            this.showToast('error', data.error);
            this.resetGenerateButton();
        });
    }

    initEventListeners() {
        // 表单提交
        this.elements.form?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.generateCards();
        });



        // 卡片导航
        this.elements.prevCard?.addEventListener('click', () => {
            this.showPreviousCard();
        });

        this.elements.nextCard?.addEventListener('click', () => {
            this.showNextCard();
        });



        // 提示词编辑器事件
        this.elements.promptSelect?.addEventListener('change', () => {
            this.loadPromptContent();
        });

        this.elements.savePromptBtn?.addEventListener('click', () => {
            this.savePromptContent();
        });

        this.elements.resetPromptBtn?.addEventListener('click', () => {
            this.resetPromptContent();
        });

        // 设置相关事件
        this.elements.settingsBtn?.addEventListener('click', () => {
            this.showSettingsModal();
        });

        this.elements.saveSettingsBtn?.addEventListener('click', () => {
            this.saveSettings();
        });

        // API测试：先保存设置再进行测试
        this.elements.testApiBtn?.addEventListener('click', async () => {
            if (this.elements.testApiBtn) this.elements.testApiBtn.disabled = true;
            try {
                const saved = await this.saveSettingsSilently();
                if (!saved) {
                    this.showToast('error', '保存设置失败，请检查后重试');
                    return;
                }
                await this.testApiConnection();
            } finally {
                if (this.elements.testApiBtn) this.elements.testApiBtn.disabled = false;
            }
        });

        // APKG导出
        this.elements.exportApkgBtn?.addEventListener('click', () => {
            this.showApkgExportModal();
        });

        this.elements.confirmApkgExport?.addEventListener('click', () => {
            this.exportApkg();
        });

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });

        // 窗口调整大小
        window.addEventListener('resize', this.debounce(() => {
            this.handleResize();
        }, 300));
    }





    async loadInitialData() {
        try {
            this.showStatus('正在加载配置...', 'info');
            
            // 并行加载所有数据
            const [templatesResponse, promptsResponse, promptNamesResponse, configResponse, settingsResponse] = await Promise.all([
                fetch('/api/templates'),
                fetch('/api/prompts'),
                fetch('/api/prompt-names'),
                fetch('/api/config'),
                fetch('/api/settings')
            ]);

            // 处理模板数据
            if (templatesResponse.ok) {
                const templatesData = await templatesResponse.json();
                if (templatesData.success) {
                    this.populateSelect(this.elements.templateSelect, templatesData.data);
                }
            }

            // 处理提示词数据
            if (promptsResponse.ok && promptNamesResponse.ok) {
                const promptsData = await promptsResponse.json();
                const promptNamesData = await promptNamesResponse.json();
                if (promptsData.success && promptNamesData.success) {
                    // 创建提示词名称到键的映射
                    this.promptNameToKey = {};
                    promptsData.data.forEach((key, index) => {
                        if (promptNamesData.data[index]) {
                            this.promptNameToKey[promptNamesData.data[index]] = key;
                        }
                    });
                    this.populateSelect(this.elements.promptSelect, promptNamesData.data);
                }
            }

            // 处理配置数据（生成表单默认值依旧保留）
            if (configResponse.ok) {
                const configData = await configResponse.json();
                if (configData.success) {
                    this.setDefaultValues(configData.data);
                }
            }

            // 处理设置数据
            if (settingsResponse.ok) {
                const settingsData = await settingsResponse.json();
                if (settingsData.success) {
                    this.loadSettings(settingsData.data);
                }
            }

            this.hideStatus();
            
        } catch (error) {
            console.error('加载初始数据失败:', error);
            this.showStatus('加载配置失败', 'warning');
            this.showToast('error', '配置加载失败，请刷新页面重试');
        }
    }

    populateSelect(selectElement, options) {
        if (!selectElement || !Array.isArray(options)) return;
        
        selectElement.innerHTML = '';
        
        // 添加默认选项
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '请选择...';
        selectElement.appendChild(defaultOption);
        
        // 添加选项
        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            optionElement.textContent = option;
            selectElement.appendChild(optionElement);
        });

        // 添加动画效果
        selectElement.classList.add('fade-in');
    }

    setDefaultValues(config) {
        if (!config) return;
        
        if (config.generation) {
            const gen = config.generation;
            
            if (this.elements.difficultySelect) {
                this.elements.difficultySelect.value = gen.default_difficulty || 'medium';
            }
            
            if (this.elements.cardCount) {
                this.elements.cardCount.value = gen.default_card_count || 5;
            }
            
            // 设置默认模板
            if (gen.default_template && this.elements.templateSelect) {
                this.elements.templateSelect.value = gen.default_template;
            }
            
            // 不为提示词类型设置默认值，保持“请选择...”
            // if (gen.default_prompt_type && this.elements.promptSelect) {
            //     // 原行为：尝试根据映射/键设置默认显示值
            // }
        }
    }

    generateCards() {
        if (this.isGenerating) {
            this.showToast('warning', '正在生成中，请等待...');
            return;
        }

        const content = this.elements.contentInput?.value.trim();
        
        if (!content) {
            this.showStatus('请输入内容', 'warning');
            this.showToast('warning', '请输入内容');
            return;
        }

        // 验证其他必填字段
        if (!this.elements.templateSelect?.value) {
            this.showToast('warning', '请选择卡片模板');
            return;
        }

        if (!this.elements.promptSelect?.value) {
            this.showToast('warning', '请选择提示词类型');
            return;
        }

        this.isGenerating = true;
        this.showGenerateButton(true);
        this.showProgress(true);

        const formData = {
            content: content,
            template: this.elements.templateSelect.value,
            prompt_type: this.promptNameToKey[this.elements.promptSelect.value] || this.elements.promptSelect.value,
            language: 'zh-CN',
            difficulty: this.elements.difficultySelect.value,
            card_count: parseInt(this.elements.cardCount.value),
            export_formats: this.getSelectedExportFormats()
        };

        this.socket.emit('generate_cards', formData);
    }



    getSelectedExportFormats() {
        const formats = [];
        const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(checkbox => {
            formats.push(checkbox.value);
        });
        return formats.length > 0 ? formats : ['json', 'apkg']; // 默认至少选择JSON和APKG
    }

    displayResults(data) {
        this.currentCards = data.cards || [];
        this.currentCardIndex = 0;

        // 隐藏欢迎卡片
        this.hideWelcomeCard();

        // 显示摘要
        if (data.summary) {
            this.displaySummary(data.summary);
        }

        // 显示卡片预览
        if (this.currentCards.length > 0) {
            this.displayCardPreview();
        }

        // 显示导出结果
        if (data.export_paths) {
            this.displayExportResults(data.export_paths);
        }

        this.resetGenerateButton();
    }

    displaySummary(summary) {
        if (!this.elements.summaryContent || !summary) return;

        this.elements.summaryContent.innerHTML = `
            <div class="col-md-4">
                <div class="summary-item bounce-in">
                    <div class="summary-number">${summary.total_cards || 0}</div>
                    <div class="summary-label">总卡片数</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="summary-item bounce-in" style="animation-delay: 0.1s;">
                    <div class="summary-number">${Object.keys(summary.deck_stats || {}).length}</div>
                    <div class="summary-label">牌组数量</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="summary-item bounce-in" style="animation-delay: 0.2s;">
                    <div class="summary-number">${Object.keys(summary.model_stats || {}).length}</div>
                    <div class="summary-label">模型数量</div>
                </div>
            </div>
        `;

        if (this.elements.summaryCard) {
            this.elements.summaryCard.classList.remove('d-none');
            this.elements.summaryCard.classList.add('fade-in');
        }
    }

    displayCardPreview() {
        if (this.elements.cardsCard) {
            this.elements.cardsCard.classList.remove('d-none');
            this.elements.cardsCard.classList.add('fade-in');
        }
        
        this.updateCardDisplay();
    }

    updateCardDisplay() {
        if (this.currentCards.length === 0 || !this.elements.cardPreview) return;

        const card = this.currentCards[this.currentCardIndex];
        
        if (this.elements.cardCounter) {
            this.elements.cardCounter.textContent = `${this.currentCardIndex + 1} / ${this.currentCards.length}`;
        }

        this.elements.cardPreview.innerHTML = `
            <div class="card-content">
                <div class="card-front">
                    <h6><i class="fas fa-eye me-2"></i>正面</h6>
                    <div>${this.formatCardContent(card.front || '')}</div>
                </div>
                <div class="card-back">
                    <h6><i class="fas fa-eye-slash me-2"></i>背面</h6>
                    <div>${this.formatCardContent(card.back || '')}</div>
                </div>
                ${card.tags && card.tags.length > 0 ? `
                <div class="card-tags">
                    <h6><i class="fas fa-tags me-2"></i>标签</h6>
                    <div>
                        ${card.tags.map(tag => `<span class="card-tag">${tag}</span>`).join('')}
                    </div>
                </div>` : ''}
                ${card.deck ? `
                <div class="mt-2">
                    <small class="text-muted">
                        <i class="fas fa-layer-group me-1"></i>牌组: ${card.deck}
                    </small>
                </div>` : ''}
            </div>
        `;

        // 更新导航按钮状态
        if (this.elements.prevCard) {
            this.elements.prevCard.disabled = this.currentCardIndex === 0;
        }
        if (this.elements.nextCard) {
            this.elements.nextCard.disabled = this.currentCardIndex === this.currentCards.length - 1;
        }
    }

    formatCardContent(content) {
        if (!content) return '';
        
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    showPreviousCard() {
        if (this.currentCardIndex > 0) {
            this.currentCardIndex--;
            this.updateCardDisplay();
            
            // 添加动画效果
            this.elements.cardPreview?.classList.add('slide-in');
            setTimeout(() => {
                this.elements.cardPreview?.classList.remove('slide-in');
            }, 300);
        }
    }

    showNextCard() {
        if (this.currentCardIndex < this.currentCards.length - 1) {
            this.currentCardIndex++;
            this.updateCardDisplay();
            
            // 添加动画效果
            this.elements.cardPreview?.classList.add('slide-in');
            setTimeout(() => {
                this.elements.cardPreview?.classList.remove('slide-in');
            }, 300);
        }
    }

    displayExportResults(exportPaths) {
        if (!this.elements.exportLinks || !exportPaths) return;

        let linksHtml = '';
        for (const [format, path] of Object.entries(exportPaths)) {
            const icon = this.getFormatIcon(format);
            
            // 从文件路径中提取文件名
            const fileName = path.split('/').pop() || path.split('\\').pop() || `${format}_export`;
            
            // 对于apkg格式，使用特殊的下载处理
            if (format.toLowerCase() === 'apkg') {
                linksHtml += `
                    <div class="col-md-6 col-lg-4 mb-2">
                        <button class="export-link w-100 btn btn-outline-success" 
                                onclick="app.downloadApkgFile('${fileName}')" 
                                title="下载APKG格式">
                            <i class="${icon} me-2"></i>
                            <span>APKG</span>
                            <i class="fas fa-download ms-auto"></i>
                        </button>
                    </div>
                `;
            } else {
                linksHtml += `
                    <div class="col-md-6 col-lg-4 mb-2">
                        <a href="/download/${fileName}" class="export-link w-100" target="_blank" title="下载${format.toUpperCase()}格式">
                            <i class="${icon} me-2"></i>
                            <span>${format.toUpperCase()}</span>
                            <i class="fas fa-download ms-auto"></i>
                        </a>
                    </div>
                `;
            }
        }

        this.elements.exportLinks.innerHTML = linksHtml;
        
        if (this.elements.exportCard) {
            this.elements.exportCard.classList.remove('d-none');
            this.elements.exportCard.classList.add('fade-in');
        }
    }

    getFormatIcon(format) {
        const icons = {
            'json': 'fas fa-code',
            'csv': 'fas fa-table',
            'html': 'fas fa-code',
            'txt': 'fas fa-file-alt',
            'apkg': 'fas fa-file-export'
        };
        return icons[format.toLowerCase()] || 'fas fa-file';
    }



    // 进度显示
    showProgress(show) {
        if (this.elements.generationProgress) {
            this.elements.generationProgress.classList.toggle('d-none', !show);
        }
    }

    updateProgress(percent, text) {
        if (this.elements.progressBar) {
            this.elements.progressBar.style.width = `${percent}%`;
        }
        
        if (this.elements.progressText) {
            this.elements.progressText.textContent = text;
        }
        
        if (this.elements.progressPercent) {
            this.elements.progressPercent.textContent = `${Math.round(percent)}%`;
        }
    }

    // 按钮状态管理
    showGenerateButton(loading) {
        if (!this.elements.generateBtn) return;
        
        this.elements.generateBtn.disabled = loading;
        
        if (this.elements.btnContent) {
            this.elements.btnContent.classList.toggle('d-none', loading);
        }
        
        if (this.elements.btnLoading) {
            this.elements.btnLoading.classList.toggle('d-none', !loading);
        }
    }

    resetGenerateButton() {
        this.isGenerating = false;
        this.showGenerateButton(false);
        this.showProgress(false);
    }

    // 状态消息显示
    showStatus(message, type = 'info') {
        if (!this.elements.statusAlert || !this.elements.statusMessage) return;
        
        this.elements.statusAlert.className = `alert alert-${type}`;
        this.elements.statusMessage.textContent = message;
        
        this.elements.statusAlert.classList.remove('d-none');
        this.elements.statusAlert.classList.add('fade-in');
        
        // 自动隐藏（除了错误消息）
        if (type !== 'danger') {
            setTimeout(() => {
                this.hideStatus();
            }, 3000);
        }
    }

    hideStatus() {
        if (this.elements.statusAlert) {
            this.elements.statusAlert.classList.add('d-none');
            this.elements.statusAlert.classList.remove('fade-in');
        }
    }

    hideWelcomeCard() {
        if (this.elements.welcomeCard) {
            this.elements.welcomeCard.style.display = 'none';
        }
    }

    // 连接状态更新
    updateConnectionStatus(connected) {
        if (!this.elements.connectionStatus) return;
        
        const icon = this.elements.connectionStatus.querySelector('i');
        const span = this.elements.connectionStatus.querySelector('span');
        
        if (connected) {
            if (icon) icon.className = 'fas fa-circle text-success me-2';
            if (span) span.textContent = '已连接';
        } else {
            if (icon) icon.className = 'fas fa-circle text-danger me-2';
            if (span) span.textContent = '连接断开';
        }
    }

    // 模态框控制
    showLoadingModal() {
        this.modals.loading?.show();
    }

    hideLoadingModal() {
        this.modals.loading?.hide();
    }

    updateLoadingMessage(message) {
        const loadingMessage = document.getElementById('loading-message');
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
    }

    showApkgExportModal() {
        if (this.currentCards.length === 0) {
            this.showToast('warning', '请先生成卡片');
            return;
        }
        this.modals.apkgExport?.show();
    }

    async exportApkg() {
        const deckName = document.getElementById('deck-name')?.value || 'AI生成卡片';
        const filename = document.getElementById('filename')?.value || null;
        
        try {
            const response = await fetch('/api/export-apkg', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cards: this.currentCards,
                    deck_name: deckName,
                    filename: filename
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showToast('success', `APKG文件导出成功: ${result.data.filename}`);
                this.modals.apkgExport?.hide();
            } else {
                this.showToast('error', result.error || 'APKG导出失败');
            }
        } catch (error) {
            console.error('APKG导出错误:', error);
            this.showToast('error', 'APKG导出过程中发生错误');
        }
    }

    async downloadApkgFile(fileName) {
        try {
            // 使用新的下载路由
            const link = document.createElement('a');
            link.href = `/download/${fileName}`;
            link.download = fileName;
            link.style.display = 'none';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showToast('success', `APKG文件下载开始: ${fileName}`);
        } catch (error) {
            console.error('APKG文件下载错误:', error);
            this.showToast('error', 'APKG文件下载失败');
        }
    }

    // 吐司通知
    showToast(type, message) {
        const toastElement = type === 'error' ? 
            document.getElementById('error-toast') : 
            document.getElementById('success-toast');
        
        const toastBody = type === 'error' ?
            document.getElementById('error-toast-body') :
            document.getElementById('success-toast-body');
        
        if (toastBody) {
            toastBody.textContent = message;
        }
        
        const toast = type === 'error' ? this.toasts.error : this.toasts.success;
        toast?.show();
    }

    // 键盘快捷键
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + Enter: 生成卡片
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            this.generateCards();
        }
        
        // 左右箭头: 切换卡片
        if (this.currentCards.length > 0) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.showPreviousCard();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                this.showNextCard();
            }
        }
        
        // ESC: 隐藏模态框
        if (e.key === 'Escape') {
            this.modals.loading?.hide();
            this.modals.apkgExport?.hide();
        }
    }

    // 窗口大小调整处理
    handleResize() {
        // 响应式调整逻辑
        const width = window.innerWidth;
        
        // 移动端优化
        if (width < 768) {
            // 移动端特定调整
        }
    }



    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // 提示词编辑器功能
    async loadPromptContent() {
        const selectedPrompt = this.elements.promptSelect?.value;
        if (!selectedPrompt) {
            this.clearPromptEditor();
            return;
        }

        try {
            // 获取提示词类型键
            const promptType = this.promptNameToKey[selectedPrompt] || selectedPrompt;
            
            const response = await fetch(`/api/prompt-content?prompt_type=${encodeURIComponent(promptType)}`);
            const result = await response.json();
            
            if (result.success) {
                this.elements.promptEditor.value = result.data.content;
                this.showPromptInfo(`已加载提示词: ${selectedPrompt}`);
                this.elements.promptEditorCard.classList.remove('d-none');
            } else {
                this.showToast('error', result.error || '加载提示词失败');
            }
        } catch (error) {
            console.error('加载提示词内容失败:', error);
            this.showToast('error', '加载提示词内容失败');
        }
    }

    async savePromptContent() {
        const selectedPrompt = this.elements.promptSelect?.value;
        const content = this.elements.promptEditor?.value;
        
        if (!selectedPrompt) {
            this.showToast('warning', '请先选择提示词类型');
            return;
        }
        
        if (!content || !content.trim()) {
            this.showToast('warning', '提示词内容不能为空');
            return;
        }

        try {
            // 获取提示词类型键
            const promptType = this.promptNameToKey[selectedPrompt] || selectedPrompt;
            
            const response = await fetch('/api/prompt-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt_type: promptType,
                    content: content.trim()
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showToast('success', '提示词内容保存成功');
                this.showPromptInfo(`提示词已保存: ${selectedPrompt}`);
            } else {
                this.showToast('error', result.error || '保存提示词失败');
            }
        } catch (error) {
            console.error('保存提示词内容失败:', error);
            this.showToast('error', '保存提示词内容失败');
        }
    }

    async resetPromptContent() {
        const selectedPrompt = this.elements.promptSelect?.value;
        if (!selectedPrompt) {
            this.showToast('warning', '请先选择提示词类型');
            return;
        }

        try {
            // 获取提示词类型键
            const promptType = this.promptNameToKey[selectedPrompt] || selectedPrompt;
            
            const response = await fetch('/api/prompt-content/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt_type: promptType
                })
            });

            const result = await response.json();
            
            if (result.success) {
                // 更新编辑器内容为原始内容
                this.elements.promptEditor.value = result.data.content;
                this.showToast('success', '提示词内容已重置为原始版本');
                this.showPromptInfo(`提示词已重置: ${selectedPrompt}`);
            } else {
                this.showToast('error', result.error || '重置提示词失败');
            }
        } catch (error) {
            console.error('重置提示词内容失败:', error);
            this.showToast('error', '重置提示词内容失败');
        }
    }

    clearPromptEditor() {
        if (this.elements.promptEditor) {
            this.elements.promptEditor.value = '';
        }
        if (this.elements.promptEditorCard) {
            this.elements.promptEditorCard.classList.add('d-none');
        }
        this.hidePromptInfo();
    }

    showPromptInfo(message) {
        if (this.elements.promptInfo && this.elements.promptInfoText) {
            this.elements.promptInfoText.textContent = message;
            this.elements.promptInfo.classList.remove('d-none');
        }
    }

    hidePromptInfo() {
        if (this.elements.promptInfo) {
            this.elements.promptInfo.classList.add('d-none');
        }
    }

    // 设置相关方法
    showSettingsModal() {
        this.elements.settingsModal.show();
    }

    loadSettings(settings) {
        if (!settings) return;

        // 加载LLM设置
        if (settings.llm) {
            const llm = settings.llm;
            if (this.elements.apiKey) this.elements.apiKey.value = llm.api_key || '';
            if (this.elements.baseUrl) this.elements.baseUrl.value = llm.base_url || 'https://api.openai.com/v1';
            if (this.elements.modelName) this.elements.modelName.value = llm.model || 'gpt-3.5-turbo';
            if (this.elements.temperature) this.elements.temperature.value = llm.temperature || 0.7;
            if (this.elements.maxTokens) this.elements.maxTokens.value = llm.max_tokens || 2000;
            if (this.elements.timeout) this.elements.timeout.value = llm.timeout || 30;
        }

        // 不再加载自动保存设置
    }

    async saveSettings() {
        // 乐观提交：点击后立即关闭设置窗口并开始异步保存
        try {
            if (this.elements.saveSettingsBtn) this.elements.saveSettingsBtn.disabled = true;
            // 立即关闭模态框，避免等待网络
            this.elements.settingsModal?.hide();

            const settings = {
                llm: {
                    api_key: this.elements.apiKey?.value || '',
                    base_url: this.elements.baseUrl?.value || 'https://api.openai.com/v1',
                    model: this.elements.modelName?.value || 'gpt-3.5-turbo',
                    temperature: parseFloat(this.elements.temperature?.value || 0.7),
                    max_tokens: parseInt(this.elements.maxTokens?.value || 2000),
                    timeout: parseInt(this.elements.timeout?.value || 30)
                }
            };

            // 设置6秒超时，避免卡顿感
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 6000);

            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings),
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const result = await response.json();

            if (result.success) {
                this.showToast('success', '设置已保存');
            } else {
                this.showToast('error', result.error || '保存设置失败');
            }
        } catch (error) {
            console.error('保存设置失败:', error);
            // 根据异常类型给出更友好的提示
            if (error.name === 'AbortError') {
                this.showToast('error', '保存超时，请重试');
            } else {
                this.showToast('error', '保存设置失败');
            }
        } finally {
            if (this.elements.saveSettingsBtn) this.elements.saveSettingsBtn.disabled = false;
        }
    }

    // 静默保存设置：不关闭设置弹窗，不提示成功，仅返回布尔结果
    async saveSettingsSilently() {
        try {
            const settings = {
                llm: {
                    api_key: this.elements.apiKey?.value || '',
                    base_url: this.elements.baseUrl?.value || 'https://api.openai.com/v1',
                    model: this.elements.modelName?.value || 'gpt-3.5-turbo',
                    temperature: parseFloat(this.elements.temperature?.value || 0.7),
                    max_tokens: parseInt(this.elements.maxTokens?.value || 2000),
                    timeout: parseInt(this.elements.timeout?.value || 30)
                }
            };

            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });

            const result = await response.json();
            return !!result.success;
        } catch (error) {
            console.error('静默保存设置失败:', error);
            return false;
        }
    }

    applyTheme(theme) {
        const body = document.body;
        body.classList.remove('theme-light', 'theme-dark');
        
        if (theme === 'dark') {
            body.classList.add('theme-dark');
        } else if (theme === 'light') {
            body.classList.add('theme-light');
        } else if (theme === 'auto') {
            // 跟随系统设置
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            body.classList.add(prefersDark ? 'theme-dark' : 'theme-light');
        }
    }

    updateDefaultValues(settings) {
        // 更新生成表单的默认值
        if (settings.generation) {
            const gen = settings.generation;
            if (this.elements.difficultySelect) {
                this.elements.difficultySelect.value = gen.default_difficulty;
            }
            if (this.elements.cardCount) {
                this.elements.cardCount.value = gen.default_card_count;
            }
            if (gen.default_template && this.elements.templateSelect) {
                this.elements.templateSelect.value = gen.default_template;
            }
            if (gen.default_prompt_type && this.elements.promptSelect) {
                this.elements.promptSelect.value = gen.default_prompt_type;
            }
        }
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new AnkiCardAssistant();
});

// 全局错误处理
window.addEventListener('error', (e) => {
    console.error('全局错误:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('未处理的Promise拒绝:', e.reason);
});
