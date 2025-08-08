from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes import router

app = FastAPI()
app.include_router(router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")