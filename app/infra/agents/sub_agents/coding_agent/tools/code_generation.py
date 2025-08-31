from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
def code_generation(query : str):
    """
    Đây là một tool tạo mã nguồn (code generator) dựa trên mô tả của người dùng.
    Sử dụng tool này khi cần tạo đoạn mã, hàm, lớp hoặc file mẫu theo yêu cầu cụ thể.

    Parameters:
        query (str): Mô tả yêu cầu tạo mã do người dùng cung cấp. Có thể bao gồm:
                     - Ngôn ngữ lập trình mong muốn (ví dụ: "python", "javascript")
                     - Yêu cầu về input/output, hiệu năng hoặc thư viện cần dùng
                     - Ví dụ đầu vào/đầu ra hoặc ràng buộc cụ thể

    Returns:
        dict: Một từ điển chứa kết quả với các khóa:
            - 'status': 'success' nếu tạo mã thành công, 'error' nếu có lỗi
            - 'code': mã nguồn (chuỗi) trả về khi thành công
            - 'message': thông báo về kết quả hoặc lỗi

    Important:
        - TOOL PHẢI CHỈ TRẢ VỀ MÃ NGUỒN THUẦN TÚY: KHÔNG có lời dẫn, giải thích, tiêu đề, hay khối markdown.
        - Nếu cần import thư viện, hãy bao gồm các câu lệnh import trong mã trả về.
        - Nếu không xác định ngôn ngữ trong `query`, mặc định trả về mã Python.
    """
    
    prompt = (
        "Bạn là một trình tạo mã. Nhiệm vụ của bạn là: tạo mã nguồn theo yêu cầu mô tả bởi người dùng. "
        "TUYỆT ĐỐI chỉ trả về MÃ NGUỒN THUẦN TÚY, KHÔNG có lời dẫn, giải thích, tiêu đề hay khối mã Markdown. "
        "Không thêm bất kỳ văn bản nào ngoài mã. Nếu cần nhập thư viện/ứng dụng, hãy bao gồm các câu lệnh import trong mã. "
        "Nếu ngôn ngữ được chỉ định trong truy vấn thì phải sử dụng ngôn ngữ đó; nếu không rõ, trả về mã Python. "
        "Hãy đảm bảo mã có thể chạy (có import cần thiết) và phù hợp với yêu cầu."
    )
    contents = prompt + "\n\nYêu cầu: " + query
    try:
        response = genai_client.models.generate_content(
            model = "gemini-2.5-flash",
            contents= contents,
        )
        return {
            "status": "success",
            "code": response.text,
            "message": "Tạo mã thành công"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    