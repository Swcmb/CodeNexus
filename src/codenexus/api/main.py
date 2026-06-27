"""
API服务器启动脚本

用于启动codenexus Web API服务器。
"""

import uvicorn
from .app import create_app

def main():
    """主函数"""
    app = create_app()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()