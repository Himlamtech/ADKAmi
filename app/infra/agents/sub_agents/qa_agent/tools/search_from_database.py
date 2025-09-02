from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from dotenv import load_dotenv
from ..connection import mongo_client
from .embedding import get_embedding
from ..config import DEFAULT_EMBEDDING_MODEL, DEFAULT_VECTOR_SEARCH_INDEX, DEFAULT_ATLAS_SEARCH_INDEX

load_dotenv()




def format_string(doc: Dict[str, Any]) -> str:
    """
    Định dạng một tài liệu thành chuỗi để tạo embedding.
    
    Args:
        doc: Document từ MongoDB collection 'knowledge'
        
    Returns:
        str: Formatted string cho embedding
    """
    # Lấy các fields thực tế từ MongoDB schema
    parts = []
    
    # Chapter/Topic info
    if chapter_name := doc.get('chapter_name', '').strip():
        parts.append(f"Chương: {chapter_name}")
        
    # Header/Title
    if header := doc.get('header', '').strip():
        parts.append(f"Tiêu đề: {header}")
        
    # Head (main concept)
    if head := doc.get('head', '').strip():
        parts.append(f"Khái niệm chính: {head}")
        
    # Definition
    if definition := doc.get('define', '').strip():
        parts.append(f"Định nghĩa: {definition}")
        
    # Content
    if content := doc.get('content', '').strip():
        # Limit content length for embedding
        content = content[:500] + "..." if len(content) > 500 else content
        parts.append(f"Nội dung: {content}")
        
    # Keywords
    if keywords := doc.get('keywords'):
        if isinstance(keywords, list):
            keywords_str = ", ".join(str(k) for k in keywords if k)
        else:
            keywords_str = str(keywords).strip()
            
        if keywords_str:
            parts.append(f"Từ khóa: {keywords_str}")
    
    # Join with double newlines for better separation
    return "\n\n".join(parts) if parts else "Không có nội dung"


def format_search_result(doc: Dict[str, Any]) -> str:
    """
    Định dạng kết quả tìm kiếm cho người dùng (khác với embedding format).
    
    Args:
        doc: Document từ search results
        
    Returns:
        str: Human-readable formatted result
    """
    result = []
    
    # Title với score nếu có
    header = doc.get('header', 'Không có tiêu đề')
    if score := doc.get('combined_score'):
        result.append(f"📚 **{header}** (Score: {score:.2f})")
    else:
        result.append(f"📚 **{header}**")
    
    # Chapter info
    if chapter := doc.get('chapter_name', '').strip():
        result.append(f"📖 *Chương: {chapter}*")
    
    # Main concept
    if head := doc.get('head', '').strip():
        result.append(f"🎯 **Khái niệm:** {head}")
    
    # Definition (shortened)
    if definition := doc.get('define', '').strip():
        definition = definition[:200] + "..." if len(definition) > 200 else definition
        result.append(f"📝 **Định nghĩa:** {definition}")
    
    # Keywords as tags
    if keywords := doc.get('keywords'):
        if isinstance(keywords, list):
            tags = [f"`{k}`" for k in keywords if k]
        else:
            tags = [f"`{keywords}`"] if str(keywords).strip() else []
            
        if tags:
            result.append(f"🏷️ **Tags:** {' '.join(tags)}")
    
    return "\n".join(result)


def format_document_for_context(doc: Dict[str, Any]) -> str:
    """
    Định dạng document để đưa vào context của AI assistant.
    
    Args:
        doc: Document từ MongoDB
        
    Returns:
        str: Formatted content for AI context
    """
    context_parts = []
    
    if header := doc.get('header', '').strip():
        context_parts.append(f"[{header}]")
    
    if head := doc.get('head', '').strip():
        context_parts.append(f"Khái niệm: {head}")
        
    if definition := doc.get('define', '').strip():
        context_parts.append(f"Định nghĩa: {definition}")
        
    if content := doc.get('content', '').strip():
        # Limit for context window
        content = content[:800] + "..." if len(content) > 800 else content
        context_parts.append(f"Chi tiết: {content}")
    
    return " | ".join(context_parts)



def find_similar_documents_by_hybrid_search(
    query: str,
    limit: int = 10,
    candidates: int = 50,
    vector_search_index: str = DEFAULT_VECTOR_SEARCH_INDEX,
    atlas_search_index: str = "text_search"
):
    """
    Đây là một tool tìm kiếm hybrid để tìm kiếm các lý thuyết môn lí thuyết đồ thị tương tự sử dụng kết hợp vector search và text search.
    Sử dụng tool này khi cần tìm kiếm các lý thuyết liên quan đến một chủ đề hoặc câu hỏi cụ thể,
    với khả năng tìm kiếm ngữ nghĩa (vector) và tìm kiếm văn bản (text) được thực hiện song song.

    Parameters:
        query (str): Câu truy vấn tìm kiếm lý thuyết.
                    Có thể là từ khóa, câu hỏi hoặc mô tả về nội dung lý thuyết cần tìm.
                    Ví dụ: "đồ thị", "lý thuyết đồ thị", "đồ thị có hướng".
        limit (int, optional): Số lượng lý thuyết tối đa trả về. Mặc định là 10.
                              Giá trị hợp lệ từ 1 đến 50.
        candidates (int, optional): Số lượng ứng viên cho vector search. Mặc định là 50.
                                   Càng cao thì chất lượng tìm kiếm càng tốt nhưng chậm hơn.
        vector_search_index (str, optional): Tên index MongoDB cho vector search. 
                                            Mặc định là "vector_index"
        atlas_search_index (str, optional): Tên index MongoDB cho text search.
                                           Mặc định là "text_search"

    Returns:
        dict: Một từ điển chứa kết quả tìm kiếm với các key:
            - 'status': 'success' nếu tìm kiếm thành công, 'error' nếu có lỗi
            - 'data': danh sách các lý thuyết tìm được dưới dạng chuỗi formatted (chỉ khi thành công)
            - 'message': thông báo về kết quả hoặc lỗi
    """
    try:
        collection = mongo_client['chatbotdb']['knowledge']
        query_embedding = get_embedding(query, DEFAULT_EMBEDDING_MODEL)
    except Exception as e:
        return {
            "status": "error",
            "data": [],
            "message": f"Lỗi kết nối hoặc tạo embedding: {str(e)}"
        }
    
    # Common project fields
    project_fields = {
        '_id': 1, 'header': 1, 'content': 1, 'define': 1, 'head': 1, 'keywords': 1, 'chapter_name': 1
    }
    
    def perform_vector_search():
        pipeline = [
            {"$vectorSearch": {
                "index": vector_search_index,
                "path": "embedding",
                "queryVector": query_embedding,
                "limit": limit,
                "numCandidates": candidates
            }},
            {"$project": {**project_fields, "vector_score": {"$meta": "vectorSearchScore"}}}
        ]
        results = list(collection.aggregate(pipeline))
        for doc in results:
            doc['combined_score'] = doc.get('vector_score', 0) * 0.7
        return results

    def perform_text_search():
        if not query.strip():
            return []
        
        pipeline = [
            {"$search": {
                "index": atlas_search_index,
                "text": {"query": query, "path": ["chapter_name", "define", "head", "keywords"]}
            }},
            {"$project": {**project_fields, "text_score": {"$meta": "searchScore"}}}
        ]
        results = list(collection.aggregate(pipeline))
        for doc in results:
            doc['combined_score'] = doc.get('text_score', 0) * 0.3
        return results
        

    # Chạy song song hai truy vấn
    with ThreadPoolExecutor(max_workers=2) as executor:
        vector_future = executor.submit(perform_vector_search)
        text_future = executor.submit(perform_text_search)
        all_results = vector_future.result() + text_future.result()

        # Hợp nhất và loại bỏ trùng lặp
    merged_map = {}
    for doc in all_results:
        doc_id = doc['_id']
        if doc_id in merged_map:
            merged_map[doc_id]['combined_score'] += doc['combined_score']
        else:
            merged_map[doc_id] = doc

        # Sắp xếp và giới hạn kết quả
    final_results = sorted(merged_map.values(), 
                             key=lambda x: x.get('combined_score', 0), 
                             reverse=True)[:limit]

    # Convert ObjectId to string for JSON serialization
    for doc in final_results:
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])

    return {
            "status": "success",
            "data": final_results,  # Return original documents with _id field as string
            "formatted_data": [format_string(doc) for doc in final_results],  # Keep formatted version for display
            "message": f"Tìm kiếm thành công - tìm thấy {len(final_results)} tài liệu"
    }

