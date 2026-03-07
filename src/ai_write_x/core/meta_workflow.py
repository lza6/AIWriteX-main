"""
工作流元学习进化机制 (Workflow Meta-Learning Evolution)
实现工作流的自我进化与优化

核心组件:
1. 工作流基因 - 工作流结构的编码
2. 遗传算法优化器 - 进化工作流结构
3. 贝叶斯超参数优化器
4. 性能反馈闭环
"""
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from datetime import datetime
from collections import defaultdict
import uuid
import json
import random
import math
import copy
import numpy as np

from src.ai_write_x.utils import log


class GeneType(str, Enum):
    """基因类型"""
    SEQUENCE = "sequence"           # 顺序执行
    PARALLEL = "parallel"           # 并行执行
    CONDITIONAL = "conditional"      # 条件分支
    LOOP = "loop"                   # 循环
    MERGE = "merge"                 # 合并
    SPLIT = "split"                 # 分割


class WorkflowGene:
    """
    工作流基因 - 工作流结构的编码
    
    包含:
    - 基因类型
    - 参数
    - 适应度分数
    """
    
    def __init__(
        self,
        gene_id: str = None,
        gene_type: GeneType = GeneType.SEQUENCE,
        params: Dict[str, Any] = None,
        task_id: str = None
    ):
        self.id = gene_id or str(uuid.uuid4())[:8]
        self.gene_type = gene_type
        self.params = params or {}
        self.task_id = task_id
        
        # 适应度
        self.fitness = 0.0
        self.execution_time = 0.0
        self.success_rate = 0.0
        self.quality_score = 0.0
        
        # 元数据
        self.generation = 0
        self.created_at = datetime.now()
    
    def mutate(self, mutation_rate: float = 0.1) -> 'WorkflowGene':
        """基因变异"""
        if random.random() > mutation_rate:
            return self
        
        # 浅拷贝
        new_gene = copy.copy(self)
        new_gene.id = str(uuid.uuid4())[:8]
        
        # 随机变异参数
        param_keys = list(new_gene.params.keys())
        if param_keys:
            key = random.choice(param_keys)
            value = new_gene.params[key]
            
            if isinstance(value, int):
                new_gene.params[key] = value + random.randint(-5, 5)
            elif isinstance(value, float):
                new_gene.params[key] = value * random.uniform(0.9, 1.1)
            elif isinstance(value, bool):
                new_gene.params[key] = not value
        
        return new_gene
    
    def crossover(self, other: 'WorkflowGene') -> 'WorkflowGene':
        """基因交叉"""
        if self.gene_type != other.gene_type:
            return self
        
        # 混合参数
        new_params = {}
        all_keys = set(self.params.keys()) | set(other.params.keys())
        
        for key in all_keys:
            if key in self.params and key in other.params:
                new_params[key] = random.choice([self.params[key], other.params[key]])
            elif key in self.params:
                new_params[key] = self.params[key]
            else:
                new_params[key] = other.params[key]
        
        return WorkflowGene(
            gene_type=self.gene_type,
            params=new_params,
            task_id=self.task_id
        )
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.gene_type.value,
            "params": self.params,
            "fitness": self.fitness,
            "execution_time": self.execution_time,
            "success_rate": self.success_rate,
            "quality_score": self.quality_score
        }


class WorkflowGenome:
    """
    工作流基因组 - 完整的工作流结构
    """
    
    def __init__(
        self,
        genome_id: str = None,
        genes: List[WorkflowGene] = None
    ):
        self.id = genome_id or str(uuid.uuid4())[:8]
        self.genes = genes or []
        
        # 适应度
        self.fitness = 0.0
        self.generation = 0
        
        # 执行历史
        self.execution_history: List[Dict] = []
    
    def add_gene(self, gene: WorkflowGene):
        """添加基因"""
        self.genes.append(gene)
    
    def remove_gene(self, index: int) -> WorkflowGene:
        """移除基因"""
        if 0 <= index < len(self.genes):
            return self.genes.pop(index)
        return None
    
    def crossover(self, other: 'WorkflowGenome') -> 'WorkflowGenome':
        """基因组交叉"""
        # 单点交叉
        crossover_point = random.randint(0, min(len(self.genes), len(other.genes)))
        
        new_genes = self.genes[:crossover_point] + other.genes[crossover_point:]
        
        return WorkflowGenome(genes=new_genes)
    
    def mutate(self, mutation_rate: float = 0.1) -> 'WorkflowGenome':
        """基因组变异"""
        new_genes = [g.mutate(mutation_rate) for g in self.genes]
        
        # 偶尔添加或删除基因
        if random.random() < mutation_rate * 0.3:
            # 添加
            new_gene = WorkflowGene(
                gene_type=random.choice(list(GeneType)),
                params={"weight": random.random()}
            )
            insert_pos = random.randint(0, len(new_genes))
            new_genes.insert(insert_pos, new_gene)
        
        if random.random() < mutation_rate * 0.2 and len(new_genes) > 1:
            # 删除
            remove_pos = random.randint(0, len(new_genes) - 1)
            new_genes.pop(remove_pos)
        
        return WorkflowGenome(genes=new_genes)
    
    def calculate_fitness(
        self,
        execution_time_weight: float = 0.3,
        success_rate_weight: float = 0.4,
        quality_weight: float = 0.3
    ) -> float:
        """计算适应度"""
        if not self.genes:
            return 0.0
        
        # 聚合基因适应度
        avg_time = sum(g.execution_time for g in self.genes) / len(self.genes)
        avg_success = sum(g.success_rate for g in self.genes) / len(self.genes)
        avg_quality = sum(g.quality_score for g in self.genes) / len(self.genes)
        
        # 归一化
        norm_time = 1.0 / (1.0 + avg_time / 60)  # 1分钟为基准
        
        self.fitness = (
            execution_time_weight * norm_time +
            success_rate_weight * avg_success +
            quality_weight * avg_quality
        )
        
        return self.fitness
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "gene_count": len(self.genes),
            "fitness": self.fitness,
            "generation": self.generation,
            "genes": [g.to_dict() for g in self.genes]
        }


class GeneticOptimizer:
    """
    遗传算法优化器 - 进化工作流结构
    
    特性:
    - 种群管理
    - 选择、交叉、变异
    - 精英保留
    - 早停机制
    """
    
    def __init__(
        self,
        population_size: int = 50,
        elite_size: int = 5,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        generations: int = 100,
        timeout: float = 300.0
    ):
        self.population_size = population_size
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.generations = generations
        self.timeout = timeout
        
        # 种群
        self.population: List[WorkflowGenome] = []
        
        # 历史
        self.best_genome: Optional[WorkflowGenome] = None
        self.fitness_history: List[float] = []
        
        # 统计
        self.current_generation = 0
        self.start_time = datetime.now()
    
    def initialize_population(
        self,
        template: Dict[str, Any] = None
    ):
        """初始化种群"""
        self.population = []
        
        for i in range(self.population_size):
            genes = []
            
            # 从模板或随机生成
            if template and "steps" in template:
                for step in template["steps"]:
                    gene = WorkflowGene(
                        gene_type=GeneType(step.get("type", "sequence")),
                        params=step.get("params", {}),
                        task_id=step.get("id")
                    )
                    genes.append(gene)
            else:
                # 随机生成3-8个基因
                gene_count = random.randint(3, 8)
                for _ in range(gene_count):
                    gene = WorkflowGene(
                        gene_type=random.choice(list(GeneType)),
                        params={"weight": random.random()}
                    )
                    genes.append(gene)
            
            genome = WorkflowGenome(genes=genes)
            self.population.append(genome)
        
        log.print_log(f"[遗传算法] 初始化种群 {self.population_size}", "info")
    
    def select_parents(
        self,
        fitnesses: List[float]
    ) -> Tuple[WorkflowGenome, WorkflowGenome]:
        """锦标赛选择"""
        # 随机选择k个候选
        k = 3
        candidates = random.sample(range(len(self.population)), min(k, len(self.population)))
        
        # 选择最优
        best_idx = max(candidates, key=lambda i: fitnesses[i])
        candidates.remove(best_idx)
        
        if candidates:
            second_idx = max(candidates, key=lambda i: fitnesses[i])
        else:
            second_idx = best_idx
        
        return self.population[best_idx], self.population[second_idx]
    
    def evolve(self) -> WorkflowGenome:
        """进化一代"""
        # 计算适应度
        fitnesses = [g.calculate_fitness() for g in self.population]
        
        # 记录最佳
        best_idx = max(range(len(fitnesses)), key=lambda i: fitnesses[i])
        self.best_genome = self.population[best_idx]
        self.fitness_history.append(fitnesses[best_idx])
        
        # 精英保留
        sorted_pop = sorted(
            zip(self.population, fitnesses),
            key=lambda x: x[1],
            reverse=True
        )
        
        new_population = [g for g, _ in sorted_pop[:self.elite_size]]
        
        # 生成新个体
        while len(new_population) < self.population_size:
            # 选择父母
            parent1, parent2 = self.select_parents(fitnesses)
            
            # 交叉
            if random.random() < self.crossover_rate:
                child = parent1.crossover(parent2)
            else:
                child = copy.copy(parent1)
            
            # 变异
            if random.random() < self.mutation_rate:
                child = child.mutate(self.mutation_rate)
            
            child.generation = self.current_generation + 1
            new_population.append(child)
        
        self.population = new_population
        self.current_generation += 1
        
        return self.best_genome
    
    def run(
        self,
        fitness_fn: Callable[[WorkflowGenome], float] = None,
        early_stop_fn: Callable[[int, float], bool] = None
    ) -> WorkflowGenome:
        """运行遗传算法"""
        self.start_time = datetime.now()
        self.current_generation = 0
        
        for gen in range(self.generations):
            # 检查超时
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > self.timeout:
                log.print_log(f"[遗传算法] 超时，停止于第 {gen} 代", "info")
                break
            
            # 进化
            best = self.evolve()
            
            # 早停检查
            if early_stop_fn and early_stop_fn(gen, best.fitness):
                log.print_log(f"[遗传算法] 早停于第 {gen} 代", "info")
                break
            
            if gen % 10 == 0:
                log.print_log(
                    f"[遗传算法] 第 {gen} 代 最佳适应度: {best.fitness:.4f}",
                    "debug"
                )
        
        return self.best_genome
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "population_size": self.population_size,
            "current_generation": self.current_generation,
            "best_fitness": self.best_genome.fitness if self.best_genome else 0.0,
            "fitness_history": self.fitness_history[-10:],
            "elite_size": self.elite_size
        }


class BayesianOptimizer:
    """
    贝叶斯超参数优化器
    
    使用高斯过程建模超参数与性能的关系
    """
    
    def __init__(
        self,
        param_space: Dict[str, Any],
        n_initial: int = 5,
        n_iterations: int = 50
    ):
        self.param_space = param_space
        self.n_initial = n_initial
        self.n_iterations = n_iterations
        
        # 观测历史
        self.observations: List[Dict] = []
        
        # 模型参数
        self.noise = 0.1
        self.length_scale = 1.0
        
        self._lock = asyncio.Lock()
    
    def _sample_params(self) -> Dict[str, Any]:
        """从参数空间采样"""
        params = {}
        
        for name, config in self.param_space.items():
            ptype = config.get("type", "float")
            
            if ptype == "float":
                low = config.get("low", 0.0)
                high = config.get("high", 1.0)
                params[name] = random.uniform(low, high)
            elif ptype == "int":
                low = config.get("low", 0)
                high = config.get("high", 10)
                params[name] = random.randint(low, high)
            elif ptype == "categorical":
                choices = config.get("choices", [0, 1])
                params[name] = random.choice(choices)
            elif ptype == "logfloat":
                low = config.get("low", -3)
                high = config.get("high", 0)
                params[name] = 10 ** random.uniform(low, high)
        
        return params
    
    def _gaussian_kernel(self, x1: Dict, x2: Dict) -> float:
        """高斯核函数"""
        dist_sq = sum(
            ((x1.get(k, 0) - x2.get(k, 0)) / self.length_scale) ** 2
            for k in set(x1.keys()) | set(x2.keys())
        )
        return math.exp(-0.5 * dist_sq)
    
    def _predict_mean_var(
        self,
        x: Dict
    ) -> Tuple[float, float]:
        """预测均值和方差"""
        if not self.observations:
            return 0.0, 1.0
        
        # 计算核矩阵
        K = np.zeros((len(self.observations), len(self.observations)))
        for i, obs1 in enumerate(self.observations):
            for j, obs2 in enumerate(self.observations):
                K[i, j] = self._gaussian_kernel(obs1["params"], obs2["params"])
        
        # 添加噪声
        K += self.noise ** 2 * np.eye(len(self.observations))
        
        # 计算核向量
        k_star = np.array([
            self._gaussian_kernel(x, obs["params"])
            for obs in self.observations
        ])
        
        # 预测
        try:
            K_inv = np.linalg.inv(K)
            mean = np.dot(k_star, np.dot(K_inv, [o["score"] for o in self.observations]))
            var = self._gaussian_kernel(x, x) - np.dot(k_star, np.dot(K_inv, k_star))
            var = max(0.0, var)
        except np.linalg.LinAlgError:
            mean = np.mean([o["score"] for o in self.observations])
            var = 1.0
        
        return mean, var
    
    async def suggest(self) -> Dict[str, Any]:
        """建议下一个参数配置"""
        async with self._lock:
            if len(self.observations) < self.n_initial:
                # 随机采样
                return self._sample_params()
            
            # 使用期望改进(EI)
            best_score = max(o["score"] for o in self.observations)
            
            best_ei = -float("inf")
            best_params = None
            
            # 采样候选
            n_candidates = 100
            for _ in range(n_candidates):
                params = self._sample_params()
                mean, var = self._predict_mean_var(params)
                
                if var < 1e-10:
                    ei = 0.0
                else:
                    z = (mean - best_score - 0.01) / math.sqrt(var)
                    ei = (mean - best_score - 0.01) * self._normal_cdf(z) + math.sqrt(var) * self._normal_pdf(z)
                
                if ei > best_ei:
                    best_ei = ei
                    best_params = params
            
            return best_params or self._sample_params()
    
    def _normal_cdf(self, x: float) -> float:
        """标准正态分布CDF"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def _normal_pdf(self, x: float) -> float:
        """标准正态分布PDF"""
        return math.exp(-0.5 * x ** 2) / math.sqrt(2 * math.pi)
    
    async def observe(
        self,
        params: Dict[str, Any],
        score: float
    ):
        """记录观测结果"""
        async with self._lock:
            self.observations.append({
                "params": params,
                "score": score,
                "timestamp": datetime.now()
            })
    
    def get_best(self) -> Optional[Dict]:
        """获取最佳参数"""
        if not self.observations:
            return None
        
        best = max(self.observations, key=lambda x: x["score"])
        return best["params"]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "observations": len(self.observations),
            "best_score": max(o["score"] for o in self.observations) if self.observations else None,
            "iterations": self.n_iterations
        }


class PerformanceFeedback:
    """
    性能反馈 - 评估工作流执行效果
    """
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
    
    def record(
        self,
        workflow_id: str,
        execution_time: float,
        success: bool,
        quality_score: float,
        resource_usage: Dict[str, float] = None
    ):
        """记录执行指标"""
        key = f"{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.metrics[key] = [
            execution_time,
            1.0 if success else 0.0,
            quality_score,
            resource_usage or {}
        ]
    
    def get_average(
        self,
        workflow_id: str,
        window: int = 10
    ) -> Dict[str, float]:
        """获取平均指标"""
        relevant = {
            k: v for k, v in self.metrics.items()
            if k.startswith(workflow_id)
        }
        
        if not relevant:
            return {
                "avg_time": 0.0,
                "avg_success": 0.0,
                "avg_quality": 0.0
            }
        
        values = list(relevant.values())
        
        return {
            "avg_time": sum(v[0] for v in values) / len(values),
            "avg_success": sum(v[1] for v in values) / len(values),
            "avg_quality": sum(v[2] for v in values) / len(values)
        }


class MetaLearningWorkflow:
    """
    元学习工作流 - 自我进化的工作流系统
    
    整合:
    - 遗传算法优化工作流结构
    - 贝叶斯优化超参数
    - 性能反馈闭环
    """
    
    def __init__(
        self,
        workflow_id: str,
        initial_template: Dict[str, Any] = None
    ):
        self.workflow_id = workflow_id
        self.initial_template = initial_template
        
        # 优化器
        self.genetic_optimizer = GeneticOptimizer(
            population_size=30,
            elite_size=3,
            generations=50
        )
        
        # 贝叶斯优化器
        self.bayesian_optimizer = BayesianOptimizer(
            param_space={
                "temperature": {"type": "float", "low": 0.1, "high": 2.0},
                "max_tokens": {"type": "int", "low": 500, "high": 4000},
                "top_p": {"type": "float", "low": 0.5, "high": 1.0},
            },
            n_iterations=30
        )
        
        # 性能反馈
        self.feedback = PerformanceFeedback()
        
        # 状态
        self.best_genome: Optional[WorkflowGenome] = None
        self.best_params: Optional[Dict] = None
        self.is_evolving = False
        
        # 初始化
        self.genetic_optimizer.initialize_population(initial_template)
    
    async def evolve_structure(
        self,
        fitness_fn: Callable,
        early_stop_fn: Callable = None
    ) -> WorkflowGenome:
        """进化工作流结构"""
        self.is_evolving = True
        
        try:
            self.best_genome = self.genetic_optimizer.run(
                fitness_fn=fitness_fn,
                early_stop_fn=early_stop_fn
            )
            
            return self.best_genome
        finally:
            self.is_evolving = False
    
    async def optimize_hyperparams(
        self,
        evaluate_fn: Callable[[Dict], float]
    ) -> Dict[str, Any]:
        """优化超参数"""
        for _ in range(self.bayesian_optimizer.n_iterations):
            # 建议参数
            params = await self.bayesian_optimizer.suggest()
            
            # 评估
            score = await evaluate_fn(params)
            
            # 记录
            await self.bayesian_optimizer.observe(params, score)
        
        self.best_params = self.bayesian_optimizer.get_best()
        
        return self.best_params
    
    def record_performance(
        self,
        execution_time: float,
        success: bool,
        quality_score: float,
        resource_usage: Dict[str, float] = None
    ):
        """记录性能"""
        self.feedback.record(
            self.workflow_id,
            execution_time,
            success,
            quality_score,
            resource_usage
        )
    
    async def feedback_loop(
        self,
        execution_time: float,
        success: bool,
        quality_score: float
    ) -> Dict[str, Any]:
        """性能反馈闭环"""
        # 记录
        self.record_performance(execution_time, success, quality_score)
        
        # 获取平均
        avg = self.feedback.get_average(self.workflow_id)
        
        # 决策是否需要重新进化
        needs_reevolution = avg["avg_success"] < 0.6
        
        return {
            "metrics": avg,
            "needs_reevolution": needs_reevolution,
            "best_genome": self.best_genome.to_dict() if self.best_genome else None,
            "best_params": self.best_params
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "workflow_id": self.workflow_id,
            "genetic": self.genetic_optimizer.get_stats(),
            "bayesian": self.bayesian_optimizer.get_stats(),
            "best_genome_fitness": self.best_genome.fitness if self.best_genome else None,
            "is_evolving": self.is_evolving
        }


# 全局工作流注册
_workflows: Dict[str, MetaLearningWorkflow] = {}


def get_meta_workflow(
    workflow_id: str,
    template: Dict[str, Any] = None
) -> MetaLearningWorkflow:
    """获取或创建元学习工作流"""
    if workflow_id not in _workflows:
        _workflows[workflow_id] = MetaLearningWorkflow(workflow_id, template)
    return _workflows[workflow_id]
