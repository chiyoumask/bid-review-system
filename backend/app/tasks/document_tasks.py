"""
文档解析和审核任务 - 后台异步执行
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session
from app.core.config import settings
from app.models.project import (
    ProjectDocument, ScoringCriteria, ReviewTask, ReviewResult
)
from app.services.pdf_parser import PDFParser
from app.services.llm_client import LLMClient
from app.services.scoring_parser import ScoringParser
from app.services.bid_analyzer import BidAnalyzer
from app.services.comparison_engine import ComparisonEngine

logger = logging.getLogger(__name__)


def _get_llm_client() -> LLMClient:
    """Get an LLM client with the first active provider."""
    # For MVP, use default config from settings
    # TODO: load from configured providers
    if not settings.LLM_API_KEY:
        raise ValueError("未配置 LLM API Key，请在系统设置中配置")
    return LLMClient(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT,
    )


async def parse_document_task(document_id: int):
    """
    Background task: parse an uploaded document (PDF → text).
    """
    async with async_session() as db:
        try:
            doc = await db.get(ProjectDocument, document_id)
            if not doc:
                return

            doc.status = "parsing"
            await db.commit()

            # Parse PDF
            if doc.file_path.lower().endswith(".pdf"):
                result = PDFParser.extract_text(doc.file_path)
                doc.parsed_text = result["text"]
                doc.page_count = result["page_count"]
                doc.parsed_json = {
                    "tables": result["tables"],
                    "pages": [{"page": p["page"], "char_count": len(p["text"])} for p in result["pages"]],
                }
            else:
                # For .txt files, read directly
                with open(doc.file_path, "r", encoding="utf-8") as f:
                    doc.parsed_text = f.read()

            # If this is a scoring criteria document, parse it with LLM
            if doc.doc_type == "scoring_criteria" and doc.parsed_text:
                try:
                    llm = _get_llm_client()
                    parser = ScoringParser(llm)
                    parsed = await parser.parse_with_retry(doc.parsed_text)

                    # Delete existing criteria for this document's project
                    existing = await db.execute(
                        select(ScoringCriteria).where(ScoringCriteria.project_id == doc.project_id)
                    )
                    for c in existing.scalars().all():
                        await db.delete(c)

                    # Create new criteria from parsed result
                    sort_order = 0
                    for category in parsed.get("categories", []):
                        for item in category.get("items", []):
                            criteria = ScoringCriteria(
                                project_id=doc.project_id,
                                category=category.get("category", "未分类"),
                                item_name=item.get("item_name", ""),
                                max_score=item.get("max_score", 0),
                                description=item.get("description", ""),
                                evaluation_criteria=item.get("evaluation_criteria", ""),
                                sort_order=sort_order,
                            )
                            db.add(criteria)
                            sort_order += 1

                    await llm.close()
                    doc.status = "parsed"
                except Exception as e:
                    logger.error(f"Failed to parse scoring criteria with LLM: {e}")
                    doc.status = "error"
                    doc.error_message = f"评分标准解析失败: {str(e)}"
            else:
                doc.status = "parsed"

            await db.commit()
            logger.info(f"Document {document_id} parsed successfully")

        except Exception as e:
            logger.error(f"Document parsing failed for {document_id}: {e}")
            try:
                doc = await db.get(ProjectDocument, document_id)
                if doc:
                    doc.status = "error"
                    doc.error_message = str(e)
                    await db.commit()
            except Exception:
                pass


async def analyze_bid_task(task_id: int):
    """
    Background task: analyze a bid document against scoring criteria.
    This is the main analysis pipeline.
    """
    async with async_session() as db:
        try:
            task = await db.get(ReviewTask, task_id)
            if not task:
                return

            task.status = "analyzing"
            await db.commit()

            # Get the bid document
            bid_doc = await db.get(ProjectDocument, task.bid_document_id)
            if not bid_doc or not bid_doc.parsed_text:
                task.status = "error"
                task.error_message = "投标文件未解析或解析失败"
                await db.commit()
                return

            # Get scoring criteria
            criteria_result = await db.execute(
                select(ScoringCriteria)
                .where(ScoringCriteria.project_id == task.project_id)
                .order_by(ScoringCriteria.sort_order)
            )
            criteria_list = criteria_result.scalars().all()
            if not criteria_list:
                task.status = "error"
                task.error_message = "未找到评分标准"
                await db.commit()
                return

            # Calculate total possible score
            total_score = sum(c.max_score for c in criteria_list)
            task.total_possible_score = total_score

            # Initialize LLM client
            llm = _get_llm_client()
            bid_analyzer = BidAnalyzer(llm)
            comparator = ComparisonEngine(llm)

            # Step 1: Extract content for each criteria
            criteria_items = [
                {
                    "item_name": c.item_name,
                    "max_score": c.max_score,
                    "description": c.description or "",
                    "evaluation_criteria": c.evaluation_criteria or "",
                }
                for c in criteria_list
            ]

            extractions = await bid_analyzer.extract_for_criteria(
                bid_doc.parsed_text, criteria_items
            )

            # Step 2: Evaluate against criteria
            evaluation = await comparator.evaluate(
                criteria_items, extractions, bid_doc.parsed_text
            )

            # Step 3: Create review results
            high_count = 0
            medium_count = 0
            low_count = 0

            for review_item in evaluation.get("review_items", []):
                # Find matching criteria
                matching_criteria = None
                for c in criteria_list:
                    if c.item_name == review_item.get("item_name"):
                        matching_criteria = c
                        break

                if not matching_criteria:
                    continue

                risk = review_item.get("risk_level", "none")
                if risk == "high":
                    high_count += 1
                elif risk == "medium":
                    medium_count += 1
                elif risk == "low":
                    low_count += 1

                result = ReviewResult(
                    task_id=task.id,
                    criteria_id=matching_criteria.id,
                    category=review_item.get("category", matching_criteria.category),
                    item_name=review_item.get("item_name", matching_criteria.item_name),
                    max_score=review_item.get("max_score", matching_criteria.max_score),
                    ai_estimated_score=review_item.get("ai_estimated_score"),
                    ai_analysis=review_item.get("ai_analysis", ""),
                    risk_level=risk,
                    risk_description=review_item.get("risk_description", ""),
                    bid_content_excerpt=review_item.get("bid_content_excerpt", ""),
                )
                db.add(result)

            # Update task summary
            task.risk_count_high = high_count
            task.risk_count_medium = medium_count
            task.risk_count_low = low_count
            task.estimated_score = sum(
                r.get("ai_estimated_score", 0) for r in evaluation.get("review_items", [])
            )
            task.summary = evaluation.get("overall_summary", "")
            task.status = "completed"

            await llm.close()
            await db.commit()
            logger.info(f"Review task {task_id} completed")

        except Exception as e:
            logger.error(f"Bid analysis failed for task {task_id}: {e}")
            try:
                task = await db.get(ReviewTask, task_id)
                if task:
                    task.status = "error"
                    task.error_message = str(e)
                    await db.commit()
            except Exception:
                pass
