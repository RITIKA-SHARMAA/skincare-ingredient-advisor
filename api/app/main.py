import json, logging, uuid
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from .config import settings
from .db import SessionLocal
from .models import Analysis, Ingredient, Product, ProductIngredient, Routine, RoutineItem
from .schemas import *
from .parser import resolve_ingredients
from .llm import get_llm
from .conflicts import routine_conflicts
from .logging_setup import configure_logging

configure_logging(); log=logging.getLogger("api")
@asynccontextmanager
async def lifespan(app): yield
app=FastAPI(title="Skincare Ingredient Advisor API",version="0.1.0",lifespan=lifespan)

def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()

@app.middleware("http")
async def request_context(request: Request, call_next):
    rid=request.headers.get("X-Request-ID",str(uuid.uuid4())); request.state.request_id=rid
    try: response=await call_next(request)
    except Exception: raise
    response.headers["X-Request-ID"]=rid; return response

def problem(status:int,title:str,detail:str): return JSONResponse(status_code=status,content={"type":"about:blank","title":title,"status":status,"detail":detail},media_type="application/problem+json")

@app.exception_handler(HTTPException)
async def http_problem(_:Request, exc:HTTPException): return problem(exc.status_code,"Request failed",str(exc.detail))

@app.get("/health")
def health(): return {"status":"ok"}

@app.post("/analyses",response_model=AnalysisResult)
def analyse(body: AnalysisRequest, db: Session=Depends(db)):
    resolved, unmatched=resolve_ingredients(db,body.ingredient_text)
    if len(resolved)+len(unmatched) > settings.max_ingredients_per_request: raise HTTPException(413,"Too many ingredients")
    base=[{"name":x.name,"function":x.function,"irritant_level":x.irritant_level} for _,x in resolved]
    client=get_llm()
    raw=None
    for attempt in range(2):
        try:
            raw=client.explain(base,body.skin_type)
            results=[IngredientResult.model_validate(x) for x in raw]
            status="ai" if settings.llm_provider.lower()=="vertex" else "fake"
            break
        except Exception as exc:
            log.warning("llm attempt %s failed: %s",attempt + 1,exc)
    else:
        results=[IngredientResult.model_validate(x) for x in __import__("app.llm",fromlist=["FakeLLM"]).FakeLLM().explain(base,body.skin_type)]
        status="fallback"
    payload={"ingredients":[x.model_dump() for x in results],"unmatched":unmatched,"ai_status":status}
    row=Analysis(ingredient_text=body.ingredient_text,skin_type=body.skin_type,ai_status=status,result_json=json.dumps(payload)); db.add(row); db.commit(); db.refresh(row)
    return payload

@app.get("/analyses/{analysis_id}",response_model=AnalysisResult)
def get_analysis(analysis_id:int,db:Session=Depends(db)):
    row=db.get(Analysis,analysis_id)
    if not row: raise HTTPException(404,"Analysis not found")
    return json.loads(row.result_json)

@app.get("/products",response_model=list[ProductOut])
def products(db:Session=Depends(db)):
    return db.scalars(select(Product).order_by(Product.id.desc())).all()
@app.post("/products",response_model=ProductOut)
def create_product(body:ProductCreate,db:Session=Depends(db)):
    p=Product(name=body.name,brand=body.brand,ingredients_text=body.ingredients_text); db.add(p); db.flush()
    resolved,_=resolve_ingredients(db,body.ingredients_text)
    p.ingredients=[ProductIngredient(ingredient=x,position=pos) for pos,x in resolved]
    db.commit(); db.refresh(p); return p
@app.get("/products/{product_id}",response_model=ProductOut)
def get_product(product_id:int,db:Session=Depends(db)):
    p=db.get(Product,product_id)
    if not p: raise HTTPException(404,"Product not found")
    return p
@app.delete("/products/{product_id}")
def delete_product(product_id:int,db:Session=Depends(db)):
    p=db.get(Product,product_id)
    if not p: raise HTTPException(404,"Product not found")
    db.delete(p); db.commit(); return {"deleted":True}

@app.get("/routines",response_model=list[RoutineOut])
def routines(db:Session=Depends(db)): return db.scalars(select(Routine)).all()
@app.post("/routines",response_model=RoutineOut)
def create_routine(body:RoutineCreate,db:Session=Depends(db)):
    r=Routine(name=body.name,skin_type=body.skin_type); db.add(r); db.commit(); db.refresh(r); return r
@app.get("/routines/{routine_id}/conflicts",response_model=list[ConflictOut])
def conflicts(routine_id:int,db:Session=Depends(db)):
    r=db.get(Routine,routine_id)
    if not r: raise HTTPException(404,"Routine not found")
    return routine_conflicts(db,r)
@app.post("/routines/{routine_id}/items")
def add_item(routine_id:int,body:RoutineItemCreate,db:Session=Depends(db)):
    if not db.get(Routine,routine_id): raise HTTPException(404,"Routine not found")
    if not db.get(Product,body.product_id): raise HTTPException(404,"Product not found")
    item=RoutineItem(routine_id=routine_id,product_id=body.product_id,slot=body.slot); db.add(item); db.commit(); return {"id":item.id}
@app.delete("/routines/{routine_id}")
def delete_routine(routine_id:int,db:Session=Depends(db)):
    r=db.get(Routine,routine_id)
    if not r: raise HTTPException(404,"Routine not found")
    db.delete(r); db.commit(); return {"deleted":True}

@app.post("/labels")
async def upload_label(file:UploadFile=File(...)):
    data=await file.read(5*1024*1024+1)
    if len(data)>5*1024*1024: raise HTTPException(413,"Image too large")
    import os, pathlib
    root=pathlib.Path(settings.storage_root); root.mkdir(parents=True,exist_ok=True)
    name=f"{uuid.uuid4()}.bin"; (root/name).write_bytes(data)
    return {"object":"labels/"+name,"local":True,"message":"Local bucket stub stored the image. Vertex extraction is enabled only with the Vertex provider."}
