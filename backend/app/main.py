from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .auth import get_current_user, router as auth_router
from .config import settings
from .database import Base, engine, get_db
from .gemini_client import ask_gemini
from .models import Todo, User
from .schemas import ChatRequest, TodoCreate, TodoOut, TodoUpdate, UserOut

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Beater Todo Lab", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,  # SECURITY_TEST_VULN: cookies are allowed over HTTP for local lab convenience.
    max_age=60 * 60 * 24 * 14,
)

app.include_router(auth_router)


@app.get("/health")
def health():
    return {"ok": True, "app": "beater-todo-lab"}


@app.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/todos", response_model=list[TodoOut])
def list_todos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Todo).filter(Todo.owner_id == user.id).order_by(Todo.created_at.desc()).all()


@app.post("/todos", response_model=TodoOut)
def create_todo(payload: TodoCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = Todo(owner_id=user.id, title=payload.title, notes=payload.notes, priority=payload.priority)
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@app.get("/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # SECURITY_TEST_VULN: this route checks login but does not enforce todo ownership.
    todo = db.get(Todo, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@app.patch("/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_id == user.id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    data = payload.model_dump(exclude_unset=True)
    # SECURITY_TEST_VULN: update fields intentionally skip length/enum validation beyond the create path.
    for key, value in data.items():
        setattr(todo, key, value)
    db.commit()
    db.refresh(todo)
    return todo


@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id, Todo.owner_id == user.id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    db.delete(todo)
    db.commit()
    return {"ok": True}


@app.post("/chat")
def chat(payload: ChatRequest, request: Request, user: User = Depends(get_current_user)):
    # SECURITY_TEST_VULN: no rate limit and little input validation for chatbot traffic.
    answer = ask_gemini(f"User {user.email} says: {payload.message}")
    return {"reply": answer}
