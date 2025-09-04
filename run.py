import os

from app.main import app

if __name__ == "__main__":
    # Sanicアプリケーションの実行
    app.run(
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 10000)),
        debug=os.getenv("ENVIRONMENT_CHECK") == "qawsedrftgyhujikolp"
    )
