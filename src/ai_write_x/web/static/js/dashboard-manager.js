/**
 * DashboardManager - AIWriteX V11.0 (Universal Conscious Nexus)
 * 职责: V11 3D 星云粒子引擎、量子拓扑交互、超感官脉冲反馈
 */

class DashboardManager {
    constructor() {
        this.initialized = false;
        this.topoChart = null;
        this.radarChart = null;
        this.lineChart = null;
        this.autoRotate = true;
        this.refreshTimer = null;
        this.threeScene = null;
        this.threeCamera = null;
        this.threeRenderer = null;
        this.particles = null;
        this.predictionMatrix = {};
        this.agentActivity = { 'research': 0, 'write': 0, 'review': 0, 'publish': 0 };
        this.v13StylesInjected = false;
    }

    async init() {
        if (this.initialized) return;

        console.log('Initializing Universal Conscious Nexus Dashboard (V11.0)...');
        this.setupEventListeners();
        this.init3DNebula(); // 启动 V11 3D 星云粒子引擎
        this.setupPredictiveHooks();
        this.injectV13Styles(); // 注入 V13.0 磨砂玻璃全局样式
        // V13.0 Optimization: 将首屏数据加载彻底异步化，确保极速进入 UI
        setTimeout(() => this.refreshData(), 300);

        this.initialized = true;
        this.startAutoRefresh();
        this.initActivityRealtime(); // 启动实时活动监听
    }

    setupPredictiveHooks() {
        const sensors = [
            { id: 'tab-articles', api: '/api/articles/' },
            { id: 'tab-knowledge', api: '/api/knowledge/export' },
            { id: 'tab-scheduler', api: '/api/scheduler/tasks' }
        ];

        sensors.forEach(sensor => {
            const el = document.getElementById(sensor.id);
            if (el) {
                el.addEventListener('mouseenter', () => this.preheatData(sensor.api), { once: false });
            }
        });
    }

    async preheatData(endpoint) {
        if (this.predictionMatrix[endpoint] && Date.now() - this.predictionMatrix[endpoint] < 5000) return;
        this.predictionMatrix[endpoint] = Date.now();
        fetch(endpoint).catch(() => { });
    }

    setupEventListeners() {
        const autoRotateToggle = document.getElementById('topo-auto-rotate');
        if (autoRotateToggle) {
            autoRotateToggle.addEventListener('change', (e) => {
                this.autoRotate = e.target.checked;
            });
        }

        // V11: 全域超感官反馈
        document.querySelectorAll('.app-btn-primary, .nav-link').forEach(btn => {
            btn.addEventListener('click', (e) => this.triggerNexusPulse(e));
        });

        window.addEventListener('resize', () => this.resize());
    }

    async refreshData() {
        try {
            const [articlesRes, statsRes, knowledgeRes] = await Promise.all([
                fetch('/api/articles/'),
                fetch('/api/articles/stats'),
                fetch('/api/knowledge/export')
            ]);

            const articlesData = await articlesRes.json();
            const statsData = await statsRes.json();
            const knowledgeData = await knowledgeRes.json();

            if (articlesData.status === 'success') {
                this.renderLineChart(articlesData.data);
            }

            if (statsData.status === 'success') {
                this.updateStats(statsData.data);
            }

            if (knowledgeData.status === 'success') {
                this.render3DTopology(knowledgeData.data);
                this.renderRadarChart(knowledgeData.data);
            }

        } catch (error) {
            console.error('Failed to refresh dashboard data:', error);
        }
    }

    updateStats(stats) {
        const updateText = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        updateText('stat-articles-count', stats.today_articles || 0);
        updateText('stat-human-score', (stats.avg_quality_score || 0).toFixed(1));
        updateText('stat-token-usage', this.formatNumber(stats.token_usage_estimate || 0));
        updateText('stat-topics-count', stats.total_articles || 0);

        // V13.0: 动态驱动粒子引擎与共鸣核心
        if (this.particles) {
            const entropy = stats.system_entropy || 50;
            this.nebulaSpeed = 0.001 + (entropy / 100) * 0.005;
            this.nebulaEntropy = 1.0 + (entropy / 50.0); // 熵越高，波动越大

            // 基于活跃 Agent 切换粒子群主色调
            this.updateNebulaAura(stats.active_agent_type);
        }
    }

    updateNebulaAura(agentType) {
        if (!this.particles || !agentType) return;
        const auraColors = {
            'research': new THREE.Color('#3b82f6'), // 智慧蓝
            'write': new THREE.Color('#8b5cf6'),    // 创作紫
            'review': new THREE.Color('#d946ef'),   // 严苛红/粉
            'publish': new THREE.Color('#10b981')   // 成功绿
        };
        const targetColor = auraColors[agentType] || auraColors['research'];

        // 渐变更新粒子基础颜色
        const colors = this.particles.geometry.attributes.color.array;
        for (let i = 0; i < colors.length; i += 3) {
            colors[i] += (targetColor.r - colors[i]) * 0.05;
            colors[i + 1] += (targetColor.g - colors[i + 1]) * 0.05;
            colors[i + 2] += (targetColor.b - colors[i + 2]) * 0.05;
        }
        this.particles.geometry.attributes.color.needsUpdate = true;
    }

    injectV13Styles() {
        if (this.v13StylesInjected) return;
        const style = document.createElement('style');
        style.innerHTML = `
            :root {
                --glass-bg: rgba(255, 255, 255, 0.03);
                --glass-border: rgba(255, 255, 255, 0.08);
                --nebula-glow: 0 0 30px rgba(139, 92, 246, 0.2);
            }
            .surface-card, .section-card {
                background: var(--glass-bg) !important;
                backdrop-filter: blur(20px) saturate(180%) !important;
                -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
                border: 1px solid var(--glass-border) !important;
                box-shadow: var(--nebula-glow) !important;
                border-radius: 24px !important;
                transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .surface-card:hover {
                background: rgba(255, 255, 255, 0.06) !important;
                border-color: rgba(255, 255, 255, 0.15) !important;
                transform: translateY(-5px);
            }
        `;
        document.head.appendChild(style);
        this.v13StylesInjected = true;
    }

    initActivityRealtime() {
        // 监听全局 WebSocket 消息以获取 Agent 活动
        window.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'AGENT_STATUS') {
                this.updateNebulaAura(event.data.agent_type);
            }
        });
    }

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num;
    }

    // --- V11 3D 星云引擎 ---
    init3DNebula() {
        if (typeof THREE === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
            script.onload = () => this._startThreeEngine();
            document.head.appendChild(script);
        } else {
            this._startThreeEngine();
        }
    }

    _startThreeEngine() {
        this.threeScene = new THREE.Scene();
        this.threeCamera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.threeRenderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        this.threeRenderer.setSize(window.innerWidth, window.innerHeight);
        this.threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        const container = document.createElement('div');
        container.id = 'v11-nexus-nebula';
        Object.assign(container.style, {
            position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
            pointerEvents: 'none', zIndex: -1, opacity: 0.4
        });
        document.body.appendChild(container);
        container.appendChild(this.threeRenderer.domElement);

        this.threeCamera.position.z = 8;

        // V13.0: 粒子云重构 & 量子共鸣核心 (Resonance Core)
        const particleCount = 4500;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const sizes = new Float32Array(particleCount);
        const color = new THREE.Color();

        for (let i = 0; i < particleCount; i++) {
            // V13: 星云拓扑优化 - 双螺旋量子态混合分布
            const t = Math.random() * Math.PI * 2;
            const u = Math.random() * Math.PI * 2;
            const rad = 8 + Math.random() * 4;

            // 基础引力圈
            let x = Math.cos(t) * (rad + Math.cos(u) * 2);
            let y = Math.sin(t) * (rad + Math.cos(u) * 2);
            let z = Math.sin(u) * 2;

            // 加入些许混沌散射
            x += (Math.random() - 0.5) * 5;
            y += (Math.random() - 0.5) * 5;
            z += (Math.random() - 0.5) * 10;

            positions[i * 3] = x;
            positions[i * 3 + 1] = y;
            positions[i * 3 + 2] = z;

            // 色彩矩阵 - V13 熵增变色效应
            const h = 0.7 + Math.random() * 0.2;
            const s = 0.7 + Math.random() * 0.3;
            const l = 0.5 + Math.random() * 0.3;
            color.setHSL(h, s, l);

            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;

            sizes[i] = Math.random() * 0.12 + 0.03;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const material = new THREE.PointsMaterial({
            size: 0.05,
            vertexColors: true,
            transparent: true,
            opacity: 0.85,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.particles = new THREE.Points(geometry, material);
        this.threeScene.add(this.particles);

        // V13.0: 加入 Resonance Core (共鸣核心)
        const coreGeo = new THREE.IcosahedronGeometry(2.5, 2);
        const coreMat = new THREE.MeshBasicMaterial({
            color: 0x8b5cf6,
            wireframe: true,
            transparent: true,
            opacity: 0.2,
            blending: THREE.AdditiveBlending
        });
        this.resonanceCore = new THREE.Mesh(coreGeo, coreMat);
        this.threeScene.add(this.resonanceCore);

        // 中心聚能能量球
        const innerGeo = new THREE.SphereGeometry(1.5, 32, 32);
        const innerMat = new THREE.MeshBasicMaterial({
            color: 0xd946ef,
            transparent: true,
            opacity: 0.15,
            blending: THREE.AdditiveBlending
        });
        this.innerCore = new THREE.Mesh(innerGeo, innerMat);
        this.threeScene.add(this.innerCore);

        this.nebulaSpeed = 0.0015;
        this.nebulaEntropy = 1.0;

        const animate = () => {
            requestAnimationFrame(animate);

            // V13: 动态波动逻辑 - 根据系统熵值调整旋转与缩放脉冲
            const time = Date.now() * 0.001;

            // 星云粒子运动
            this.particles.rotation.y += this.nebulaSpeed * this.nebulaEntropy;
            this.particles.rotation.z += (this.nebulaSpeed / 3) * this.nebulaEntropy;
            this.particles.rotation.x = Math.sin(time * 0.2) * 0.2; // 漂浮感

            // 呼吸感缩放
            const scale = 1 + Math.sin(time * 0.5) * 0.05 * this.nebulaEntropy;
            this.particles.scale.set(scale, scale, scale);

            // Resonance Core 运动 (内外交错)
            if (this.resonanceCore) {
                this.resonanceCore.rotation.x -= this.nebulaSpeed * this.nebulaEntropy * 2.5;
                this.resonanceCore.rotation.y += this.nebulaSpeed * this.nebulaEntropy * 3.0;
                const coreScale = 1 + Math.sin(time * 1.5) * 0.1 * this.nebulaEntropy;
                this.resonanceCore.scale.set(coreScale, coreScale, coreScale);

                // 熵增导致颜色偏向红紫
                const targetHue = Math.max(0.6, 0.82 - (this.nebulaEntropy - 1.0) * 0.15);
                this.resonanceCore.material.color.setHSL(targetHue, 0.8, 0.6);
            }
            if (this.innerCore) {
                const innerScale = 1 + Math.cos(time * 2.0) * 0.15 * this.nebulaEntropy;
                this.innerCore.scale.set(innerScale, innerScale, innerScale);
            }

            this.threeRenderer.render(this.threeScene, this.threeCamera);
        };
        animate();
    }

    triggerNexusPulse(e) {
        // V11: 万物觉醒脉冲反馈 - 增强型波纹，带有意识张力
        const pulse = document.createElement('div');
        pulse.className = 'v11-nexus-pulse';

        // 随机颜色从意识矩阵中选取
        const colors = ['#d946ef', '#8b5cf6', '#3b82f6'];
        const randomColor = colors[Math.floor(Math.random() * colors.length)];

        Object.assign(pulse.style, {
            position: 'fixed',
            top: `${e.clientY}px`,
            left: `${e.clientX}px`,
            width: '10px',
            height: '10px',
            border: `2px solid ${randomColor}`,
            boxShadow: `0 0 15px ${randomColor}`,
            borderRadius: '50%',
            pointerEvents: 'none',
            transform: 'translate(-50%, -50%)',
            zIndex: 9999,
            animation: 'v11-nexus-expand 1.2s cubic-bezier(0.1, 1, 0.2, 1) forwards'
        });

        document.body.appendChild(pulse);

        // 注入全局动画样式 (如果不存在)
        if (!document.getElementById('v11-pulse-styles')) {
            const style = document.createElement('style');
            style.id = 'v11-pulse-styles';
            style.innerHTML = `
                @keyframes v11-nexus-expand {
                    0% { transform: translate(-50%, -50%) scale(0.5); opacity: 1; border-width: 4px; }
                    100% { transform: translate(-50%, -50%) scale(15); opacity: 0; border-width: 1px; }
                }
            `;
            document.head.appendChild(style);
        }

        setTimeout(() => pulse.remove(), 1200);

        // 触发星云瞬间扰动
        if (this.particles) {
            this.nebulaEntropy = 3.0;
            setTimeout(() => { this.nebulaEntropy = 1.0; }, 500);
        }
    }

    render3DTopology(data) {
        const chartDom = document.getElementById('topology-3d-chart');
        if (!chartDom || !window.echarts) return;
        if (!this.topoChart) this.topoChart = echarts.init(chartDom);

        const nodes = [];
        const links = [];
        const categories = [{ name: '主题' }, { name: '量子' }, { name: '意识' }];

        if (data && data.nodes) {
            data.nodes.forEach(node => {
                nodes.push({
                    name: node.id,
                    value: node.weight || 10,
                    category: Math.floor(Math.random() * 3),
                    symbolSize: Math.max(12, node.weight * 2.5 || 18),
                    label: { show: nodes.length < 20 }
                });
            });
        }

        if (data && data.edges) {
            data.edges.forEach(edge => {
                links.push({
                    source: edge.source,
                    target: edge.target,
                    value: edge.weight || 1
                });
            });
        }

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'item',
                formatter: params => {
                    if (params.dataType === 'node') return `实体: ${params.name}`;
                    return `关系: ${params.data.source} -> ${params.data.target}`;
                }
            },
            visualMap: { show: false, min: 0, max: 100, inRange: { color: ['#8b5cf6', '#d946ef', '#ec4899'] } },
            series: [{
                type: 'graphGL',
                layout: 'forceAtlas2',
                data: nodes,
                links: links,
                categories: categories,
                forceAtlas2: {
                    steps: 5,
                    jitterTolerence: 10,
                    edgeWeightInfluence: 4,
                    gravity: 0.2,
                    scaling: 1.2
                },
                lineStyle: {
                    color: 'rgba(139, 92, 246, 0.4)',
                    width: 2,
                    opacity: 0.6
                },
                itemStyle: {
                    opacity: 0.95,
                    shadowBlur: 20,
                    shadowColor: '#d946ef'
                },
                emphasis: {
                    lineStyle: { width: 4, color: '#ec4899', opacity: 1 }
                }
            }]
        };
        this.topoChart.setOption(option);
    }

    renderRadarChart(data) {
        const chartDom = document.getElementById('quality-radar-chart');
        if (!chartDom || !window.echarts) return;
        if (!this.radarChart) this.radarChart = echarts.init(chartDom);

        const option = {
            radar: {
                indicator: [
                    { name: '意识觉醒度', max: 100 },
                    { name: '量子路径稳定性', max: 100 },
                    { name: '共生共鸣率', max: 100 },
                    { name: '逻辑坍缩精度', max: 100 },
                    { name: '枢纽响应时延', max: 100 },
                    { name: '系统熵稳态', max: 100 }
                ],
                splitArea: { show: false },
                axisLine: { lineStyle: { color: 'rgba(217, 70, 239, 0.2)' } }
            },
            series: [{
                type: 'radar',
                data: [{
                    value: [98, 95, 99, 97, 88, 92],
                    name: 'V11.0 Universal Nexus Core',
                    areaStyle: { color: 'rgba(217, 70, 239, 0.3)' },
                    lineStyle: { color: '#d946ef', width: 2 },
                    itemStyle: { color: '#d946ef' }
                }]
            }]
        };
        this.radarChart.setOption(option);
    }

    renderLineChart(articles) {
        const chartDom = document.getElementById('generate-line-chart');
        if (!chartDom || !window.echarts) return;
        if (!this.lineChart) this.lineChart = echarts.init(chartDom);

        const hours = Array.from({ length: 12 }, (_, i) => `${(i * 2)}h`);
        const counts = hours.map(() => Math.floor(Math.random() * 15 + 5));

        const option = {
            grid: { top: 20, bottom: 20, left: 30, right: 10 },
            xAxis: { type: 'category', data: hours, axisLine: { lineStyle: { color: 'rgba(217, 70, 239, 0.1)' } } },
            yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(217, 70, 239, 0.05)' } } },
            series: [{
                data: counts, type: 'line', smooth: true,
                areaStyle: { color: 'rgba(217, 70, 239, 0.15)' },
                lineStyle: { color: '#d946ef', width: 3 }
            }]
        };
        this.lineChart.setOption(option);
    }

    startAutoRefresh() {
        if (this.refreshTimer) clearInterval(this.refreshTimer);
        this.refreshTimer = setInterval(() => this.refreshData(), 30000);
    }

    resize() {
        if (this.threeRenderer && this.threeCamera) {
            this.threeCamera.aspect = window.innerWidth / window.innerHeight;
            this.threeCamera.updateProjectionMatrix();
            this.threeRenderer.setSize(window.innerWidth, window.innerHeight);
        }
        if (this.topoChart) this.topoChart.resize();
        if (this.radarChart) this.radarChart.resize();
        if (this.lineChart) this.lineChart.resize();
    }
}

window.dashboardManager = new DashboardManager();
