import uvicorn
uvicorn.run("genesis.api:app",host="127.0.0.1",port=8766,reload=False)
