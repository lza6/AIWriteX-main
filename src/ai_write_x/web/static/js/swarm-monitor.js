class SwarmMonitor {
    constructor() {
        this.cy = null;
        this.updateInterval = null;
        this.init();
    }

    async init() {
        await this.initCytoscape();
        this.bindEvents();
        this.startAutoRefresh();
        console.log("Swarm Monitor v18.0 Initialized");
    }

    async initCytoscape() {
        // Cytoscape.js 配置
        this.cy = cytoscape({
            container: document.getElementById('swarm-cy-container'),
            style: [
                {
                    selector: 'node[type="agent"]',
                    style: {
                        'background-color': '#007bff',
                        'label': 'data(label)',
                        'color': '#fff',
                        'font-size': '10px',
                        'text-wrap': 'wrap',
                        'width': 60,
                        'height': 60,
                        'text-valign': 'center',
                        'shape': 'hexagon'
                    }
                },
                {
                    selector: 'node[type="task"]',
                    style: {
                        'background-color': '#ffc107',
                        'label': 'data(label)',
                        'shape': 'round-rectangle',
                        'width': 80,
                        'height': 30
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#444',
                        'target-arrow-color': '#444',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '8px'
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true
            }
        });
    }

    bindEvents() {
        document.getElementById('refresh-topology').addEventListener('click', () => {
            this.fetchData();
        });
    }

    async fetchData() {
        try {
            const response = await fetch('/api/swarm/topology');
            const data = await response.json();

            // 更新拓扑图
            this.cy.json({ elements: data.elements });
            this.cy.layout({ name: 'cose', animate: false }).run();

            // 更新统计
            document.getElementById('active-node-count').textContent = data.stats.node_count;
            document.getElementById('consensus-hash').textContent = data.stats.consensus_digest.substring(0, 16) + "...";

        } catch (error) {
            console.error("Failed to fetch swarm topology:", error);
        }
    }

    startAutoRefresh() {
        this.updateInterval = setInterval(() => this.fetchData(), 3000);
    }
}

// 自动实例化
document.addEventListener('DOMContentLoaded', () => {
    window.swarmMonitor = new SwarmMonitor();
});
