"""
评分标准解析服务 - 从评分标准文档中提取结构化评分项
"""
import logging
from typing import List, Dict, Any

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

SCORING_CRITERIA_SYSTEM_PROMPT = """你是一个专业的招投标文件分析专家。你的任务是从投标评分标准文档中提取所有评分项。

请按照以下JSON格式返回提取结果：

```json
{
  "project_name": "项目名称（如果能识别到）",
  "total_score": 满分总分,
  "categories": [
    {
      "category": "大类名称（如：资质条件、技术方案、商务条款、价格评分等）",
      "items": [
        {
          "item_name": "评分项名称",
          "max_score": 该项满分分值,
          "description": "评分项的详细描述",
          "evaluation_criteria": "具体的评分标准和细则（如：满足得X分，不满足得0分）",
          "sort_order": 在该大类中的排序序号
        }
      ]
    }
  ]
}
```

注意：
1. 必须提取所有评分项，不要遗漏
2. 分值必须准确，包括小数分值
3. 评分细则要完整提取，包括各种得分条件
4. 如果评分标准包含否决项（废标项），也要标记出来
5. 排序按照文档中出现的顺序"""


class ScoringParser:
    """Parse scoring criteria documents using LLM."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse a scoring criteria document into structured data.

        Returns:
            {
                "project_name": str,
                "total_score": float,
                "categories": [
                    {
                        "category": str,
                        "items": [
                            {
                                "item_name": str,
                                "max_score": float,
                                "description": str,
                                "evaluation_criteria": str,
                                "sort_order": int
                            }
                        ]
                    }
                ]
            }
        """
        messages = [
            {"role": "system", "content": SCORING_CRITERIA_SYSTEM_PROMPT},
            {"role": "user", "content": f"请从以下投标评分标准文档中提取所有评分项：\n\n{document_text}"},
        ]

        try:
            result = await self.llm.chat_json(messages, temperature=0.1)
            return self._validate_result(result)
        except Exception as e:
            logger.error(f"Failed to parse scoring criteria: {e}")
            raise

    @staticmethod
    def _validate_result(result: dict) -> dict:
        """Validate and clean the parsed result."""
        if "categories" not in result:
            raise ValueError("LLM response missing 'categories' field")

        for cat in result["categories"]:
            if "category" not in cat or "items" not in cat:
                raise ValueError(f"Invalid category structure: {cat}")
            for item in cat["items"]:
                required_fields = ["item_name", "max_score"]
                for field in required_fields:
                    if field not in item:
                        raise ValueError(f"Missing required field '{field}' in item: {item}")

        return result

    async def parse_with_retry(self, document_text: str, max_retries: int = 2) -> Dict[str, Any]:
        """Parse with retry logic for robustness."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return await self.parse(document_text)
            except Exception as e:
                last_error = e
                logger.warning(f"Parse attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    # Slightly increase temperature on retry for different extraction
                    pass
        raise last_error
