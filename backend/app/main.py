from fastapi import FastAPI

from backend.app.api.agent import router as agent_router
from backend.app.api.tools import router as tools_router

app = FastAPI(title="AI Agent Workspace")
app.include_router(agent_router)
app.include_router(tools_router)
