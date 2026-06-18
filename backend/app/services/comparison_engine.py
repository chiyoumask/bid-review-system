"""
评分比对引擎 - 将投标文件内容与评分标准进行比对，给出预估得分和风险判定
"""
import logging
from typing import Dict, Any, List

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

COMPARISON_SYSTEM_PROMPT = """你是一个资深的招投标评审专家。你的任务是根据评分标准，逐项评估投标文件的响应情况。

评估原则：
1. 严格按照评分标准的得分条件进行评估
2. 高风险（high）：明显不满足、缺失关键材料、可能废标
3. 中风险（medium）：部分满足、描述不够充分、可能失分
4. 低风险（low）：基本满足但可以优化
5. 无风险（none）：完全满足且表述充分

请严格按照JSON格式返回评审结果：

```json
{
  "review_items": [
    {
      "item_name": "评分项名称",
      "category": "所属大类",
      "max_score": 满分分值,
      "ai_estimated_score": AI预估得分,
      "ai_analysis": "详细的分析说明（为什么给这个分数）",
      "risk_level": "high/medium/low/none",
      "risk_description": "风险描述（如有）",
      "bid_content_excerpt": "投标文件中的相关原文摘录",
      "improvement_suggestions": "改进建议（如有）"
    }
  ],
  "overall_summary": "整体评价总结",
  "critical_issues": ["关键问题列表（可能导致废标的问题）"]
}
```

重要：
1. 评分要客观公正，有理有据
2. 分析说明要具体，引用原文
3. 对于无法判断的项，保守评分并说明原因"""


class ComparisonEngine:
    """Compare bid content against scoring criteria and generate review results."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def evaluate(
        self,
        scoring_criteria: List[Dict[str, Any]],
        bid_extractions: Dict[str, Any],
        bid_document_text: str,
    ) -> Dict[str, Any]:
        """
        Evaluate a bid against scoring criteria.

        Args:
            scoring_criteria: List of scoring criteria items
            bid_extractions: Extracted content from bid document (keyed by item_name)
            bid_document_text: Full bid document text (as fallback context)

        Returns:
            Complete evaluation results
        """
        # Build criteria description
        criteria_desc = []
        total_score = 0
        for item in scoring_criteria:
            criteria_desc.append(
                f"- [{item.get('category', '未分类')}] {item['item_name']}（满分{item['max_score']}分）: "
                f"{item.get('description', '')} | 评分标准: {item.get('evaluation_criteria', '无')}"
            )
            total_score += item["max_score"]

        criteria_text = "\n".join(criteria_desc)

        # Build extraction summary
        extraction_desc = []
        for item_name, extraction in bid_extractions.items():
            content = extraction.get("relevant_content", "未找到对应内容") if isinstance(extraction, dict) else "未找到"
            extraction_desc.append(f"[{item_name}]: {content[:300]}")
        extraction_text = "\n".join(extraction_desc) if extraction_desc else "（未提取到具体内容）"

        # Truncate document for context
        doc_truncated = bid_document_text[:40000]

        user_prompt = f"""请根据以下评分标准，逐项评估投标文件的响应情况。

===== 评分标准（满分{total_score}分）=====
{criteria_text}

===== 投标文件针对各评分项的内容摘录 =====
{extraction_text}

===== 投标文件全文参考 =====
{doc_truncated}

请逐项给出预估得分、分析说明和风险等级。"""

        messages = [
            {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.2, max_tokens=8192)
            result["total_possible_score"] = total_score
            return result
        except Exception as e:
            logger.error(f"Failed to evaluate bid: {e}")
            raise

    async def generate_summary(
        self,
        evaluation_results: List[Dict[str, Any]],
        total_possible_score: float,
    ) -> str:
        """Generate a human-readable summary of the evaluation."""
        high_risks = [r for r in evaluation_results if r.get("risk_level") == "high"]
        medium_risks = [r for r in evaluation_results if r.get("risk_level") == "medium"]

        total_estimated = sum(r.get("ai_estimated_score", 0) for r in evaluation_results)
        percentage = (total_estimated / total_possible_score * 100) if total_possible_score > 0 else 0

        summary_parts = [
            f"预估总分：{total_estimated:.1f} / {total_possible_score:.1f}（{percentage:.1f}%）",
            f"高风险项：{len(high_risks)}个",
            f"中风险项：{len(medium_risks)}个",
        ]

        if high_risks:
            summary_parts.append("\n⚠️ 关键风险：")
            for r in high_risks[:5]:
                summary_parts.append(f"  - [{r.get('category', '')}] {r.get('item_name', '')}: {r.get('risk_description', '')}")

        return "\n".join(summary_parts)
