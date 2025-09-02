from ..connection import client
from typing import List
import json
import logging

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def rerank_documents(user_question: str, documents: List[dict]) -> List[dict]: # just demo with gemini-2.5-flash to rerank documents, will change to model best to rerank documents
    """
    rerank tài liệu dựa trên mức độ liên quan đến câu hỏi của người dùng
    """
    if not documents:
        logger.warning("No documents provided for reranking")
        return []

    if not user_question or not user_question.strip():
        logger.warning("No question provided for reranking")
        return documents

    logger.info(f"Starting reranking for {len(documents)} documents with question: '{user_question}'")

    docs_for_prompt = []
    for doc in documents:
        # Ensure _id is string (handle both ObjectId and string cases)
        doc_id = str(doc['_id'])
        doc['_id'] = doc_id  # Update the original document too
        
        # Build richer content from available fields
        content_parts = []
        if doc.get('head'):
            content_parts.append(f"Tiêu đề: {doc['head']}")
        if doc.get('define'):
            content_parts.append(f"Định nghĩa: {doc['define']}")
        if doc.get('keywords') and isinstance(doc['keywords'], list):
            content_parts.append(f"Từ khóa: {', '.join(doc['keywords'])}")
        if doc.get('chapter_name'):
            content_parts.append(f"Chương: {doc['chapter_name']}")
        
        content = "\n".join(content_parts) if content_parts else doc.get('define', '')
        
        docs_for_prompt.append({
            "id": doc_id,
            "content": content
        })
        
        logger.info(f"Doc {doc_id}: head='{doc.get('head', 'N/A')}', define_len={len(doc.get('define', ''))}, keywords={doc.get('keywords', 'N/A')}")
        logger.info(f"Prepared doc {doc_id}: content length={len(content)}, preview={content[:100]}...")

    logger.info(f"Prepared {len(docs_for_prompt)} documents for reranking")

    prompt = f"""Bạn là chuyên gia đánh giá mức độ liên quan của tài liệu. Hãy chấm điểm từ 0.0 đến 1.0 cho mỗi tài liệu dựa trên mức độ liên quan với câu hỏi.

THANG ĐIỂM:
- 1.0: Tài liệu trả lời trực tiếp và đầy đủ câu hỏi
- 0.8: Tài liệu có thông tin rất liên quan, giúp trả lời câu hỏi
- 0.6: Tài liệu có liên quan nhưng không trả lời trực tiếp
- 0.4: Tài liệu có một số thông tin liên quan
- 0.2: Tài liệu ít liên quan
- 0.0: Tài liệu không liên quan

CÂU HỎI: {user_question}

TÀI LIỆU:
{json.dumps(docs_for_prompt, ensure_ascii=False, indent=2)}

Trả về JSON theo format:
[
  {{"id": "doc_id", "new_score": điểm_số}},
  ...
]"""

    logger.info("Sending reranking request to Gemini API...")
    response = client.models.generate_content(model='gemini-2.5-pro', contents=prompt)
    logger.info("Received response from Gemini API")
    
    # Log raw response for debugging
    raw_response = response.text.strip()
    logger.info(f"Raw response: {raw_response}")
    
    # Clean the response
    cleaned_response_text = raw_response
    if "```json" in cleaned_response_text:
        cleaned_response_text = cleaned_response_text.replace("```json", "").replace("```", "")
    elif "```" in cleaned_response_text:
        cleaned_response_text = cleaned_response_text.replace("```", "")
    
    cleaned_response_text = cleaned_response_text.strip()
    logger.info(f"Cleaned response: {cleaned_response_text}")
    
    # Parse JSON
    rerank_results = json.loads(cleaned_response_text)
    logger.info(f"Parsed {len(rerank_results)} rerank results")
    
    # Create scores mapping
    scores_map = {item['id']: item['new_score'] for item in rerank_results}
    logger.info(f"Scores map: {scores_map}")
    
    # Apply scores to documents
    for doc in documents:
        doc_id = str(doc['_id'])  # Ensure string comparison
        new_score = scores_map.get(doc_id, 0.0)
        doc['new_score'] = new_score
        logger.debug(f"Applied score {new_score} to doc {doc_id}")
    
    # Sort by new score
    reranked_documents = sorted(documents, key=lambda x: x.get('new_score', 0.0), reverse=True)
    
    final_scores = [doc.get('new_score', 0.0) for doc in reranked_documents]
    logger.info(f"Reranking completed. Final scores: {final_scores}")
    
    return reranked_documents