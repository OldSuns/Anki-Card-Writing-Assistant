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
        
        // 恢复页面滚动位置
        this.restoreScrollPosition();
        
        console.log('Anki Card Assistant initialized successfully');
    }

    cacheElements() {
        // 表单元素
        this.elements.form = document.getElementById('generation-form');
        this.elements.contentInput = document.getElementById('content-input');
        this.elements.deckNameInput = document.getElementById('deck-name-input');
        
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
        this.elements.toggleApiKeyBtn = document.getElementById('toggle-api-key');
        this.elements.toggleApiKeyIcon = document.getElementById('toggle-api-key-icon');
        this.modals.apiTest = new bootstrap.Modal(document.getElementById('api-test-modal'));
        this.elements.apiTestResult = document.getElementById('api-test-result');
        
        // 模态框
        this.modals.loading = new bootstrap.Modal(document.getElementById('loading-modal'));
        this.modals.apkgExport = new bootstrap.Modal(document.getElementById('apkg-export-modal'));
        
        // 吐司通知
        this.toasts.error = new bootstrap.Toast(document.getElementById('error-toast'));
        this.toasts.success = new bootstrap.Toast(document.getElementById('success-toast'));
        
        // 历史记录相关元素
        this.elements.historyBtn = document.getElementById('history-btn');
        this.modals.history = new bootstrap.Modal(document.getElementById('history-modal'));
        this.modals.historyDetail = new bootstrap.Modal(document.getElementById('history-detail-modal'));
        this.elements.historyLoading = document.getElementById('history-loading');
        this.elements.historyList = document.getElementById('history-list');
        this.elements.historyEmpty = document.getElementById('history-empty');
        this.elements.historyRecords = document.getElementById('history-records');
        this.elements.historyCount = document.getElementById('history-count');
        this.elements.refreshHistoryBtn = document.getElementById('refresh-history-btn');
        
        // 历史记录详情元素
        this.elements.detailLoading = document.getElementById('detail-loading');
        this.elements.detailContent = document.getElementById('detail-content');
        this.elements.detailTimestamp = document.getElementById('detail-timestamp');
        this.elements.detailDeckName = document.getElementById('detail-deck-name');
        this.elements.detailCardCount = document.getElementById('detail-card-count');
        this.elements.detailContentPreview = document.getElementById('detail-content-preview');
        this.elements.detailCardsList = document.getElementById('detail-cards-list');
        this.elements.detailFiles = document.getElementById('detail-files');
        this.elements.deleteRecordBtn = document.getElementById('delete-record-btn');
        
        // 历史记录卡片导航元素
        this.elements.cardNavigationInfo = document.getElementById('card-navigation-info');
        this.elements.prevCardBtn = document.getElementById('prev-card-btn');
        this.elements.nextCardBtn = document.getElementById('next-card-btn');

        // 初始禁用“提示词类型”，待选择模板后启用
        if (this.elements.promptSelect) {
            this.elements.promptSelect.disabled = true;
            // 确保占位选项存在
            this.elements.promptSelect.innerHTML = '';
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = '请选择...';
            this.elements.promptSelect.appendChild(defaultOption);
        }
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

        // 内容输入框事件
        this.elements.contentInput?.addEventListener('input', () => {
            // 当用户开始输入时，清除保存的滚动位置
            if (this.elements.contentInput.value.trim() === '') {
                this.clearScrollPosition();
            }
        });

        // 模板变更 → 动态填充提示词
        this.elements.templateSelect?.addEventListener('change', () => {
            this.updatePromptOptionsByTemplate();
        });

        // 卡片导航
        this.elements.prevCard?.addEventListener('click', () => {
            this.showPreviousCard();
        });

        this.elements.nextCard?.addEventListener('click', () => {
            this.showNextCard();
        });

        // 历史记录详情卡片导航
        this.elements.prevCardBtn?.addEventListener('click', () => {
            this.showPreviousCard();
        });

        this.elements.nextCardBtn?.addEventListener('click', () => {
            this.showNextCard();
        });

        // 监听导出格式复选框变化
        this.initExportFormatListeners();

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

        // 历史记录相关事件
        this.elements.historyBtn?.addEventListener('click', () => {
            this.showHistoryModal();
        });

        this.elements.refreshHistoryBtn?.addEventListener('click', () => {
            this.loadHistoryRecords();
        });

        this.elements.deleteRecordBtn?.addEventListener('click', () => {
            this.deleteHistoryRecord();
        });

        // 设置相关事件
        this.elements.settingsBtn?.addEventListener('click', () => {
            this.showSettingsModal();
        });

        this.elements.saveSettingsBtn?.addEventListener('click', () => {
            this.saveSettings();
        });

        // API密钥显示/隐藏切换
        this.elements.toggleApiKeyBtn?.addEventListener('click', () => {
            this.toggleApiKeyVisibility();
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
        
        // 页面滚动事件 - 保存滚动位置
        window.addEventListener('scroll', this.debounce(() => {
            this.saveScrollPosition();
        }, 100));
        
        // 页面卸载前保存滚动位置
        window.addEventListener('beforeunload', () => {
            this.saveScrollPosition();
        });
    }





    async loadInitialData() {
        try {
            this.showStatus('正在加载配置...', 'info');
            
            // 并行加载模板、配置、设置；提示词列表延后在选择模板时再加载
            const [templatesResponse, configResponse, settingsResponse] = await Promise.all([
                fetch('/api/templates'),
                fetch('/api/config'),
                fetch('/api/settings')
            ]);

            if (templatesResponse.ok) {
                const templatesData = await templatesResponse.json();
                if (templatesData.success) {
                    this.populateSelect(this.elements.templateSelect, templatesData.data);
                }
            }

            if (configResponse.ok) {
                const configData = await configResponse.json();
                if (configData.success) {
                    this.setDefaultValues(configData.data);
                }
            }

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
             
            // 不设置默认模板，保持"请选择..."
            // 不设置默认提示词类型，保持"请选择..."
        }
        
        // 保存默认导出格式
        if (config.export && config.export.default_formats) {
            this.defaultExportFormats = config.export.default_formats;
            // 设置默认选中的导出格式
            this.setDefaultExportFormats();
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
            this.showToast('warning', '请先选择卡片模板');
            return;
        }

        if (!this.elements.promptSelect?.value) {
            this.showToast('warning', '请选择提示词类型');
            return;
        }

        this.isGenerating = true;
        this.showGenerateButton(true);
        this.showProgress(true);
        
        // 开始生成时清除保存的滚动位置
        this.clearScrollPosition();

        const formData = {
            content: content,
            template: this.elements.templateSelect.value,
            prompt_type: this.promptNameToKey[this.elements.promptSelect.value] || this.elements.promptSelect.value,
            language: 'zh-CN',
            difficulty: this.elements.difficultySelect.value,
            card_count: parseInt(this.elements.cardCount.value),
            export_formats: this.getSelectedExportFormats(),
            deck_name: this.elements.deckNameInput?.value.trim() || null
        };

        this.socket.emit('generate_cards', formData);
    }



    getSelectedExportFormats() {
        const formats = [];
        const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
        checkboxes.forEach(checkbox => {
            formats.push(checkbox.value);
        });
        // 如果没有选择任何格式，则使用配置文件中的默认格式
        return formats.length > 0 ? formats : (this.defaultExportFormats || ['json', 'apkg']);
    }

    displayResults(data) {
        this.currentCards = data.cards || [];
        this.currentCardIndex = 0;

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
        
        // 生成新卡片后，滚动到结果区域并清除保存的滚动位置
        this.clearScrollPosition();
        this.scrollToResults();
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
            let fileName = path.replace(/\\/g, '/').split('/').pop() || `${format}_export`;
            
            // 确保文件名不为空且有效
            if (!fileName || fileName.trim() === '') {
                fileName = `${format}_export_${new Date().getTime()}`;
            }
            
            // 记录文件名和路径，便于调试
            console.log(`导出格式: ${format}, 文件名: ${fileName}, 原始路径: ${path}`);
            
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
                        <a href="/download/${encodeURIComponent(fileName)}" class="export-link w-100" target="_blank" title="下载${format.toUpperCase()}格式">
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
            // 确保文件名有效
            if (!fileName || fileName.trim() === '') {
                fileName = `anki_cards_${new Date().getTime()}.apkg`;
            }
            
            // 记录下载尝试
            console.log(`尝试下载APKG文件: ${fileName}`);
            
            // 使用新的下载路由，确保文件名正确编码
            const link = document.createElement('a');
            link.href = `/download/${encodeURIComponent(fileName)}`;
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

        // 选择提示词时清除保存的滚动位置
        this.clearScrollPosition();

        try {
            const promptType = this.promptNameToKey[selectedPrompt] || selectedPrompt;
            const template = this.elements.templateSelect?.value || '';
            
            const response = await fetch(`/api/prompt-content?prompt_type=${encodeURIComponent(promptType)}${template ? `&template=${encodeURIComponent(template)}` : ''}`);
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
            const promptType = this.promptNameToKey[selectedPrompt] || selectedPrompt;
            const template = this.elements.templateSelect?.value || '';
            
            const response = await fetch('/api/prompt-content', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt_type: promptType,
                    content: content.trim(),
                    template: template || undefined
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
            const promptType = this.promptNameToKey[selectedPrompt] || selectedPrompt;
            const template = this.elements.templateSelect?.value || '';
            
            const response = await fetch('/api/prompt-content/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt_type: promptType,
                    template: template || undefined
                })
            });

            const result = await response.json();
            
            if (result.success) {
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
        // 打开设置时清除保存的滚动位置
        this.clearScrollPosition();
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
            if (this.elements.maxTokens) this.elements.maxTokens.value = llm.max_tokens || 20000;
            if (this.elements.timeout) this.elements.timeout.value = llm.timeout || 30;
        }
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
                    max_tokens: parseInt(this.elements.maxTokens?.value || 20000),
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

    // API密钥显示/隐藏切换
    toggleApiKeyVisibility() {
        const apiKeyInput = this.elements.apiKey;
        const toggleIcon = this.elements.toggleApiKeyIcon;
        
        if (apiKeyInput && toggleIcon) {
            if (apiKeyInput.type === 'password') {
                // 显示密钥
                apiKeyInput.type = 'text';
                toggleIcon.className = 'fas fa-eye-slash';
                toggleIcon.title = '隐藏API密钥';
            } else {
                // 隐藏密钥
                apiKeyInput.type = 'password';
                toggleIcon.className = 'fas fa-eye';
                toggleIcon.title = '显示API密钥';
            }
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
                    max_tokens: parseInt(this.elements.maxTokens?.value || 20000),
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
            // 不设置默认模板和提示词类型，保持"请选择..."
        }
    }

    // 基于所选模板更新“提示词类型”选项
    async updatePromptOptionsByTemplate() {
        if (!this.elements.promptSelect) return;
        const template = this.elements.templateSelect?.value || '';

        // 切换模板时清除保存的滚动位置
        this.clearScrollPosition();

        // 重置下拉框
        this.elements.promptSelect.innerHTML = '';
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '请选择...';
        this.elements.promptSelect.appendChild(defaultOption);

        // 无模板时禁用
        if (!template) {
            this.elements.promptSelect.disabled = true;
            return;
        }

        // 从后端按模板加载提示词键与名称（保持与服务端一致）
        try {
            const [keysResp, namesResp] = await Promise.all([
                fetch(`/api/prompts?template=${encodeURIComponent(template)}`),
                fetch(`/api/prompt-names?template=${encodeURIComponent(template)}`)
            ]);
            if (keysResp.ok && namesResp.ok) {
                const keysData = await keysResp.json();
                const namesData = await namesResp.json();
                if (keysData.success && namesData.success) {
                    // 建立映射
                    this.promptNameToKey = {};
                    this.promptKeyToName = {};
                    keysData.data.forEach((key, index) => {
                        const name = namesData.data[index] || key;
                        this.promptNameToKey[name] = key;
                        this.promptKeyToName[key] = name;
                    });
                    // 填充下拉
                    namesData.data.forEach((displayName) => {
                        const optionElement = document.createElement('option');
                        optionElement.value = displayName;
                        optionElement.textContent = displayName;
                        this.elements.promptSelect.appendChild(optionElement);
                    });
                }
            }
        } catch (e) {
            console.error('加载提示词列表失败:', e);
        }

        this.elements.promptSelect.disabled = false;
        this.clearPromptEditor();
    }

    // 设置默认导出格式
    setDefaultExportFormats() {
        if (!this.defaultExportFormats || !Array.isArray(this.defaultExportFormats)) {
            return;
        }
        
        // 取消选中所有导出格式复选框
        const exportCheckboxes = document.querySelectorAll('input[type="checkbox"][id^="export-"]');
        exportCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // 根据配置选中默认的导出格式
        this.defaultExportFormats.forEach(format => {
            const checkbox = document.getElementById(`export-${format}`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
    }

    // 初始化导出格式监听器
    initExportFormatListeners() {
        // 为所有导出格式复选框添加变化事件监听器
        const exportCheckboxes = document.querySelectorAll('.export-format-checkbox');
        exportCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateExportFormatsInConfig();
            });
        });
    }

    // 更新配置文件中的导出格式
    async updateExportFormatsInConfig() {
        try {
            // 获取当前选中的导出格式
            const selectedFormats = this.getSelectedExportFormats();
            
            // 发送到后端更新配置
            const response = await fetch('/api/update-export-formats', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    export_formats: selectedFormats
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('success', '导出格式已保存到配置文件');
                // 更新本地存储的默认导出格式
                this.defaultExportFormats = selectedFormats;
            } else {
                this.showToast('error', result.error || '保存导出格式失败');
            }
        } catch (error) {
            console.error('更新导出格式失败:', error);
            this.showToast('error', '保存导出格式失败');
        }
    }

    // ==================== 历史记录功能 ====================
    
    // 显示历史记录模态框
    showHistoryModal() {
        this.modals.history.show();
        this.loadHistoryRecords();
        // 打开历史记录时清除保存的滚动位置
        this.clearScrollPosition();
    }

    // 加载历史记录
    async loadHistoryRecords() {
        try {
            console.log('开始加载历史记录...');
            
            // 检查必要元素是否存在
            if (!this.elements.historyLoading || !this.elements.historyList || !this.elements.historyEmpty) {
                console.error('历史记录相关元素不存在');
                return;
            }
            
            // 显示加载状态
            this.elements.historyLoading.classList.remove('d-none');
            this.elements.historyList.classList.add('d-none');
            this.elements.historyEmpty.classList.add('d-none');

            const response = await fetch('/api/history');
            console.log('历史记录API响应状态:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log('历史记录API响应数据:', result);

            if (result.success) {
                const records = result.data;
                console.log('获取到的历史记录:', records);
                
                if (this.elements.historyCount) {
                    this.elements.historyCount.textContent = records.length;
                }

                if (!Array.isArray(records) || records.length === 0) {
                    // 显示空状态
                    console.log('没有历史记录，显示空状态');
                    this.elements.historyLoading.classList.add('d-none');
                    this.elements.historyEmpty.classList.remove('d-none');
                } else {
                    // 显示记录列表
                    console.log('开始渲染历史记录列表');
                    this.renderHistoryRecords(records);
                    this.elements.historyLoading.classList.add('d-none');
                    this.elements.historyList.classList.remove('d-none');
                }
            } else {
                throw new Error(result.error || '加载历史记录失败');
            }
        } catch (error) {
            console.error('加载历史记录失败:', error);
            this.showToast('error', error.message || '加载历史记录失败');
            
            if (this.elements.historyLoading) {
                this.elements.historyLoading.classList.add('d-none');
            }
            if (this.elements.historyEmpty) {
                this.elements.historyEmpty.classList.remove('d-none');
            }
        }
    }

    // 渲染历史记录列表
    renderHistoryRecords(records) {
        if (!this.elements.historyRecords) {
            console.error('历史记录容器元素不存在');
            return;
        }
        
        this.elements.historyRecords.innerHTML = '';

        if (!Array.isArray(records) || records.length === 0) {
            console.log('没有历史记录数据');
            return;
        }

        console.log('开始渲染历史记录:', records);

        records.forEach((record, index) => {
            try {
                const recordElement = document.createElement('div');
                recordElement.className = 'list-group-item list-group-item-action';
                
                // 确保数据字段存在，提供默认值
                const deckName = record.deck_name || '未知牌组';
                const timestampDisplay = record.timestamp_display || '未知时间';
                const contentPreview = record.content_preview || '无内容预览';
                const cardCount = record.card_count || 0;
                const recordId = record.id || `record_${index}`;
                const files = record.files || {};
                
                recordElement.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="mb-0">${deckName}</h6>
                                <small class="text-muted">${timestampDisplay}</small>
                            </div>
                            <p class="mb-2 text-muted small">${contentPreview}</p>
                            <div class="d-flex align-items-center gap-3">
                                <span class="badge bg-primary">${cardCount} 张卡片</span>
                                <div class="d-flex gap-1">
                                    ${this.renderFileIcons(files)}
                                </div>
                            </div>
                        </div>
                        <div class="ms-3">
                            <button class="btn btn-outline-primary btn-sm" onclick="app.showHistoryDetail('${recordId}')" title="查看详情">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                `;
                this.elements.historyRecords.appendChild(recordElement);
            } catch (error) {
                console.error('渲染历史记录项失败:', error, record);
            }
        });
        
        console.log('历史记录渲染完成');
    }

    // 渲染文件图标
    renderFileIcons(files) {
        if (!files || typeof files !== 'object') {
            return '';
        }
        
        const icons = [];
        const fileTypes = {
            'json': { icon: 'fas fa-code', color: 'text-info', title: 'JSON数据' },
            'csv': { icon: 'fas fa-table', color: 'text-success', title: 'CSV表格' },
            'html': { icon: 'fas fa-file-code', color: 'text-warning', title: 'HTML文件' },
            'txt': { icon: 'fas fa-file-alt', color: 'text-secondary', title: '文本文件' },
            'apkg': { icon: 'fas fa-download', color: 'text-danger', title: 'Anki包文件' }
        };

        try {
            Object.entries(files).forEach(([type, file]) => {
                if (file && file.exists) {
                    const fileType = fileTypes[type];
                    if (fileType) {
                        icons.push(`
                            <i class="${fileType.icon} ${fileType.color}" title="${fileType.title}" style="font-size: 0.9em;"></i>
                        `);
                    }
                }
            });
        } catch (error) {
            console.error('渲染文件图标失败:', error);
        }

        return icons.join('');
    }

    // 显示历史记录详情
    async showHistoryDetail(recordId) {
        try {
            // 显示加载状态
            this.elements.detailLoading.classList.remove('d-none');
            this.elements.detailContent.classList.add('d-none');

            const response = await fetch(`/api/history/${recordId}/detail`);
            const result = await response.json();

            if (result.success) {
                const data = result.data;
                
                // 填充基本信息
                this.elements.detailTimestamp.textContent = this.formatTimestamp(data.timestamp || recordId);
                this.elements.detailDeckName.textContent = data.deck_name || '未知牌组';
                this.elements.detailCardCount.textContent = data.card_count || (data.cards ? data.cards.length : 0);
                this.elements.detailContentPreview.textContent = data.content_preview || '无';

                // 渲染卡片列表
                this.renderDetailCards(data.cards || []);

                // 渲染文件下载 - 需要重新获取文件信息
                await this.renderDetailFiles(recordId, {});

                // 设置删除按钮的记录ID
                this.elements.deleteRecordBtn.setAttribute('data-record-id', recordId);

                // 显示详情内容
                this.elements.detailLoading.classList.add('d-none');
                this.elements.detailContent.classList.remove('d-none');
                
                // 显示详情模态框
                this.modals.historyDetail.show();
            } else {
                throw new Error(result.error || '加载详情失败');
            }
        } catch (error) {
            console.error('加载历史记录详情失败:', error);
            this.showToast('error', error.message || '加载详情失败');
        }
    }

    // 渲染详情卡片列表（单卡片显示模式）
    renderDetailCards(cards) {
        if (!this.elements.detailCardsList) {
            console.error('详情卡片列表容器不存在');
            return;
        }
        
        this.elements.detailCardsList.innerHTML = '';

        if (!Array.isArray(cards) || cards.length === 0) {
            this.elements.detailCardsList.innerHTML = '<p class="text-muted">暂无卡片数据</p>';
            this.updateCardNavigation(0, 0);
            return;
        }

        // 存储卡片数据供导航使用
        this.currentCards = cards;
        this.currentCardIndex = 0;
        
        // 显示第一张卡片
        this.showCard(0);
    }
    
    // 显示指定索引的卡片
    showCard(cardIndex) {
        if (!this.currentCards || cardIndex < 0 || cardIndex >= this.currentCards.length) {
            return;
        }
        
        const card = this.currentCards[cardIndex];
        this.currentCardIndex = cardIndex;
        
        try {
            // 处理不同格式的卡片数据
            let frontContent = '无';
            let backContent = '无';
            let tags = [];
            let deckName = '';
            
            if (card && typeof card === 'object') {
                // 新格式：直接有front/back字段
                if (card.front !== undefined) {
                    frontContent = card.front || '无';
                } else if (card.fields && card.fields.Front) {
                    // 旧格式：在fields中
                    frontContent = card.fields.Front || '无';
                }
                
                if (card.back !== undefined) {
                    backContent = card.back || '无';
                } else if (card.fields && card.fields.Back) {
                    // 旧格式：在fields中
                    backContent = card.fields.Back || '无';
                }
                
                // 获取标签
                if (card.tags && Array.isArray(card.tags)) {
                    tags = card.tags;
                } else if (card.fields && card.fields.Tags) {
                    tags = card.fields.Tags.split(' ').filter(tag => tag.trim());
                }
                
                // 获取牌组名称
                deckName = card.deckName || card.deck || card.fields?.Deck || '';
            }
            
            // 清理HTML内容，防止XSS
            const cleanHtml = (html) => {
                if (!html) return '无';
                return html
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/\n/g, '<br>');
            };
            
            this.elements.detailCardsList.innerHTML = `
                <div class="card">
                    <div class="card-header py-2">
                        <h6 class="mb-0">卡片 ${cardIndex + 1}</h6>
                    </div>
                    <div class="card-body py-2">
                        <div class="row">
                            <div class="col-md-6">
                                <strong>正面：</strong>
                                <div class="border rounded p-2 bg-light mt-1">${cleanHtml(frontContent)}</div>
                            </div>
                            <div class="col-md-6">
                                <strong>背面：</strong>
                                <div class="border rounded p-2 bg-light mt-1">${cleanHtml(backContent)}</div>
                            </div>
                        </div>
                        ${tags.length > 0 ? `
                        <div class="row mt-2">
                            <div class="col-12">
                                <strong>标签：</strong>
                                <div class="mt-1">
                                    ${tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                                </div>
                            </div>
                        </div>` : ''}
                        ${deckName ? `
                        <div class="row mt-2">
                            <div class="col-12">
                                <strong>牌组：</strong>
                                <span class="text-muted">${deckName}</span>
                            </div>
                        </div>` : ''}
                    </div>
                </div>
            `;
            
            // 更新导航状态
            this.updateCardNavigation(cardIndex, this.currentCards.length);
        } catch (error) {
            console.error('渲染卡片详情失败:', error, card);
        }
    }
    
    // 更新卡片导航状态
    updateCardNavigation(currentIndex, totalCards) {
        if (this.elements.cardNavigationInfo) {
            this.elements.cardNavigationInfo.textContent = `${currentIndex + 1} / ${totalCards}`;
        }
        
        if (this.elements.prevCardBtn) {
            this.elements.prevCardBtn.disabled = currentIndex <= 0;
        }
        
        if (this.elements.nextCardBtn) {
            this.elements.nextCardBtn.disabled = currentIndex >= totalCards - 1;
        }
    }
    
    // 显示上一张卡片
    showPreviousCard() {
        if (this.currentCardIndex > 0) {
            this.showCard(this.currentCardIndex - 1);
        }
    }
    
    // 显示下一张卡片
    showNextCard() {
        if (this.currentCards && this.currentCardIndex < this.currentCards.length - 1) {
            this.showCard(this.currentCardIndex + 1);
        }
    }

    // 渲染详情文件下载
    async renderDetailFiles(recordId, files) {
        this.elements.detailFiles.innerHTML = '';

        const fileTypes = {
            'json': { name: 'JSON数据', icon: 'fas fa-code', color: 'btn-outline-info' },
            'csv': { name: 'CSV表格', icon: 'fas fa-table', color: 'btn-outline-success' },
            'html': { name: 'HTML文件', icon: 'fas fa-file-code', color: 'btn-outline-warning' },
            'txt': { name: '文本文件', icon: 'fas fa-file-alt', color: 'btn-outline-secondary' },
            'apkg': { name: 'Anki包', icon: 'fas fa-download', color: 'btn-outline-danger' }
        };

        // 检查文件是否存在
        const fileChecks = Object.keys(fileTypes).map(async (type) => {
            try {
                const response = await fetch(`/api/history/${recordId}/download/${type}`);
                if (response.ok) {
                    const contentLength = response.headers.get('content-length');
                    const fileSize = contentLength ? parseInt(contentLength) : 0;
                    return { type, exists: true, size: fileSize };
                } else {
                    return { type, exists: false };
                }
            } catch (error) {
                return { type, exists: false };
            }
        });

        const fileResults = await Promise.all(fileChecks);

        fileResults.forEach((file) => {
            if (file.exists) {
                const fileType = fileTypes[file.type];
                const fileSize = this.formatFileSize(file.size);
                
                const fileElement = document.createElement('div');
                fileElement.className = 'col-md-6 col-lg-4 mb-2';
                fileElement.innerHTML = `
                    <button class="btn ${fileType.color} btn-sm w-100" 
                            onclick="app.downloadHistoryFile('${recordId}', '${file.type}')" 
                            title="${fileType.name} (${fileSize})">
                        <i class="${fileType.icon} me-2"></i>
                        ${fileType.name}
                        <br><small class="text-muted">${fileSize}</small>
                    </button>
                `;
                this.elements.detailFiles.appendChild(fileElement);
            }
        });
    }

    // 下载历史记录文件
    async downloadHistoryFile(recordId, fileType) {
        try {
            const response = await fetch(`/api/history/${recordId}/download/${fileType}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${recordId}.${fileType}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.showToast('success', '文件下载成功');
            } else {
                const result = await response.json();
                throw new Error(result.error || '下载失败');
            }
        } catch (error) {
            console.error('下载文件失败:', error);
            this.showToast('error', error.message || '下载文件失败');
        }
    }

    // 删除历史记录
    async deleteHistoryRecord() {
        const recordId = this.elements.deleteRecordBtn.getAttribute('data-record-id');
        if (!recordId) {
            this.showToast('error', '记录ID不存在');
            return;
        }

        if (!confirm('确定要删除这条历史记录吗？此操作不可恢复。')) {
            return;
        }

        try {
            const response = await fetch(`/api/history/${recordId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (result.success) {
                this.showToast('success', result.message || '删除成功');
                this.modals.historyDetail.hide();
                this.loadHistoryRecords(); // 重新加载历史记录列表
            } else {
                throw new Error(result.error || '删除失败');
            }
        } catch (error) {
            console.error('删除历史记录失败:', error);
            this.showToast('error', error.message || '删除失败');
        }
    }

    // 格式化时间戳
    formatTimestamp(timestamp) {
        try {
            if (timestamp.includes('_')) {
                // 从文件名解析时间戳
                // 格式: anki_cards_20250828_231020
                const parts = timestamp.split('_');
                if (parts.length >= 3) {
                    const dateStr = parts[parts.length - 2]; // 20250828
                    const timeStr = parts[parts.length - 1]; // 231020
                    
                    if (dateStr.length === 8 && timeStr.length === 6) {
                        const year = parseInt(dateStr.substring(0, 4));
                        const month = parseInt(dateStr.substring(4, 6)) - 1; // 月份从0开始
                        const day = parseInt(dateStr.substring(6, 8));
                        const hour = parseInt(timeStr.substring(0, 2));
                        const minute = parseInt(timeStr.substring(2, 4));
                        const second = parseInt(timeStr.substring(4, 6));
                        
                        const date = new Date(year, month, day, hour, minute, second);
                        return date.toLocaleString('zh-CN');
                    }
                }
                // 如果解析失败，返回原始时间戳
                return timestamp;
            } else {
                // ISO格式时间戳
                return new Date(timestamp).toLocaleString('zh-CN');
            }
        } catch (error) {
            return timestamp;
        }
    }

    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // 保存滚动位置
    saveScrollPosition() {
        try {
            const scrollPosition = {
                x: window.pageXOffset || document.documentElement.scrollLeft,
                y: window.pageYOffset || document.documentElement.scrollTop,
                timestamp: Date.now()
            };
            sessionStorage.setItem('ankiAssistant_scrollPosition', JSON.stringify(scrollPosition));
        } catch (error) {
            console.warn('保存滚动位置失败:', error);
        }
    }

    // 恢复滚动位置
    restoreScrollPosition() {
        try {
            const savedPosition = sessionStorage.getItem('ankiAssistant_scrollPosition');
            if (savedPosition) {
                const position = JSON.parse(savedPosition);
                
                // 检查保存的时间戳，如果超过30分钟则清除
                const now = Date.now();
                const timeDiff = now - position.timestamp;
                const thirtyMinutes = 30 * 60 * 1000; // 30分钟
                
                if (timeDiff > thirtyMinutes) {
                    sessionStorage.removeItem('ankiAssistant_scrollPosition');
                    this.scrollToTop();
                    return;
                }
                
                // 等待页面完全加载后再恢复滚动位置
                const restorePosition = () => {
                    window.scrollTo({
                        left: position.x || 0,
                        top: position.y || 0,
                        behavior: 'instant' // 使用instant避免动画
                    });
                };
                
                // 如果页面已经加载完成，立即恢复位置
                if (document.readyState === 'complete') {
                    setTimeout(restorePosition, 50);
                } else {
                    // 否则等待页面加载完成
                    window.addEventListener('load', () => {
                        setTimeout(restorePosition, 50);
                    });
                }
            } else {
                // 如果没有保存的位置，滚动到顶部
                this.scrollToTop();
            }
        } catch (error) {
            console.warn('恢复滚动位置失败:', error);
            this.scrollToTop();
        }
    }

    // 滚动到顶部
    scrollToTop() {
        window.scrollTo({
            top: 0,
            left: 0,
            behavior: 'smooth'
        });
        // 滚动到顶部时清除保存的位置
        this.clearScrollPosition();
    }

    // 滚动到结果区域
    scrollToResults() {
        const resultsSection = document.querySelector('.col-lg-8');
        if (resultsSection) {
            resultsSection.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }

    // 清除保存的滚动位置
    clearScrollPosition() {
        try {
            sessionStorage.removeItem('ankiAssistant_scrollPosition');
        } catch (error) {
            console.warn('清除滚动位置失败:', error);
        }
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AnkiCardAssistant();
});

// 全局错误处理
window.addEventListener('error', (e) => {
    console.error('全局错误:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('未处理的Promise拒绝:', e.reason);
});
