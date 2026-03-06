"""
知识图谱系统
- 实体关系抽取
- 语义网络构建
- 智能检索引擎
- 知识推理能力
"""

import re
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class EntityType(Enum):
    """实体类型"""
    PERSON = "person"           # 人物
    ORGANIZATION = "org"        # 组织机构
    LOCATION = "location"       # 地点
    EVENT = "event"             # 事件
    CONCEPT = "concept"         # 概念
    TIME = "time"               # 时间
    PRODUCT = "product"         # 产品
    TECHNOLOGY = "tech"         # 技术
    TOPIC = "topic"             # 主题


class RelationType(Enum):
    """关系类型"""
    BELONGS_TO = "belongs_to"       # 属于
    LOCATED_AT = "located_at"       # 位于
    OCCURRED_AT = "occurred_at"     # 发生于
    CREATED_BY = "created_by"       # 由...创建
    RELATED_TO = "related_to"       # 相关
    PART_OF = "part_of"             # ...的一部分
    CAUSED_BY = "caused_by"         # 由...导致
    LEADS_TO = "leads_to"           # 导致
    SIMILAR_TO = "similar_to"       # 相似于
    OPPOSITE_OF = "opposite_of"     # 相反于
    USED_FOR = "used_for"           # 用于
    DEVELOPED_BY = "developed_by"   # 由...开发


@dataclass
class Entity:
    """实体"""
    id: str
    name: str
    type: EntityType
    aliases: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    frequency: int = 1
    confidence: float = 1.0


@dataclass
class Relation:
    """关系"""
    source_id: str
    target_id: str
    type: RelationType
    weight: float = 1.0
    evidence: str = ""
    confidence: float = 1.0


@dataclass
class KnowledgeNode:
    """知识节点"""
    entity: Entity
    relations: List[Relation] = field(default_factory=list)
    connections: Set[str] = field(default_factory=set)


class EntityExtractor:
    """实体抽取器"""
    
    # 预定义的实体词典
    ENTITY_DICTS = {
        EntityType.PERSON: [
            "特朗普", "拜登", "普京", "泽连斯基", "习近平", "马克龙", "默克尔",
            "马斯克", "库克", "盖茨", "马云", "马化腾", "任正非", "雷军",
        ],
        EntityType.ORGANIZATION: [
            "美国", "中国", "俄罗斯", "欧盟", "联合国", "北约",
            "谷歌", "苹果", "微软", "亚马逊", "特斯拉", "华为", "阿里巴巴", "腾讯", "字节跳动",
            "OpenAI", "DeepMind", "百度", "小米",
        ],
        EntityType.LOCATION: [
            "北京", "上海", "深圳", "广州", "杭州", "纽约", "华盛顿", "伦敦", "巴黎",
            "东京", "首尔", "新加坡", "香港", "台湾", "乌克兰", "中东",
        ],
        EntityType.TECHNOLOGY: [
            "人工智能", "机器学习", "深度学习", "神经网络", "GPT", "ChatGPT",
            "区块链", "量子计算", "5G", "云计算", "大数据", "物联网",
            "自动驾驶", "元宇宙", "VR", "AR", "芯片", "半导体",
        ],
        EntityType.EVENT: [
            "疫情", "奥运会", "世界杯", "大选", "贸易战", "制裁", "冲突",
            "发布会", "峰会", "论坛",
        ],
        EntityType.CONCEPT: [
            "经济", "政治", "文化", "科技", "教育", "医疗", "环保",
            "创新", "发展", "改革", "全球化", "数字化",
        ],
    }
    
    # 实体识别模式
    ENTITY_PATTERNS = {
        EntityType.TIME: [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}年\d{1,2}月',
            r'\d{1,2}月\d{1,2}日',
            r'去年', r'今年', r'明年',
            r'上个月', r'这个月', r'下个月',
            r'昨天', r'今天', r'明天',
        ],
        EntityType.PRODUCT: [
            r'iPhone\s*\d+',
            r'iPad\s*\w*',
            r'Galaxy\s*\w+',
            r'华为\w+',
            r'小米\w+',
        ],
    }
    
    def __init__(self):
        self.entity_index: Dict[str, EntityType] = {}
        self._build_index()
    
    def _build_index(self):
        """构建实体索引"""
        for entity_type, entities in self.ENTITY_DICTS.items():
            for entity in entities:
                self.entity_index[entity.lower()] = entity_type
    
    def extract(self, text: str) -> List[Entity]:
        """从文本中提取实体"""
        entities = []
        found_entities = set()
        
        # 基于词典匹配
        for name, entity_type in self.entity_index.items():
            if name in text.lower() and name not in found_entities:
                entity = Entity(
                    id=self._generate_id(name, entity_type),
                    name=name,
                    type=entity_type,
                )
                entities.append(entity)
                found_entities.add(name)
        
        # 基于模式匹配
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if match not in found_entities:
                        entity = Entity(
                            id=self._generate_id(match, entity_type),
                            name=match,
                            type=entity_type,
                        )
                        entities.append(entity)
                        found_entities.add(match)
        
        return entities
    
    def _generate_id(self, name: str, entity_type: EntityType) -> str:
        """生成实体ID"""
        return f"{entity_type.value}_{hash(name) % 10000}"


class RelationExtractor:
    """关系抽取器"""
    
    # 关系模式
    RELATION_PATTERNS = {
        RelationType.BELONGS_TO: [
            r'(.+?)属于(.+?)',
            r'(.+?)是(.+?)的',
        ],
        RelationType.LOCATED_AT: [
            r'(.+?)位于(.+?)',
            r'(.+?)在(.+?)(?:开设|设立|建立)',
            r'(.+?)总部在(.+?)',
        ],
        RelationType.CREATED_BY: [
            r'(.+?)由(.+?)创建',
            r'(.+?)由(.+?)发明',
            r'(.+?)创始人(.+?)',
        ],
        RelationType.DEVELOPED_BY: [
            r'(.+?)由(.+?)开发',
            r'(.+?)研发的(.+?)',
        ],
        RelationType.CAUSED_BY: [
            r'(.+?)导致(.+?)',
            r'(.+?)造成(.+?)',
            r'(.+?)引起(.+?)',
        ],
        RelationType.RELATED_TO: [
            r'(.+?)与(.+?)相关',
            r'(.+?)和(.+?)有关',
            r'(.+?)涉及(.+?)',
        ],
    }
    
    def extract(self, text: str, entities: List[Entity]) -> List[Relation]:
        """从文本中提取关系"""
        relations = []
        entity_dict = {e.name.lower(): e for e in entities}
        
        for relation_type, patterns in self.RELATION_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if len(match) >= 2:
                        source_name = match[0].strip()
                        target_name = match[1].strip()
                        
                        source = entity_dict.get(source_name.lower())
                        target = entity_dict.get(target_name.lower())
                        
                        if source and target:
                            relation = Relation(
                                source_id=source.id,
                                target_id=target.id,
                                type=relation_type,
                                evidence=match[0] + " " + pattern.split('(.+?)')[1] + " " + match[1],
                            )
                            relations.append(relation)
        
        return relations


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
        
        # V14.6: 持久化路径
        from src.ai_write_x.utils.path_manager import PathManager
        self.persist_path = PathManager.get_base_dir() / "knowledge_graph.json"
        
        # 初始化时尝试从本地加载
        self.load_from_file()
    
    def save_to_file(self):
        """V14.6: 将知识图谱持久化到本地文件"""
        try:
            data = self.export_graph()
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # from src.ai_write_x.utils import log
            # log.print_log(f"💾 知识图谱已持久化至 {self.persist_path}", "success")
        except Exception as e:
            from src.ai_write_x.utils import log
            log.print_log(f"知识图谱持久化失败: {e}", "warning")

    def load_from_file(self):
        """V14.6: 从本地文件加载知识图谱"""
        if not self.persist_path.exists():
            return
            
        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 导入实体
            for node_data in data.get("nodes", []):
                entity = Entity(
                    id=node_data["id"],
                    name=node_data["name"],
                    type=EntityType(node_data["type"]),
                    frequency=node_data.get("frequency", 1),
                    confidence=node_data.get("confidence", 1.0)
                )
                self.nodes[entity.id] = KnowledgeNode(entity=entity)
            
            # 导入关系
            for edge_data in data.get("edges", []):
                source_id = edge_data["source"]
                target_id = edge_data["target"]
                if source_id in self.nodes:
                    relation = Relation(
                        source_id=source_id,
                        target_id=target_id,
                        type=RelationType(edge_data["type"]),
                        weight=edge_data.get("weight", 1.0),
                        evidence=edge_data.get("evidence", "")
                    )
                    self.nodes[source_id].relations.append(relation)
                    self.nodes[source_id].connections.add(target_id)
            
            from src.ai_write_x.utils import log
            log.print_log(f"🧠 已从本地加载知识图谱：{len(self.nodes)} 个实体", "success")
        except Exception as e:
            from src.ai_write_x.utils import log
            log.print_log(f"加载知识图谱失败: {e}", "warning")

    def build_from_text(self, text: str) -> Dict[str, Any]:
        """从文本构建知识图谱"""
        # 提取实体
        entities = self.entity_extractor.extract(text)
        
        # 提取关系
        relations = self.relation_extractor.extract(text, entities)
        
        # 构建节点
        for entity in entities:
            if entity.id not in self.nodes:
                self.nodes[entity.id] = KnowledgeNode(entity=entity)
            else:
                self.nodes[entity.id].entity.frequency += 1
        
        # 添加关系
        for relation in relations:
            if relation.source_id in self.nodes:
                self.nodes[relation.source_id].relations.append(relation)
                self.nodes[relation.source_id].connections.add(relation.target_id)
        
        # V14.6: 每次构建后自动持久化
        self.save_to_file()
        
        return {
            "entities": [self._entity_to_dict(e) for e in entities],
            "relations": [self._relation_to_dict(r) for r in relations],
            "stats": {
                "entity_count": len(entities),
                "relation_count": len(relations),
                "node_count": len(self.nodes),
            }
        }
    
    def _entity_to_dict(self, entity: Entity) -> Dict:
        """实体转字典"""
        return {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type.value,
            "frequency": entity.frequency,
            "confidence": entity.confidence,
        }
    
    def _relation_to_dict(self, relation: Relation) -> Dict:
        """关系转字典"""
        return {
            "source": relation.source_id,
            "target": relation.target_id,
            "type": relation.type.value,
            "weight": relation.weight,
            "evidence": relation.evidence,
        }
    
    def get_entity_network(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """获取实体的关系网络"""
        if entity_id not in self.nodes:
            return {"nodes": [], "edges": []}
        
        nodes = []
        edges = []
        visited = set()
        
        def traverse(node_id: str, current_depth: int):
            if current_depth > depth or node_id in visited:
                return
            
            visited.add(node_id)
            node = self.nodes.get(node_id)
            
            if node:
                nodes.append(self._entity_to_dict(node.entity))
                
                for relation in node.relations:
                    edges.append(self._relation_to_dict(relation))
                    traverse(relation.target_id, current_depth + 1)
        
        traverse(entity_id, 0)
        
        return {"nodes": nodes, "edges": edges}
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """搜索实体"""
        results = []
        query_lower = query.lower()
        
        for node in self.nodes.values():
            if query_lower in node.entity.name.lower():
                results.append({
                    "entity": self._entity_to_dict(node.entity),
                    "connections": len(node.connections),
                })
        
        # 按连接数排序
        results.sort(key=lambda x: x["connections"], reverse=True)
        
        return results[:10]
    
    def get_top_entities(self, entity_type: EntityType = None, limit: int = 10) -> List[Dict]:
        """获取热门实体"""
        entities = []
        
        for node in self.nodes.values():
            if entity_type is None or node.entity.type == entity_type:
                entities.append({
                    "entity": self._entity_to_dict(node.entity),
                    "connections": len(node.connections),
                })
        
        # 按频率和连接数排序
        entities.sort(key=lambda x: (x["entity"]["frequency"], x["connections"]), reverse=True)
        
        return entities[:limit]
    
    def infer_relations(self, entity_id: str) -> List[Dict[str, Any]]:
        """推理可能的关系"""
        inferred = []
        
        if entity_id not in self.nodes:
            return inferred
        
        node = self.nodes[entity_id]
        
        # 基于传递性推理
        for relation in node.relations:
            if relation.target_id in self.nodes:
                target_node = self.nodes[relation.target_id]
                
                for target_relation in target_node.relations:
                    if target_relation.target_id != entity_id:
                        inferred.append({
                            "type": "inferred_transitive",
                            "path": [
                                node.entity.name,
                                target_node.entity.name,
                                self.nodes.get(target_relation.target_id, KnowledgeNode(Entity("", "", EntityType.CONCEPT))).entity.name,
                            ],
                            "confidence": 0.6,
                        })
        
        return inferred[:5]
    
    def export_graph(self) -> Dict[str, Any]:
        """导出知识图谱"""
        return {
            "nodes": [self._entity_to_dict(n.entity) for n in self.nodes.values()],
            "edges": [
                self._relation_to_dict(r)
                for n in self.nodes.values()
                for r in n.relations
            ],
            "stats": {
                "total_entities": len(self.nodes),
                "total_relations": sum(len(n.relations) for n in self.nodes.values()),
                "entity_types": self._count_entity_types(),
            }
        }
    
    def _count_entity_types(self) -> Dict[str, int]:
        """统计实体类型"""
        counts = defaultdict(int)
        for node in self.nodes.values():
            counts[node.entity.type.value] += 1
        return dict(counts)

    def discover_emerging_trends(self, window_size: int = 50) -> List[Dict[str, Any]]:
        """
        V7.0: 发现新兴趋势
        分析最近加入图谱的实体，识别其关联度突然增高的簇。
        """
        all_entities = self.get_top_entities(limit=window_size)
        trends = []
        for item in all_entities:
            entity = item["entity"]
            connections = item["connections"]
            # 逻辑：高频词且具有跨域连接 (与超过3种不同类型的实体相连)
            connected_types = {self.nodes[conn_id].entity.type for conn_id in self.nodes[entity["id"]].connections if conn_id in self.nodes}
            if len(connected_types) >= 2 or connections > 5:
                trends.append({
                    "topic": entity["name"],
                    "significance": connections * entity["frequency"],
                    "domain_coverage": [t.value for t in connected_types]
                })
        
        trends.sort(key=lambda x: x["significance"], reverse=True)
        return trends[:5]

    def analyze_semantic_gaps(self, base_topics: List[str]) -> List[str]:
        """
        V7.0: 语义空白分析
        基于现有主题，通过图谱推理寻找未被充分探讨的关联路径。
        """
        suggestions = []
        for topic in base_topics:
            results = self.search(topic)
            if not results: continue
            
            entity_id = results[0]["entity"]["id"]
            # 获取二度人脉中的高频实体但在base_topics中没出现的
            network = self.get_entity_network(entity_id, depth=2)
            for node in network["nodes"]:
                if node["name"] not in base_topics and node["frequency"] > 1:
                    suggestions.append(node["name"])
        
        return list(set(suggestions))[:5]
    
    def clear(self):
        """清空图谱"""
        self.nodes.clear()
        # V14.6: 同时删除持久化文件
        if self.persist_path.exists():
            try:
                os.remove(self.persist_path)
            except:
                pass


class SemanticAnalyzer:
    """语义分析器"""
    
    def __init__(self):
        self.knowledge_graph = KnowledgeGraph()
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """分析文本语义"""
        # 构建知识图谱
        graph_data = self.knowledge_graph.build_from_text(text)
        
        # 提取主题
        topics = self._extract_topics(text)
        
        # 分析语义结构
        structure = self._analyze_structure(text)
        
        return {
            "graph": graph_data,
            "topics": topics,
            "structure": structure,
        }
    
    def _extract_topics(self, text: str) -> List[str]:
        """提取主题"""
        # 基于实体频率提取主题
        top_entities = self.knowledge_graph.get_top_entities(limit=5)
        topics = []
        
        for item in top_entities:
            entity = item["entity"]
            if entity["type"] in ["topic", "concept", "tech"]:
                topics.append(entity["name"])
        
        return topics
    
    def _analyze_structure(self, text: str) -> Dict[str, Any]:
        """分析语义结构"""
        sentences = re.split(r'[。！？\n]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return {
            "sentence_count": len(sentences),
            "avg_sentence_length": sum(len(s) for s in sentences) / len(sentences) if sentences else 0,
            "has_question": any('?' in s or '？' in s for s in sentences),
            "has_exclamation": any('!' in s or '！' in s for s in sentences),
        }
    
    def get_entity_network(self, entity_name: str) -> Dict[str, Any]:
        """获取实体网络"""
        # 查找实体ID
        for node in self.knowledge_graph.nodes.values():
            if node.entity.name.lower() == entity_name.lower():
                return self.knowledge_graph.get_entity_network(node.entity.id)
        
        return {"nodes": [], "edges": []}


# 全局实例
_semantic_analyzer = None


def get_semantic_analyzer() -> SemanticAnalyzer:
    """获取语义分析器实例"""
    global _semantic_analyzer
    if _semantic_analyzer is None:
        _semantic_analyzer = SemanticAnalyzer()
    return _semantic_analyzer
