"""
跨模态推理引擎
├── 文本→视觉推理: 从描述生成视觉概念
├── 视觉→文本推理: 图像理解和描述
├── 跨模态类比: 不同模态间的相似性推理
├── 模态一致性检查: 确保多模态输出协调
└── 模态选择性融合: 根据任务动态加权
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from collections import defaultdict
import threading
import json


class ModalType(Enum):
    """模态类型"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED = "structured"  # 表格、JSON等


class ReasoningDirection(Enum):
    """推理方向"""
    TEXT_TO_VISUAL = "text_to_visual"    # 文本→视觉
    VISUAL_TO_TEXT = "visual_to_text"    # 视觉→文本
    CROSS_MODAL = "cross_modal"          # 跨模态
    MULTI_FUSION = "multi_fusion"        # 多模态融合


class ConsistencyStatus(Enum):
    """一致性状态"""
    CONSISTENT = "consistent"
    PARTIAL = "partial"
    INCONSISTENT = "inconsistent"
    UNKNOWN = "unknown"


@dataclass
class VisualConcept:
    """视觉概念"""
    id: str
    objects: List[Dict[str, Any]]      # 检测到的对象
    scenes: List[str]                  # 场景描述
    colors: List[str]                  # 颜色
    spatial_relations: List[Dict]     # 空间关系
    attributes: Dict[str, Any]         # 属性
    confidence: float = 1.0


@dataclass
class TextRepresentation:
    """文本表示"""
    id: str
    content: str
    entities: List[Dict[str, Any]]      # 实体
    relations: List[Dict[str, Any]]    # 关系
    sentiment: float = 0.0             # 情感倾向
    keywords: List[str] = field(default_factory=list)


@dataclass
class CrossModalMapping:
    """跨模态映射"""
    id: str
    source_modal: ModalType
    target_modal: ModalType
    mappings: Dict[str, Any]            # 映射关系
    similarity: float                  # 相似度
    confidence: float                  # 置信度
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FusionResult:
    """融合结果"""
    content: Any
    modality_weights: Dict[ModalType, float]
    consistency: ConsistencyStatus
    reasoning_chain: List[Dict[str, Any]]
    confidence: float


@dataclass
class AnalogyResult:
    """类比结果"""
    source: Any
    target: Any
    similarity: float
    mappings: List[Dict[str, Any]]
    reasoning: str


class MultiModalReasoning:
    """
    跨模态推理引擎

    实现多模态信息的理解、推理和生成:
    1. 文本→视觉: 从文本描述生成视觉概念
    2. 视觉→文本: 图像理解与描述
    3. 跨模态类比: 模态间相似性推理
    4. 模态一致性: 多模态输出协调性检查
    5. 模态融合: 动态加权融合多模态信息
    """

    # 相似度阈值
    HIGH_SIMILARITY = 0.8
    MEDIUM_SIMILARITY = 0.5
    LOW_SIMILARITY = 0.3

    # 一致性阈值
    CONSISTENT_THRESHOLD = 0.8
    PARTIAL_THRESHOLD = 0.5

    def __init__(
        self,
        enable_consistency_check: bool = True,
        enable_adaptive_fusion: bool = True,
        similarity_threshold: float = 0.6
    ):
        """
        初始化跨模态推理引擎

        Args:
            enable_consistency_check: 启用一致性检查
            enable_adaptive_fusion: 启用自适应融合
            similarity_threshold: 相似度阈值
        """
        self.enable_consistency_check = enable_consistency_check
        self.enable_adaptive_fusion = enable_adaptive_fusion
        self.similarity_threshold = similarity_threshold

        # 模态处理器
        self._modal_processors: Dict[ModalType, Callable] = {}

        # 历史记录
        self._mapping_history: List[CrossModalMapping] = []
        self._fusion_history: List[FusionResult] = []
        self._analogy_history: List[AnalogyResult] = []

        # 模态嵌入缓存
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # 线程安全
        self._lock = threading.RLock()

    # ==================== 文本→视觉推理 ====================

    def text_to_visual(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> VisualConcept:
        """
        文本→视觉推理

        Args:
            text: 文本描述
            context: 上下文信息

        Returns:
            视觉概念
        """
        with self._lock:
            concept_id = f"vc_{len(self._mapping_history)}"

            # 1. 解析文本实体
            entities = self._extract_entities(text)

            # 2. 提取视觉元素
            objects = self._extract_visual_objects(entities, context or {})

            # 3. 推断场景
            scenes = self._infer_scenes(entities, context or {})

            # 4. 提取颜色
            colors = self._extract_colors(text)

            # 5. 推断空间关系
            spatial_relations = self._infer_spatial_relations(objects, text)

            # 6. 提取属性
            attributes = self._extract_attributes(text, entities)

            return VisualConcept(
                id=concept_id,
                objects=objects,
                scenes=scenes,
                colors=colors,
                spatial_relations=spatial_relations,
                attributes=attributes,
                confidence=0.8
            )

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """提取实体"""
        entities = []

        # 简单实体提取（实际可用NER）
        common_entities = {
            "person": ["人", "男人", "女人", "孩子", "老人", "player", "man", "woman"],
            "object": ["物", "东西", "物品", "object", "item"],
            "place": ["地", "地方", "处", "place", "location"],
            "animal": ["动物", "狗", "猫", "bird", "animal"],
        }

        for entity_type, keywords in common_entities.items():
            for kw in keywords:
                if kw in text.lower():
                    entities.append({
                        "type": entity_type,
                        "text": kw,
                        "position": text.lower().find(kw)
                    })

        return entities

    def _extract_visual_objects(
        self,
        entities: List[Dict],
        context: Dict
    ) -> List[Dict[str, Any]]:
        """提取视觉对象"""
        objects = []

        for entity in entities:
            if entity["type"] in ["person", "object", "animal"]:
                obj = {
                    "type": entity["type"],
                    "label": entity["text"],
                    "position": {"x": 0.5, "y": 0.5},
                    "size": {"width": 100, "height": 100},
                    "confidence": 0.7
                }
                objects.append(obj)

        # 如果没有实体，添加默认对象
        if not objects:
            objects.append({
                "type": "object",
                "label": "unknown",
                "position": {"x": 0.5, "y": 0.5},
                "size": {"width": 100, "height": 100},
                "confidence": 0.3
            })

        return objects

    def _infer_scenes(
        self,
        entities: List[Dict],
        context: Dict
    ) -> List[str]:
        """推断场景"""
        scenes = []

        # 基于实体推断场景
        entity_types = [e["type"] for e in entities]

        if "person" in entity_types and "place" in entity_types:
            scenes.append("室内活动")
        if "animal" in entity_types:
            scenes.append("自然环境")
        if "object" in entity_types:
            scenes.append("物品特写")

        # 默认场景
        if not scenes:
            scenes.append("通用场景")

        return scenes

    def _extract_colors(self, text: str) -> List[str]:
        """提取颜色"""
        colors = []

        color_map = {
            "红": ["red", "红色"],
            "蓝": ["blue", "蓝色"],
            "绿": ["green", "绿色"],
            "黄": ["yellow", "黄色"],
            "黑": ["black", "黑色"],
            "白": ["white", "白色"],
            "金": ["gold", "金色"],
            "银": ["silver", "银色"],
        }

        for eng, chn in color_map.items():
            if eng in text or any(c in text.lower() for c in chn):
                colors.append(eng)

        return colors

    def _infer_spatial_relations(
        self,
        objects: List[Dict],
        text: str
    ) -> List[Dict]:
        """推断空间关系"""
        relations = []

        spatial_keywords = {
            "上": "above",
            "下": "below",
            "左": "left",
            "右": "right",
            "前": "front",
            "后": "behind",
            "中间": "center",
            "near": "near",
            "above": "above",
            "below": "below"
        }

        for kw, eng in spatial_keywords.items():
            if kw in text:
                relations.append({
                    "relation": eng,
                    "from": "object1",
                    "to": "object2"
                })

        return relations

    def _extract_attributes(
        self,
        text: str,
        entities: List[Dict]
    ) -> Dict[str, Any]:
        """提取属性"""
        attributes = {}

        # 尺寸
        size_keywords = {"大": "large", "小": "small", "big": "big", "small": "small"}
        for kw, size in size_keywords.items():
            if kw in text:
                attributes["size"] = size

        # 状态
        state_keywords = {"新": "new", "旧": "old", "new": "new", "old": "old"}
        for kw, state in state_keywords.items():
            if kw in text:
                attributes["state"] = state

        # 情感
        emotion_keywords = {
            "开心": "happy", "高兴": "happy",
            "悲伤": "sad", "难过": "sad",
            "愤怒": "angry", "生气": "angry"
        }
        for kw, emotion in emotion_keywords.items():
            if kw in text:
                attributes["emotion"] = emotion

        return attributes

    # ==================== 视觉→文本推理 ====================

    def visual_to_text(
        self,
        visual_data: Union[VisualConcept, Dict],
        context: Optional[Dict[str, Any]] = None
    ) -> TextRepresentation:
        """
        视觉→文本推理

        Args:
            visual_data: 视觉数据
            context: 上下文信息

        Returns:
            文本表示
        """
        with self._lock:
            # 如果是字典，转换为VisualConcept
            if isinstance(visual_data, dict):
                visual_data = self._dict_to_concept(visual_data)

            text_id = f"tr_{len(self._mapping_history)}"

            # 1. 生成场景描述
            content = self._generate_scene_description(visual_data)

            # 2. 提取实体
            entities = self._extract_entities_from_visual(visual_data)

            # 3. 推断关系
            relations = self._infer_relations_from_visual(visual_data)

            # 4. 推断情感
            sentiment = self._infer_sentiment(visual_data)

            # 5. 提取关键词
            keywords = self._extract_keywords_from_visual(visual_data)

            return TextRepresentation(
                id=text_id,
                content=content,
                entities=entities,
                relations=relations,
                sentiment=sentiment,
                keywords=keywords
            )

    def _dict_to_concept(self, data: Dict) -> VisualConcept:
        """字典转VisualConcept"""
        return VisualConcept(
            id=data.get("id", "unknown"),
            objects=data.get("objects", []),
            scenes=data.get("scenes", []),
            colors=data.get("colors", []),
            spatial_relations=data.get("spatial_relations", []),
            attributes=data.get("attributes", {}),
            confidence=data.get("confidence", 0.5)
        )

    def _generate_scene_description(self, concept: VisualConcept) -> str:
        """生成场景描述"""
        parts = []

        # 场景
        if concept.scenes:
            parts.append(f"这是一个{concept.scenes[0]}")

        # 对象
        if concept.objects:
            obj_names = [o.get("label", "物体") for o in concept.objects]
            parts.append(f"场景中有{', '.join(obj_names)}")

        # 颜色
        if concept.colors:
            parts.append(f"主要颜色有{', '.join(concept.colors)}")

        return "，".join(parts) if parts else "场景内容未知"

    def _extract_entities_from_visual(
        self,
        concept: VisualConcept
    ) -> List[Dict[str, Any]]:
        """从视觉提取实体"""
        entities = []

        for obj in concept.objects:
            entities.append({
                "type": obj.get("type", "object"),
                "text": obj.get("label", "unknown"),
                "confidence": obj.get("confidence", 0.5)
            })

        return entities

    def _infer_relations_from_visual(
        self,
        concept: VisualConcept
    ) -> List[Dict[str, Any]]:
        """从视觉推断关系"""
        return concept.spatial_relations

    def _infer_sentiment(self, concept: VisualConcept) -> float:
        """推断情感"""
        emotion = concept.attributes.get("emotion", "")

        sentiment_map = {
            "happy": 0.8,
            "sad": -0.6,
            "angry": -0.7,
            "neutral": 0.0
        }

        return sentiment_map.get(emotion, 0.0)

    def _extract_keywords_from_visual(
        self,
        concept: VisualConcept
    ) -> List[str]:
        """从视觉提取关键词"""
        keywords = []

        # 从场景提取
        keywords.extend(concept.scenes)

        # 从对象提取
        for obj in concept.objects:
            keywords.append(obj.get("label", ""))

        # 从颜色提取
        keywords.extend(concept.colors)

        # 去重
        return list(set([k for k in keywords if k]))

    # ==================== 跨模态类比 ====================

    def cross_modal_analogy(
        self,
        source: Any,
        source_modal: ModalType,
        target_modal: ModalType,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalogyResult:
        """
        跨模态类比推理

        Args:
            source: 源数据
            source_modal: 源模态
            target_modal: 目标模态
            context: 上下文

        Returns:
            类比结果
        """
        with self._lock:
            # 1. 提取源特征
            source_features = self._extract_modal_features(source, source_modal)

            # 2. 查找目标模态的相似特征
            target_features = self._find_similar_features(
                source_features,
                target_modal,
                context or {}
            )

            # 3. 建立映射
            mappings = self._create_mappings(source_features, target_features)

            # 4. 计算相似度
            similarity = self._compute_analogy_similarity(source_features, target_features)

            # 5. 生成推理
            reasoning = self._generate_analogy_reasoning(
                source, source_features, mappings
            )

            result = AnalogyResult(
                source=source,
                target=target_features,
                similarity=similarity,
                mappings=mappings,
                reasoning=reasoning
            )

            self._analogy_history.append(result)

            return result

    def _extract_modal_features(
        self,
        data: Any,
        modal: ModalType
    ) -> Dict[str, Any]:
        """提取模态特征"""
        features = {}

        if modal == ModalType.TEXT:
            if isinstance(data, str):
                features = {
                    "content": data,
                    "entities": self._extract_entities(data),
                    "keywords": data.split()[:10]
                }
        elif modal == ModalType.IMAGE:
            if isinstance(data, VisualConcept):
                features = {
                    "objects": [o["label"] for o in data.objects],
                    "scenes": data.scenes,
                    "colors": data.colors
                }
            else:
                features = {"objects": [], "scenes": [], "colors": []}

        return features

    def _find_similar_features(
        self,
        source_features: Dict,
        target_modal: ModalType,
        context: Dict
    ) -> Any:
        """查找相似特征"""
        # 简化实现：返回基于源特征的推理
        if target_modal == ModalType.TEXT:
            # 文本→视觉
            return self.text_to_visual(
                source_features.get("content", ""),
                context
            )
        elif target_modal == ModalType.IMAGE:
            # 视觉→文本
            concept = VisualConcept(
                id="temp",
                objects=[{"label": o, "type": "object"} for o in source_features.get("objects", [])],
                scenes=source_features.get("scenes", []),
                colors=source_features.get("colors", []),
                spatial_relations=[],
                attributes={}
            )
            return self.visual_to_text(concept, context)

        return None

    def _create_mappings(
        self,
        source: Dict,
        target: Any
    ) -> List[Dict[str, Any]]:
        """创建映射"""
        mappings = []

        # 简单映射
        if "entities" in source and isinstance(target, TextRepresentation):
            for i, entity in enumerate(source.get("entities", [])):
                mappings.append({
                    "source": entity["text"],
                    "target": target.entities[i] if i < len(target.entities) else None,
                    "relation": "entity_mapping"
                })

        return mappings

    def _compute_analogy_similarity(
        self,
        source: Dict,
        target: Any
    ) -> float:
        """计算类比相似度"""
        # 简化实现
        if isinstance(target, VisualConcept):
            source_objs = set(source.get("objects", []))
            target_objs = set(o["label"] for o in target.objects)

            if not source_objs or not target_objs:
                return 0.5

            overlap = len(source_objs & target_objs)
            return overlap / len(source_objs | target_objs)

        elif isinstance(target, TextRepresentation):
            source_kw = set(source.get("keywords", []))
            target_kw = set(target.keywords)

            if not source_kw or not target_kw:
                return 0.5

            overlap = len(source_kw & target_kw)
            return overlap / len(source_kw | target_kw)

        return 0.3

    def _generate_analogy_reasoning(
        self,
        source: Any,
        features: Dict,
        mappings: List[Dict]
    ) -> str:
        """生成类比推理"""
        if not mappings:
            return "无法建立有效的映射关系"

        mapping_desc = ", ".join([m["source"] for m in mappings[:3]])

        return f"基于源数据特征({mapping_desc})，建立跨模态映射关系"

    # ==================== 模态一致性检查 ====================

    def check_consistency(
        self,
        outputs: Dict[ModalType, Any]
    ) -> Tuple[ConsistencyStatus, float]:
        """
        检查多模态输出的一致性

        Args:
            outputs: 各模态的输出

        Returns:
            (一致性状态, 一致性得分)
        """
        if not self.enable_consistency_check:
            return ConsistencyStatus.UNKNOWN, 0.5

        if len(outputs) < 2:
            return ConsistencyStatus.UNKNOWN, 0.5

        consistency_scores = []

        # 比较各模态对
        modals = list(outputs.keys())

        for i in range(len(modals)):
            for j in range(i + 1, len(modals)):
                score = self._compare_modalities(
                    outputs[modals[i]],
                    outputs[modals[j]]
                )
                consistency_scores.append(score)

        avg_score = np.mean(consistency_scores)

        # 确定状态
        if avg_score >= self.CONSISTENT_THRESHOLD:
            status = ConsistencyStatus.CONSISTENT
        elif avg_score >= self.PARTIAL_THRESHOLD:
            status = ConsistencyStatus.PARTIAL
        else:
            status = ConsistencyStatus.INCONSISTENT

        return status, avg_score

    def _compare_modalities(self, output1: Any, output2: Any) -> float:
        """比较两个模态的输出"""
        # 提取可比较的特征
        features1 = self._extract_comparable_features(output1)
        features2 = self._extract_comparable_features(output2)

        if not features1 or not features2:
            return 0.5

        # 计算Jaccard相似度
        set1 = set(features1)
        set2 = set(features2)

        if not set1 or not set2:
            return 0.5

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.5

    def _extract_comparable_features(self, output: Any) -> List[str]:
        """提取可比较的特征"""
        features = []

        if isinstance(output, VisualConcept):
            features.extend([o["label"] for o in output.objects])
            features.extend(output.scenes)
            features.extend(output.colors)

        elif isinstance(output, TextRepresentation):
            features.extend(output.keywords)
            features.extend([e["text"] for e in output.entities])

        elif isinstance(output, str):
            features.extend(output.split())

        elif isinstance(output, dict):
            for v in output.values():
                if isinstance(v, list):
                    features.extend([str(i) for i in v])
                else:
                    features.append(str(v))

        return features

    # ==================== 模态选择性融合 ====================

    def adaptive_fusion(
        self,
        inputs: Dict[ModalType, Any],
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> FusionResult:
        """
        自适应模态融合

        Args:
            inputs: 各模态输入
            task: 任务类型
            context: 上下文

        Returns:
            融合结果
        """
        with self._lock:
            # 1. 计算各模态权重
            weights = self._compute_modality_weights(inputs, task, context or {})

            # 2. 提取各模态表示
            representations = {}

            for modal, data in inputs.items():
                if modal == ModalType.TEXT:
                    if isinstance(data, str):
                        representations[modal] = self._text_to_embedding(data)
                    else:
                        representations[modal] = data

                elif modal == ModalType.IMAGE:
                    if isinstance(data, dict):
                        concept = self._dict_to_concept(data)
                    else:
                        concept = data
                    representations[modal] = self._visual_to_embedding(concept)

                else:
                    representations[modal] = self._generic_to_embedding(data)

            # 3. 加权融合
            fused = self._weighted_fuse(representations, weights)

            # 4. 检查一致性
            consistency_status = ConsistencyStatus.UNKNOWN
            consistency_score = 0.5

            if self.enable_consistency_check and len(inputs) > 1:
                consistency_status, consistency_score = self.check_consistency(inputs)

            # 5. 构建推理链
            reasoning_chain = self._build_fusion_reasoning(inputs, weights)

            result = FusionResult(
                content=fused,
                modality_weights=weights,
                consistency=consistency_status,
                reasoning_chain=reasoning_chain,
                confidence=consistency_score
            )

            self._fusion_history.append(result)

            return result

    def _compute_modality_weights(
        self,
        inputs: Dict[ModalType, Any],
        task: str,
        context: Dict
    ) -> Dict[ModalType, float]:
        """计算模态权重"""
        weights = {}

        # 任务相关的默认权重
        task_weights = {
            "description": {ModalType.TEXT: 0.6, ModalType.IMAGE: 0.4},
            "generation": {ModalType.TEXT: 0.7, ModalType.IMAGE: 0.3},
            "analysis": {ModalType.TEXT: 0.5, ModalType.IMAGE: 0.5},
            "comparison": {ModalType.TEXT: 0.4, ModalType.IMAGE: 0.6},
        }

        default_weights = task_weights.get(task, {ModalType.TEXT: 0.5, ModalType.IMAGE: 0.5})

        for modal in inputs.keys():
            # 基础权重
            base_weight = default_weights.get(modal, 0.5)

            # 质量调整
            quality = context.get(f"{modal.value}_quality", 0.8)

            # 可靠性调整
            reliability = context.get(f"{modal.value}_reliability", 0.8)

            weights[modal] = base_weight * quality * reliability

        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def _text_to_embedding(self, text: str) -> np.ndarray:
        """文本转嵌入"""
        # 简化实现：词袋向量
        words = text.lower().split()
        vec = np.random.randn(128)

        for i, w in enumerate(words[:128]):
            vec[i] = hash(w) % 100 / 100.0

        return vec / (np.linalg.norm(vec) + 1e-8)

    def _visual_to_embedding(self, concept: VisualConcept) -> np.ndarray:
        """视觉转嵌入"""
        vec = np.random.randn(128)

        # 基于对象
        for i, obj in enumerate(concept.objects[:32]):
            vec[i] = hash(obj.get("label", "")) % 100 / 100.0

        return vec / (np.linalg.norm(vec) + 1e-8)

    def _generic_to_embedding(self, data: Any) -> np.ndarray:
        """通用转嵌入"""
        return np.random.randn(128)

    def _weighted_fuse(
        self,
        representations: Dict[ModalType, np.ndarray],
        weights: Dict[ModalType, float]
    ) -> Any:
        """加权融合"""
        fused = np.zeros(128)

        for modal, embedding in representations.items():
            weight = weights.get(modal, 0.0)
            fused += weight * embedding

        # 返回简化结果
        return {
            "embedding": fused.tolist(),
            "magnitude": float(np.linalg.norm(fused))
        }

    def _build_fusion_reasoning(
        self,
        inputs: Dict[ModalType, Any],
        weights: Dict[ModalType, float]
    ) -> List[Dict[str, Any]]:
        """构建融合推理链"""
        reasoning = []

        for modal, weight in weights.items():
            reasoning.append({
                "modality": modal.value,
                "weight": weight,
                "action": "weighted_contribution"
            })

        return reasoning

    # ==================== 历史和统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_mappings": len(self._mapping_history),
            "total_fusions": len(self._fusion_history),
            "total_analogies": len(self._analogy_history),
            "cache_size": len(self._embedding_cache)
        }

    def __repr__(self) -> str:
        return f"MultiModalReasoning(mappings={len(self._mapping_history)}, fusions={len(self._fusion_history)})"
