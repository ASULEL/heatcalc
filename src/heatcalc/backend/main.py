from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="heatcalc API")

# 开发阶段允许Vue本地开发服务器跨域访问（默认 vite 端口 5173）
# 生产环境部署时应收紧成实际的前端域名，而不是用 "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# 注册路由模块
from heatcalc.backend.routers import chat

app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("heatcalc.backend.main:app", host="0.0.0.0", port=8000, reload=True)
