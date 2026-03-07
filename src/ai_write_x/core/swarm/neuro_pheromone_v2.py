"""
神经形态信息素协议 V2 (Neuro-Morphic Pheromone Protocol V2)
类脑计算启发的信息素系统 - 模拟生物神经元的脉冲传递

核心特性:
1. 脉冲神经网络编码 - 使用时空脉冲模式编码信息
2. Hebbian学习机制 - 突触可塑性，"一起放电的神经元连接加强"
3. 多模态信息素 - 支持视觉/语义/时序三种模态
4. 全局同步振荡 - 模拟脑波的同步机制
"""
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import json
import math
import random
import numpy as np

from src.ai_write_x.utils import log


class NeurotransmitterType(str, Enum):
    """神经递质类型"""
    EXCITATORY = "excitatory"    # 兴奋性 - 促进接收神经元放电
    INHIBITORY = "inhibitory"    # 抑制性 - 抑制接收神经元放电
    MODULATORY = "modulatory"    # 调节性 - 调节突触可塑性


class SpikePattern:
    """
    脉冲模式 - 编码信息的时空脉冲序列
    
    使用二进制脉冲序列表示信息:
    - 时间维度: 脉冲发生的时刻
    - 空间维度: 不同神经元的放电模式
    """
    
    def __init__(
        self,
        pattern_id: str = None,
        spikes: List[Tuple[float, int]] = None,  # (time, neuron_id)
        dimension: int = 8,
        encoding: str = "temporal"
    ):
        self.id = pattern_id or str(uuid.uuid4())[:8]
        self.spikes = spikes or []  # list of (timestamp, neuron_id)
        self.dimension = dimension
        self.encoding = encoding
        self.created_at = datetime.now()
    
    def add_spike(self, neuron_id: int, timestamp: float = None):
        """添加一个脉冲"""
        ts = timestamp or (datetime.now() - self.created_at).total_seconds()
        self.spikes.append((ts, neuron_id % self.dimension))
    
    def encode_data(self, data: Any) -> 'SpikePattern':
        """将任意数据编码为脉冲模式"""
        # 简单实现: 哈希编码
        data_str = json.dumps(data, sort_keys=True, default=str)
        hash_val = hash(data_str) % (2**32)
        
        for i in range(min(self.dimension, 8)):
            if (hash_val >> i) & 1:
                self.add_spike(i)
        
        return self
    
    def compute_similarity(self, other: 'SpikePattern') -> float:
        """计算两个脉冲模式的相似度 (0-1)"""
        if not self.spikes or not other.spikes:
            return 0.0
        
        # 使用时间窗口对齐计算相似度
        my_neurons = set(n for _, n in self.spikes)
        other_neurons = set(n for _, n in other.spikes)
        
        intersection = len(my_neurons & other_neurons)
        union = len(my_neurons | other_neurons)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def to_tensor(self) -> np.ndarray:
        """转换为numpy张量 (用于学习)"""
        tensor = np.zeros((self.dimension, 100))  # 100个时间步
        
        for ts, nid in self.spikes:
            t_idx = min(int(ts * 10), 99)  # 10Hz采样
            tensor[nid, t_idx] = 1.0
        
        return tensor
    
    def __repr__(self):
        return f"SpikePattern(id={self.id}, spikes={len(self.spikes)}, dim={self.dimension})"


class Synapse:
    """
    突触 - 连接两个神经元
    
    包含:
    - 突触权重: 连接的强度
    - 可塑性率: 学习速度
    - 上次更新时间: 用于遗忘
    """
    
    def __init__(
        self,
        pre_neuron_id: str,
        post_neuron_id: str,
        initial_weight: float = 0.5,
        plasticity_rate: float = 0.01
    ):
        self.pre_neuron_id = pre_neuron_id
        self.post_neuron_id = post_neuron_id
        self.weight = initial_weight
        self.plasticity_rate = plasticity_rate
        self.last_update = datetime.now()
        self.spike_history: List[bool] = []  # 记录双方放电历史
    
    def hebbian_update(self, pre_fired: bool, post_fired: bool):
        """
        Hebbian学习规则更新权重
        
        核心思想: "一起放电的神经元连接加强"
        - 如果前突触和后突触都放电: 权重增加
        - 如果只有前突触放电: 权重不变
        - 如果只有后突触放电: 权重减少(anti-Hebbian)
        - 都不放电: 权重缓慢衰减
        """
        if pre_fired and post_fired:
            # Hebbian强化: "一起放电，加强连接"
            self.weight = min(1.0, self.weight + self.plasticity_rate)
        elif pre_fired and not post_fired:
            # 轻微衰减
            self.weight = max(0.0, self.weight - self.plasticity_rate * 0.1)
        elif not pre_fired and post_fired:
            # Anti-Hebbian
            self.weight = max(0.0, self.weight - self.plasticity_rate * 0.5)
        else:
            # 遗忘: 长时间不一起放电则衰减
            self.weight = max(0.0, self.weight - self.plasticity_rate * 0.01)
        
        self.last_update = datetime.now()
    
    def decay(self, decay_rate: float = 0.001):
        """时间衰减 - 模拟神经递质耗尽"""
        self.weight = max(0.0, self.weight - decay_rate)


class Neuron:
    """
    神经元 - 信息处理单元
    
    特性:
    - 膜电位: 累积输入
    - 阈值: 超过阈值则放电
    - 不应期: 放电后短暂休息
    """
    
    def __init__(
        self,
        neuron_id: str,
        threshold: float = 1.0,
        membrane_decay: float = 0.9,
        refractory_period: float = 0.05  # 50ms不应期
    ):
        self.neuron_id = neuron_id
        self.threshold = threshold
        self.membrane_potential = 0.0
        self.membrane_decay = membrane_decay
        self.refractory_period = refractory_period
        self.last_spike_time: Optional[datetime] = None
        self.spike_count = 0
    
    def receive_input(self, signal_strength: float, neurotransmitter: NeurotransmitterType):
        """接收输入信号"""
        # 检查不应期
        if self.last_spike_time:
            elapsed = (datetime.now() - self.last_spike_time).total_seconds()
            if elapsed < self.refractory_period:
                return False  # 不应期内不响应
        
        # 根据神经递质类型调整信号
        if neurotransmitter == NeurotransmitterType.EXCITATORY:
            self.membrane_potential += signal_strength
        elif neurotransmitter == NeurotransmitterType.INHIBITORY:
            self.membrane_potential -= signal_strength
        elif neurotransmitter == NeurotransmitterType.MODULATORY:
            # 调节性神经递质不直接影响电位，但可能改变阈值
            self.threshold *= (1 + signal_strength * 0.1)
        
        return True
    
    def tick(self) -> bool:
        """神经元更新tick - 检查是否放电"""
        # 检查不应期
        if self.last_spike_time:
            elapsed = (datetime.now() - self.last_spike_time).total_seconds()
            if elapsed < self.refractory_period:
                return False
        
        # 膜电位衰减
        self.membrane_potential *= self.membrane_decay
        
        # 检查阈值
        if self.membrane_potential >= self.threshold:
            self.spike()
            return True
        
        return False
    
    def spike(self):
        """神经元放电"""
        self.membrane_potential = 0.0
        self.last_spike_time = datetime.now()
        self.spike_count += 1
    
    def reset(self):
        """重置神经元状态"""
        self.membrane_potential = 0.0
        self.last_spike_time = None


class NeuralPheromone:
    """
    神经形态信息素 - 模拟生物神经元的脉冲传递
    
    特性:
    - spike_pattern: 脉冲模式编码信息
    - synaptic_weight: 突触权重(学习得到)
    - neurotransmitter_type: 神经递质类型
    - plasticity_rate: 可塑性率(Hebbian学习)
    """
    
    def __init__(
        self,
        p_type: str,
        spike_pattern: SpikePattern = None,
        synaptic_weight: float = 0.5,
        neurotransmitter_type: NeurotransmitterType = NeurotransmitterType.EXCITATORY,
        plasticity_rate: float = 0.01,
        source_id: str = None,
        target_id: str = None,
        ttl: float = 60.0
    ):
        self.id = str(uuid.uuid4())
        self.type = p_type
        self.spike_pattern = spike_pattern or SpikePattern()
        self.synaptic_weight = synaptic_weight
        self.neurotransmitter_type = neurotransmitter_type
        self.plasticity_rate = plasticity_rate
        self.source_id = source_id
        self.target_id = target_id
        self.created_at = datetime.now()
        self.ttl = ttl
        
        # 学习历史
        self.activation_history: List[bool] = []
    
    @property
    def is_expired(self) -> bool:
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    @property
    def effective_strength(self) -> float:
        """有效强度 = 突触权重 * 脉冲强度"""
        age = (datetime.now() - self.created_at).total_seconds()
        decay = math.exp(-0.05 * age)
        return self.synaptic_weight * decay * (len(self.spike_pattern.spikes) / max(1, self.spike_pattern.dimension))
    
    def record_activation(self, activated: bool):
        """记录激活状态用于学习"""
        self.activation_history.append(activated)
        if len(self.activation_history) > 100:
            self.activation_history.pop(0)
    
    def learn_from_feedback(self, success: bool):
        """基于反馈学习调整权重"""
        # 成功则增强权重，失败则减弱
        delta = self.plasticity_rate * (1.0 if success else -0.5)
        self.synaptic_weight = min(1.0, max(0.0, self.synaptic_weight + delta))


class NeuroPheromoneSpace:
    """
    神经形态信息素空间
    
    管理整个蜂群的神经形态信息素:
    - 神经元网络
    - 突触连接
    - 全局同步振荡
    """
    
    def __init__(
        self,
        neuron_count: int = 64,
        decay_rate: float = 0.02,
        sync_frequency: float = 10.0  # 同步振荡频率 (Hz)
    ):
        self.neuron_count = neuron_count
        self.decay_rate = decay_rate
        self.sync_frequency = sync_frequency
        
        # 神经元网络
        self.neurons: Dict[str, Neuron] = {}
        for i in range(neuron_count):
            nid = f"neuron_{i}"
            self.neurons[nid] = Neuron(nid)
        
        # 突触连接矩阵
        self.synapses: Dict[Tuple[str, str], Synapse] = {}
        
        # 信息素存储
        self.pheromones: Dict[str, NeuralPheromone] = {}
        
        # 全局同步
        self.sync_phase = 0.0
        self.last_sync_time = datetime.now()
        
        # 统计
        self.total_spikes = 0
        
        self._lock = asyncio.Lock()
    
    async def emit(
        self,
        p_type: str,
        data: Any = None,
        synaptic_weight: float = 0.5,
        neurotransmitter: NeurotransmitterType = NeurotransmitterType.EXCITATORY,
        plasticity_rate: float = 0.01,
        source_id: str = None,
        target_id: str = None,
        ttl: float = 60.0
    ) -> str:
        """发射神经形态信息素"""
        async with self._lock:
            # 创建脉冲模式
            pattern = SpikePattern(dimension=self.neuron_count)
            if data:
                pattern.encode_data(data)
            
            pheromone = NeuralPheromone(
                p_type=p_type,
                spike_pattern=pattern,
                synaptic_weight=synaptic_weight,
                neurotransmitter_type=neurotransmitter,
                plasticity_rate=plasticity_rate,
                source_id=source_id,
                target_id=target_id,
                ttl=ttl
            )
            
            self.pheromones[pheromone.id] = pheromone
            
            # 激活相关神经元
            await self._activate_neurons_for_pheromone(pheromone)
            
            log.print_log(
                f"[神经信息素] {source_id or 'system'} 发射 {p_type} "
                f"权重={synaptic_weight:.2f} 脉冲数={len(pattern.spikes)}",
                "debug"
            )
            
            return pheromone.id
    
    async def _activate_neurons_for_pheromone(self, pheromone: NeuralPheromone):
        """根据信息素激活神经元"""
        for ts, nid in pheromone.spike_pattern.spikes:
            neuron_key = f"neuron_{nid}"
            if neuron_key in self.neurons:
                neuron = self.neurons[neuron_key]
                neuron.receive_input(
                    pheromone.synaptic_weight,
                    pheromone.neurotransmitter_type
                )
    
    async def sense(
        self,
        agent_id: str,
        p_types: List[str] = None,
        threshold: float = 0.3
    ) -> List[NeuralPheromone]:
        """感知信息素"""
        async with self._lock:
            p_types = p_types or []
            
            sensed = []
            for p in self.pheromones.values():
                if p.is_expired:
                    continue
                if p_types and p.type not in p_types:
                    continue
                
                if p.effective_strength >= threshold:
                    sensed.append(p)
                    p.record_activation(True)
                else:
                    p.record_activation(False)
            
            return sensed
    
    async def tick(self):
        """更新神经元网络"""
        async with self._lock:
            spike_count = 0
            
            for neuron in self.neurons.values():
                if neuron.tick():
                    spike_count += 1
            
            self.total_spikes += spike_count
            
            # Hebbian学习: 更新突触
            await self._hebbian_learning()
            
            # 全局同步振荡
            await self._sync_oscillation()
            
            # 衰减
            await self._decay()
    
    async def _hebbian_learning(self):
        """Hebbian学习 - 强化同时放电的连接"""
        # 简化实现: 基于最近脉冲更新突触权重
        recent_firings = {
            nid: n.spike_count for nid, n in self.neurons.items()
        }
        
        for (pre, post), synapse in self.synapses.items():
            pre_fired = recent_firings.get(pre, 0) > 0
            post_fired = recent_firings.get(post, 0) > 0
            synapse.hebbian_update(pre_fired, post_fired)
    
    async def _sync_oscillation(self):
        """全局同步振荡 - 模拟脑波"""
        now = datetime.now()
        elapsed = (now - self.last_sync_time).total_seconds()
        
        # 更新同步相位
        self.sync_phase = (self.sync_phase + elapsed * self.sync_frequency) % (2 * math.pi)
        
        # 在振荡峰值时增强信息素
        if abs(math.sin(self.sync_phase)) > 0.9:
            for p in self.pheromones.values():
                p.synaptic_weight = min(1.0, p.synaptic_weight * 1.05)
        
        self.last_sync_time = now
    
    async def _decay(self):
        """衰减过期信息素"""
        expired = [pid for pid, p in self.pheromones.items() if p.is_expired]
        for pid in expired:
            del self.pheromones[pid]
        
        # 突触衰减
        for synapse in self.synapses.values():
            synapse.decay()
    
    async def create_synapse(
        self,
        pre_neuron_id: str,
        post_neuron_id: str,
        initial_weight: float = 0.5
    ) -> Synapse:
        """创建新的突触连接"""
        async with self._lock:
            key = (pre_neuron_id, post_neuron_id)
            if key not in self.synapses:
                synapse = Synapse(pre_neuron_id, post_neuron_id, initial_weight)
                self.synapses[key] = synapse
                return synapse
            return self.synapses[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "neuron_count": len(self.neurons),
            "synapse_count": len(self.synapses),
            "pheromone_count": len(self.pheromones),
            "total_spikes": self.total_spikes,
            "sync_phase": round(self.sync_phase, 3),
            "sync_strength": round(abs(math.sin(self.sync_phase)), 3)
        }


class NeuroPheromoneComm:
    """
    神经形态信息素通信协议 V2
    
    特性:
    - 脉冲神经网络编码
    - Hebbian学习机制
    - 多模态信息素
    - 全局同步振荡
    """
    
    def __init__(self):
        self.neuro_space = NeuroPheromoneSpace()
        self._running = False
        self._tick_task: Optional[asyncio.Task] = None
        
        # 学习参数
        self.learning_rate = 0.01
        self.consolidation_threshold = 0.7
    
    async def start(self):
        """启动神经形态通信"""
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop())
        
        # 初始化一些突触连接
        for i in range(32):
            pre = f"neuron_{i % 32}"
            post = f"neuron_{(i + 1) % 32}"
            await self.neuro_space.create_synapse(pre, post, 0.3 + random.random() * 0.4)
        
        log.print_log("🧠 神经形态信息素协议 V2 已启动", "info")
    
    async def stop(self):
        """停止通信"""
        self._running = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        log.print_log("🧠 神经形态信息素协议 V2 已停止", "info")
    
    async def _tick_loop(self):
        """主循环 - 50Hz更新"""
        while self._running:
            try:
                await asyncio.sleep(0.02)  # 50Hz
                await self.neuro_space.tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.print_log(f"神经形态Tick错误: {e}", "error")
    
    async def emit_semantic(
        self,
        source_id: str,
        semantic_data: Dict[str, Any],
        strength: float = 0.8
    ) -> str:
        """发射语义信息素"""
        return await self.neuro_space.emit(
            p_type="semantic",
            data=semantic_data,
            synaptic_weight=strength,
            neurotransmitter=NeurotransmitterType.EXCITATORY,
            source_id=source_id,
            ttl=120.0
        )
    
    async def emit_temporal(
        self,
        source_id: str,
        temporal_data: List[Dict],
        strength: float = 0.7
    ) -> str:
        """发射时序信息素"""
        return await self.neuro_space.emit(
            p_type="temporal",
            data={"sequence": temporal_data},
            synaptic_weight=strength,
            neurotransmitter=NeurotransmitterType.MODULATORY,
            source_id=source_id,
            ttl=60.0
        )
    
    async def emit_visual(
        self,
        source_id: str,
        visual_data: Dict[str, Any],
        strength: float = 0.9
    ) -> str:
        """发射视觉信息素"""
        return await self.neuro_space.emit(
            p_type="visual",
            data=visual_data,
            synaptic_weight=strength,
            neurotransmitter=NeurotransmitterType.EXCITATORY,
            source_id=source_id,
            ttl=30.0
        )
    
    async def sense_all(
        self,
        agent_id: str,
        threshold: float = 0.3
    ) -> List[NeuralPheromone]:
        """感知所有可用信息素"""
        return await self.neuro_space.sense(agent_id, threshold=threshold)
    
    async def learn_from_outcome(
        self,
        pheromone_id: str,
        success: bool
    ):
        """从结果学习 - 强化或减弱信息素"""
        async with self.neuro_space._lock:
            if pheromone_id in self.neuro_space.pheromones:
                p = self.neuro_space.pheromones[pheromone_id]
                p.learn_from_feedback(success)
                log.print_log(
                    f"[学习] {pheromone_id[:8]} -> {'强化' if success else '减弱'} "
                    f"新权重={p.synaptic_weight:.3f}",
                    "debug"
                )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取通信统计"""
        neuro_stats = self.neuro_space.get_stats()
        
        # 按类型统计信息素
        by_type = defaultdict(int)
        for p in self.neuro_space.pheromones.values():
            by_type[p.type] += 1
        
        return {
            "neuro_space": neuro_stats,
            "pheromones_by_type": dict(by_type),
            "running": self._running
        }


# 全局实例
_global_neuro_comm: Optional[NeuroPheromoneComm] = None


def get_neuro_pheromone_comm() -> NeuroPheromoneComm:
    """获取全局神经形态信息素通信实例"""
    global _global_neuro_comm
    if _global_neuro_comm is None:
        _global_neuro_comm = NeuroPheromoneComm()
    return _global_neuro_comm
