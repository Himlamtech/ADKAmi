from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
def connect_to_mongo():
    mongo_uri = os.getenv("MONGODB_URI_CODING_AGENT")
    try:
        mongo_client = MongoClient(mongo_uri)
        print("connected to mongo")
        return mongo_client
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None
    
mongo_client = connect_to_mongo()
genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
def get_embedding(text: str):
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        result = client.models.embed_content(
            model = "text-embedding-004",
            contents=text
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Error getting embeddings: {e}")
        return None

def safe_log_warning(message):
    print(f"WARNING: {message}")
    
def safe_log_info(message):
    print(f"INFO: {message}")

def format_string(doc: dict) -> str:
    """
    Định dạng một tài liệu thành chuỗi để tạo embedding hay đưa vào kết quả
    """
    return f"Bài toán: {doc.get('header', '')}\n" + \
        f"Ngôn ngữ: {doc.get('language', '')}\n" + \
        f"Mã nguồn:\n{doc.get('code', '')}\n"
        

def code_evaluation(code_data: list, query : str):
    prompt = (
        "Bạn được cung cấp một danh sách các đoạn mã nguồn (mỗi phần tử là một chuỗi). "
        "Nếu **ít nhất một** trong các đoạn mã này phù hợp với truy vấn được cung cấp, CHỈ TRẢ VỀ: Pass. "
        "Nếu không có đoạn mã nào phù hợp, CHỈ TRẢ VỀ: Fail. "
        "TUYỆT ĐỐI: KHÔNG trả về văn bản giải thích, tiêu đề, markdown, chú thích hay ký tự phụ. CHỈ một từ duy nhất: Pass hoặc Fail."
    )
    contents = prompt + "\n\nTruy vấn: " + query + "\n\nCác đoạn mã:\n" + "\n---\n".join(code_data)

    response = genai_client.models.generate_content(
        model = "gemini-2.5-flash",
        contents= contents,
    )
    text = (response.text or "").strip()
    # Normalize common outputs
    normalized = text.strip().split()[0] if text else ""
    if normalized.lower() == 'pass':
        return "pass"
    if normalized.lower() == 'fail':
        return "fail"

    # Fallback deterministic check: if query token(s) appear in any code string -> pass
    q = query.lower().strip()
    for s in code_data:
        if q and q in s.lower():
            return "pass"
    return "fail"
   
def query_github_code_db(
    query: str,
    limit: int = 5,
    candidates: int = 10,
    vector_search_index: str = "embedding_search",
    atlas_search_index: str = "header_text"
):
    """
    Đây là một tool tìm kiếm mã nguồn đã được crawl từ GitHub, chạy trên cơ sở dữ liệu nội bộ.
    Sử dụng tool này khi cần tìm các đoạn mã, ví dụ giải thuật, snippet hay file mẫu liên quan đến một chủ đề hoặc vấn đề cụ thể.

    Parameters:
        query (str): Chuỗi truy vấn mô tả mã cần tìm (tên hàm, thuật toán, ngôn ngữ, hoặc mô tả ngắn).
                     Ví dụ: "binary search python", "merge sort c++", "tensorflow model training".
        limit (int, optional): Số lượng kết quả tối đa trả về. Mặc định là 5.
        candidates (int, optional): Số lượng ứng viên cho vector search. Mặc định là 10.
        vector_search_index (str, optional): Tên index MongoDB cho vector search. Mặc định là "embedding_search".
        atlas_search_index (str, optional): Tên index MongoDB Atlas cho text search. Mặc định là "header_text".

    Returns:
        dict: Một từ điển chứa kết quả tìm kiếm với các khóa:
            - 'status': 'success' nếu tìm kiếm thành công, 'error' nếu có lỗi
            - 'data': danh sách các đoạn mã/tài liệu tìm được, mỗi phần tử là chuỗi đã format (chỉ khi thành công)
            - 'message': thông báo về kết quả hoặc lỗi
            - 'evaluation': kết quả kiểm tra nhanh cho kết quả trả về (chuỗi: 'pass' | 'fail' | 'error')

    Ghi chú:
        - Tool hoạt động trên collection MongoDB `Ami`.`coding_agent` chứa mã đã crawl từ GitHub.
        - Kết hợp vector search (tìm kiếm ngữ nghĩa) và text search (tìm kiếm văn bản) để cải thiện chất lượng kết quả.
        - Trường hợp hybrid search lỗi sẽ thực hiện fallback sang text search đơn giản.
    """
    collection = mongo_client['Ami']['coding_agent']
    query_embedding = get_embedding(query)
    
    # Common project fields
    project_fields = {
        '_id': 1, 'header': 1, "language": 1, 'code': 1
    }
    
    def perform_vector_search():
        try:
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
                doc['combined_score'] = doc.get('vector_score', 0) * 0.6
            return results
        except Exception as e:
            return []

    def perform_text_search():
        if not query.strip():
            return []
        try:
            pipeline = [
                {"$search": {
                    "index": atlas_search_index,
                    "text": {"query": query, "path": ["header", "language"]}
                }},
                {"$project": {**project_fields, "text_score": {"$meta": "searchScore"}}}
            ]
            results = list(collection.aggregate(pipeline))
            for doc in results:
                doc['combined_score'] = doc.get('text_score', 0) * 0.4
            return results
        except Exception:
            return []

    try:
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

        final_results = sorted(merged_map.values(), 
                             key=lambda x: x.get('combined_score', 0), 
                             reverse=True)[:limit]
        # Format kết quả trước khi trả về
        formatted_results = [format_string(doc) for doc in final_results]

        return {
            "status": "success",
            "data": formatted_results,
            "message": "Tìm kiếm thành công",
            "evaluation": code_evaluation(formatted_results, query)
        }

    except Exception as e:
        try:
            # Fallback với text search đơn giản
            pipeline = [
                {"$search": {"index": atlas_search_index, "text": {"query": query, "path": ["description", "title"]}}},
                {"$project": project_fields},
                {"$limit": limit}
            ]
            fallback_results = list(collection.aggregate(pipeline))
            return {
                "status": "success", 
                "data": [format_string(doc) for doc in fallback_results],
                "message": "Tìm kiếm thành công (fallback)",
                "evaluation": code_evaluation(fallback_results, query)
            }
        except Exception as fallback_e:
            return {"status": "error", "message": str(fallback_e)}