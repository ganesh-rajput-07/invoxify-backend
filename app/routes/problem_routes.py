from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.database.connection import get_db
from app.database import models
from app.schemas import problem_schema
from app.routes.dependencies import get_current_user
import uuid

router = APIRouter(prefix="/api/problems", tags=["Problems"])

@router.post("/", response_model=problem_schema.ProblemResponse)
def create_problem(problem: problem_schema.ProblemCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_problem = models.Problem(
        title=problem.title,
        description=problem.description,
        category=problem.category,
        user_id=current_user.id
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)
    return db_problem

@router.get("/", response_model=List[problem_schema.ProblemResponse])
def get_all_problems(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Simple feed, order by newest
    problems = db.query(models.Problem).order_by(desc(models.Problem.created_at)).all()
    
    # Optional logic: Add comment counts, save counts, and is_saved for the current user
    results = []
    for p in problems:
        is_saved = db.query(models.ProblemSave).filter(
            models.ProblemSave.problem_id == p.id,
            models.ProblemSave.user_id == current_user.id
        ).first() is not None
        
        save_count = db.query(models.ProblemSave).filter(models.ProblemSave.problem_id == p.id).count()
        comment_count = db.query(models.ProblemComment).filter(models.ProblemComment.problem_id == p.id).count()
        
        # Build dictionary from model to satisfy Pydantic
        res = {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "category": p.category,
            "user_id": p.user_id,
            "created_at": p.created_at,
            "author": p.author,
            "comments_count": comment_count,
            "saves_count": save_count,
            "is_saved": is_saved,
            "comments": []
        }
        results.append(res)
    return results

@router.get("/{problem_id}", response_model=problem_schema.ProblemResponse)
def get_problem(problem_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        pid = uuid.UUID(problem_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    problem = db.query(models.Problem).filter(models.Problem.id == pid).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem Statement not found")
        
    is_saved = db.query(models.ProblemSave).filter(
        models.ProblemSave.problem_id == problem.id,
        models.ProblemSave.user_id == current_user.id
    ).first() is not None
    
    save_count = db.query(models.ProblemSave).filter(models.ProblemSave.problem_id == problem.id).count()
    comment_count = db.query(models.ProblemComment).filter(models.ProblemComment.problem_id == problem.id).count()
    
    comments = db.query(models.ProblemComment).filter(models.ProblemComment.problem_id == problem.id).order_by(models.ProblemComment.created_at).all()
    proposed_solutions = db.query(models.Idea).filter(models.Idea.problem_id == problem.id).order_by(desc(models.Idea.created_at)).all()
    
    res = {
        "id": problem.id,
        "title": problem.title,
        "description": problem.description,
        "category": problem.category,
        "user_id": problem.user_id,
        "created_at": problem.created_at,
        "author": problem.author,
        "comments_count": comment_count,
        "saves_count": save_count,
        "is_saved": is_saved,
        "comments": comments,
        "proposed_solutions": proposed_solutions
    }
    return res

@router.post("/{problem_id}/comments", response_model=problem_schema.ProblemCommentResponse)
def add_comment(problem_id: str, comment: problem_schema.ProblemCommentCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(problem_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    problem = db.query(models.Problem).filter(models.Problem.id == pid).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem Statement not found")

    new_comment = models.ProblemComment(
        problem_id=pid,
        user_id=current_user.id,
        content=comment.content,
        parent_id=comment.parent_id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment

@router.post("/{problem_id}/save")
def toggle_save_problem(problem_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(problem_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid UUID")

    problem = db.query(models.Problem).filter(models.Problem.id == pid).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem Statement not found")

    existing_save = db.query(models.ProblemSave).filter(
        models.ProblemSave.problem_id == pid,
        models.ProblemSave.user_id == current_user.id
    ).first()

    if existing_save:
        db.delete(existing_save)
        db.commit()
        return {"status": "unsaved"}
    else:
        new_save = models.ProblemSave(
            problem_id=pid,
            user_id=current_user.id
        )
        db.add(new_save)
        db.commit()
        return {"status": "saved"}
