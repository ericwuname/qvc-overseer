"""模拟 Bug #9：空值防御缺失"""


def process_upload(request):
    """处理上传文件 —— BUG：未检查 files 是否为空"""
    
    # BUG: 如果 request.files 为空或 None，这里会崩溃
    uploaded_file = request.files[0]  # IndexError 或 AttributeError
    
    content = uploaded_file.read()
    
    # BUG: content 可能为空，但直接处理
    result = content.decode("utf-8").split("\n")  # NoneType has no attribute decode
    
    return result


def safe_version(request):
    """正确做法：添加空值检查"""
    if not hasattr(request, "files") or not request.files:
        return []
    
    content = request.files[0].read()
    if content is None:
        return []
    
    return content.decode("utf-8").split("\n")
