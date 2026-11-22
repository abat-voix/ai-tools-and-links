from app.main import app
from support_reports.api import router

app.include_router(router)
