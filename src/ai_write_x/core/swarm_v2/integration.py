"""
AIWriteX V18.0 - V17/V18 集成模块
将Neural Collective功能集成到现有工作流
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

# 日志适配器
class LogAdapter:
    def __init__(self):
        try:
            import src.ai_write_x.utils.log as _lg
            self.logger = _lg
        except ImportError:
            import logging
            self.logger = logging.getLogger('swarm_integration')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def print_log(self, message, level="info"):
        if hasattr(self.logger, 'print_log'):
            self.logger.print_log(message, level)
        else:
            import logging
            import re
            level_map = {"info": logging.INFO, "warning": logging.WARNING, 
                        "error": logging.ERROR, "success": logging.INFO}
            clean_msg = re.sub(r'[^\x00-\x7F]+', '', message)
            self.logger.log(level_map.get(level, logging.INFO), clean_msg)

lg = LogAdapter()

# Config导入
try:
    from src.ai_write_x.config.config import Config
except ImportError:
    class Config:
        @staticmethod
        def get_instance():
            return Config()
        def get(self, key, default=None):
            return default

# V18 模块
try:
    from .collective_mind import CollectiveMind, IntentionType, SwarmIntention
    from .consensus_protocol import ConsensusProtocol, ProposalType
    from .knowledge_organism import KnowledgeOrganism, KnowledgeType
    from .self_healing import SelfHealing
except ImportError:
    from collective_mind import CollectiveMind, IntentionType, SwarmIntention
    from consensus_protocol import ConsensusProtocol, ProposalType
    from knowledge_organism import KnowledgeOrganism, KnowledgeType
    from self_healing import SelfHealing


class SwarmV18Integration:
    """
    V18 Swarm系统集成器
    
    将V18的自治智能体群体功能集成到V17现有架构中
    提供渐进式升级路径
    """
    
    _instance: Optional['SwarmV18Integration'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.config = Config.get_instance()
        
        # V18组件
        self.collective_mind: Optional[CollectiveMind] = None
        self.consensus: Optional[ConsensusProtocol] = None
        self.knowledge_organism: Optional[KnowledgeOrganism] = None
        self.self_healing: Optional[SelfHealing] = None
        
        # 状态
        self.enabled = self.config.get('swarm_v18_enabled', True)
        self.initialized = False
        
        lg.print_log("🔌 SwarmV18Integration initialized", "info")
    
    async def initialize(self) -> bool:
        """初始化V18组件"""
        if not self.enabled:
            lg.print_log("⏭️ Swarm V18 disabled in config", "warning")
            return False
        
        if self.initialized:
            return True
        
        try:
            lg.print_log("🚀 Initializing Swarm V18 components...", "info")
            
            # 1. 初始化集体意识
            self.collective_mind = CollectiveMind()
            await self.collective_mind.start()
            lg.print_log("✅ CollectiveMind initialized", "success")
            
            # 2. 初始化共识协议
            self.consensus = ConsensusProtocol(self.collective_mind)
            await self.consensus.start()
            lg.print_log("✅ ConsensusProtocol initialized", "success")
            
            # 3. 初始化知识有机体
            self.knowledge_organism = KnowledgeOrganism()
            await self.knowledge_organism.start()
            lg.print_log("✅ KnowledgeOrganism initialized", "success")
            
            # 4. 初始化自修复
            self.self_healing = SelfHealing(self.collective_mind)
            await self.self_healing.start()
            lg.print_log("✅ SelfHealing initialized", "success")
            
            self.initialized = True
            lg.print_log("🎉 Swarm V18 fully initialized", "success")
            return True
            
        except Exception as e:
            lg.print_log(f"❌ Swarm V18 initialization failed: {e}", "error")
            self.enabled = False
            return False
    
    async def shutdown(self):
        """关闭V18组件"""
        if self.collective_mind:
            await self.collective_mind.stop()
            lg.print_log("Swarm V18 shutdown complete", "info")
    
    # ========== 工作流集成接口 ==========
    
    async def register_agent(self, agent_id: str, role: str, 
                            capabilities: List[str]) -> bool:
        """注册智能体到V18群体"""
        if not self.initialized:
            return False
        
        try:
            await self.collective_mind.register_agent(agent_id, role, capabilities)
            return True
        except Exception as e:
            lg.print_log(f"Agent registration failed: {e}", "error")
            return False
    
    async def submit_content_intention(self, topic: str, 
                                       source_agents: List[str],
                                       priority: int = 5) -> Optional[str]:
        """提交内容创作意图"""
        if not self.initialized:
            return None
        
        intention = SwarmIntention(
            type=IntentionType.CONTENT_CREATION,
            source_agents=source_agents,
            payload={"topic": topic, "timestamp": datetime.now().isoformat()},
            priority=priority
        )
        
        return await self.collective_mind.submit_intention(intention)
    
    async def propose_task_allocation(self, task: Dict[str, Any],
                                     proposer: str) -> Optional[str]:
        """提议任务分配"""
        if not self.initialized:
            return None
        
        proposal = await self.consensus.create_proposal(
            ProposalType.TASK_ALLOCATION,
            proposer,
            task,
            f"Task allocation: {task.get('name', 'unknown')}"
        )
        
        return proposal.id
    
    async def store_knowledge(self, content: Dict[str, Any],
                             knowledge_type: KnowledgeType = KnowledgeType.CONCEPT,
                             agent_id: Optional[str] = None) -> Optional[str]:
        """存储知识到有机体系统"""
        if not self.initialized:
            return None
        
        return await self.knowledge_organism.create_organism(
            content, knowledge_type, agent_id
        )
    
    async def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识"""
        if not self.initialized:
            return []
        
        results = self.knowledge_organism.search_knowledge(query, top_k)
        return [
            {
                "organism_id": r.dna.organism_id,
                "type": r.dna.knowledge_type.value,
                "fitness": r.dna.get_fitness_score(),
                "relevance": score
            }
            for r, score in results
        ]
    
    async def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        if not self.initialized or not self.self_healing:
            return {"status": "not_initialized"}
        
        return self.self_healing.get_system_health()
    
    async def get_collective_stats(self) -> Dict[str, Any]:
        """获取群体统计"""
        if not self.initialized:
            return {"status": "not_initialized"}
        
        return {
            "collective": self.collective_mind.get_stats(),
            "consensus": self.consensus.get_stats(),
            "knowledge": self.knowledge_organism.get_population_stats(),
            "health": self.self_healing.get_system_health()
        }
    
    # ========== 与V17的桥接方法 ==========
    
    async def on_article_created(self, article_id: str, topic: str, 
                                 agent_ids: List[str]):
        """文章创建后的回调"""
        if not self.initialized:
            return
        
        # 同步知识
        await self.collective_mind.sync_knowledge(
            "article_creation",
            {"article_id": article_id, "topic": topic, "agents": agent_ids}
        )
    
    async def on_task_completed(self, task_id: str, result: Dict[str, Any],
                                agent_id: str):
        """任务完成后的回调"""
        if not self.initialized:
            return
        
        # 更新智能体状态
        await self.collective_mind.update_agent_state(agent_id, {
            "status": "idle",
            "current_task": None
        })
    
    async def get_recommendations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """基于群体知识获取推荐"""
        if not self.initialized:
            return []
        
        # 查询相关知识
        query = context.get("topic", "")
        results = await self.search_knowledge(query, top_k=3)
        
        return results


# 全局访问点
def get_swarm_v18() -> SwarmV18Integration:
    """获取SwarmV18集成实例"""
    return SwarmV18Integration()


# 便捷函数
async def init_swarm_v18() -> bool:
    """初始化V18群体系统"""
    swarm = get_swarm_v18()
    return await swarm.initialize()


async def shutdown_swarm_v18():
    """关闭V18群体系统"""
    swarm = get_swarm_v18()
    await swarm.shutdown()
