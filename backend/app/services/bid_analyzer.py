"""
投标文件分析服务 - 提取投标文件中的关键信息
"""
import logging
from typing import Dict, Any, List

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

BID_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的招投标文件分析专家。你的任务是从投标文件中提取关键信息。

请提取以下方面的信息并以JSON格式返回：

```json
{
  "bidder_name": "投标单位名称",
  "project_understanding": "对项目的理解（简要）",
  "qualifications": {
    "company_qualifications": ["公司资质列表"],
    "team_qualifications": ["项目团队资质"],
    "experience": ["类似项目经验"]
  },
  "technical_proposal": {
    "solution_overview": "技术方案概述",
    "key_features": ["关键技术特点"],
    "implementation_plan": "实施方案概要",
    "timeline": "项目时间计划"
  },
  "commercial_terms": {
    "total_price": "投标总价",
    "price_breakdown": {"项目": "金额"},
    "payment_terms": "付款条件",
    "warranty": "质保承诺",
    "delivery_time": "交付周期"
  },
  "risk_commitments": ["投标方做出的承诺和保证"],
  "special_terms": ["特殊条款或偏离项"]
}
```

注意：
1. 如果某项信息在文档中未找到，对应字段设为 null
2. 金额请保留原始格式
3. 关键承诺和保证必须完整提取
4. 偏离招标要求的条款要特别标记"""


class BidAnalyzer:
    """Analyze bid documents using LLM."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def extract_info(self, document_text: str) -> Dict[str, Any]:
        """
        Extract key information from a bid document.

        Returns structured data about the bid.
        """
        # For very long documents, we may need to split and process in chunks
        # For now, send the full text with a reasonable token limit
        truncated_text = document_text[:80000]  # ~20K tokens, safe for most LLMs

        messages = [
            {"role": "system", "content": BID_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"请从以下投标文件中提取关键信息：\n\n{truncated_text}"},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.1)
            return result
        except Exception as e:
            logger.error(f"Failed to extract bid info: {e}")
            raise

    async def extract_for_criteria(
        self, document_text: str, criteria_items: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Extract content from bid document specifically related to each scoring criteria item.

        Args:
            document_text: The full text of the bid document
            criteria_items: List of scoring criteria items to match against

        Returns:
            Dict mapping criteria item_name to extracted relevant content
        """
        criteria_list = "\n".join([
            f"- {item['item_name']}（满分{item['max_score']}分）: {item.get('description', '')}"
            for item in criteria_items
        ])

        prompt = f"""请从投标文件中，针对以下每个评分项，提取对应的投标文件内容摘录。

评分项列表：
{criteria_list}

请以JSON格式返回，每个评分项对应一个提取结果：

```json
{{
  "extractions": {{
    "评分项名称": {{
      "relevant_content": "投标文件中与该评分项相关的原文摘录",
      "page_reference": "大致在文档的哪个部分",
      "completeness": "完整/部分/缺失"
    }}
  }}
}}
```

注意：
1. 尽量引用原文内容，不要改写
2. 如果某个评分项在投标文件中找不到对应内容，标记为"缺失"
3. 每个摘录控制在500字以内"""

        truncated_text = document_text[:60000]
        messages = [
            {"role": "system", "content": "你是招投标文件分析专家，擅长从投标文件中定位与评分标准对应的内容。"},
            {"role": "user", "content": f"{prompt}\n\n投标文件内容：\n{truncated_text}"},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.1)
            return result.get("extractions", {})
        except Exception as e:
            logger.error(f"Failed to extract for criteria: {e}")
            raise
