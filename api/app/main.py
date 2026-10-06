import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from . import analysis as analysis_service
from .config import Settings, get_settings
from .conflicts import routine_conflicts
from .db import get_db
from .llm import LLMClient, LLMError, VertexGemini
from .logging_setup import configure_logging, request_id_var
from .models import Analysis, Product, ProductIngredient, Routine, RoutineItem
from .parser import IngredientMatcher
from .schemas import (
    AnalysisRequest,
    AnalysisResult,
    ConflictOut,
    LabelAnalysisRequest,
    LabelAnalysisResult,
    LabelUploadRequest,
    LabelUploadTicket,
    ProductCreate,
    ProductOut,
    RoutineCreate,
    RoutineItemCreate,
    RoutineItemOut,
    RoutineOut,
)
from .storage import (
    LabelStorage,
    LocalStorage,
    ObjectNotFound,
    StorageError,
    build_storage,
    mime_type_for,
    new_object_name,
)

configure_logging()
log = logging.getLogger("api")

app = FastAPI(
    title="Skincare Ingredient Advisor API",
    version="0.2.0",
    description="Ingredient analysis, routine conflicts and Gemini-backed explanations. "
    "Illustrative data only, not medical advice.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Request-ID"],
)

DB = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

_llm: LLMClient | None = None


def get_llm() -> LLMClient | None:
    """None means rules-only mode. The Vertex client is created once and reused."""
    global _llm
    settings = get_settings()
    if settings.llm_provider != "vertex":
        return None
    if _llm is None:
        _llm = VertexGemini(settings)
    return _llm


def get_storage() -> LabelStorage:
    return build_storage(get_settings())


LLM = Annotated[LLMClient | None, Depends(get_llm)]
Storage = Annotated[LabelStorage, Depends(get_storage)]


# ---------------------------------------------------------------- errors and middleware


def problem(status_code: int, title: str, detail: object) -> JSONResponse:
    """RFC 7807 problem details."""
    return JSONResponse(
        status_code=status_code,
        content={
            "type": "about:blank",
            "title": title,
            "status": status_code,
            "detail": detail,
            "request_id": request_id_var.get(),
        },
        media_type="application/problem+json",
    )


@app.exception_handler(HTTPException)
async def http_problem(_: Request, exc: HTTPException) -> JSONResponse:
    return problem(exc.status_code, "Request failed", exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_problem(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return problem(422, "Validation failed", errors)


@app.exception_handler(Exception)
async def unhandled_problem(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error")
    return problem(500, "Internal error", "Unexpected error; see logs for the request id.")


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = request_id_var.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-ID"] = request_id
    return response


def not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------- analyses


@app.post("/analyses", response_model=AnalysisResult, status_code=201)
def create_analysis(
    body: AnalysisRequest, db: DB, llm: LLM, settings: AppSettings
) -> AnalysisResult:
    try:
        return analysis_service.analyse(
            db, llm, body.ingredient_text, body.skin_type, settings.max_ingredients_per_request
        )
    except analysis_service.TooManyIngredients as exc:
        raise HTTPException(413, str(exc)) from exc


@app.get("/analyses/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: int, db: DB) -> AnalysisResult:
    row = db.get(Analysis, analysis_id)
    if row is None:
        raise not_found("Analysis")
    result = AnalysisResult.model_validate_json(row.result_json)
    result.id = row.id
    return result


# ---------------------------------------------------------------- products


def product_out(product: Product) -> ProductOut:
    out = ProductOut.model_validate(product)
    out.ingredient_names = [link.ingredient.name for link in product.ingredients]
    return out


def load_product(db: Session, product_id: int) -> Product:
    product = db.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.ingredients).selectinload(ProductIngredient.ingredient))
    )
    if product is None:
        raise not_found("Product")
    return product


@app.get("/products", response_model=list[ProductOut])
def list_products(db: DB) -> list[ProductOut]:
    products = db.scalars(
        select(Product)
        .order_by(Product.id.desc())
        .options(selectinload(Product.ingredients).selectinload(ProductIngredient.ingredient))
    )
    return [product_out(p) for p in products]


@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, db: DB) -> ProductOut:
    product = Product(name=body.name, brand=body.brand, ingredients_text=body.ingredients_text)
    matches, _ = IngredientMatcher(db).resolve(body.ingredients_text)
    seen: set[int] = set()
    for m in matches:
        # A product lists each catalogue ingredient once, at its first position.
        if m.ingredient.id in seen:
            continue
        seen.add(m.ingredient.id)
        product.ingredients.append(ProductIngredient(ingredient=m.ingredient, position=m.position))
    db.add(product)
    db.commit()
    return product_out(load_product(db, product.id))


@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: DB) -> ProductOut:
    return product_out(load_product(db, product_id))


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: DB) -> Response:
    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Product")
    db.delete(product)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- routines


def load_routine(db: Session, routine_id: int) -> Routine:
    routine = db.scalar(
        select(Routine)
        .where(Routine.id == routine_id)
        .options(
            selectinload(Routine.items)
            .selectinload(RoutineItem.product)
            .selectinload(Product.ingredients)
            .selectinload(ProductIngredient.ingredient)
        )
    )
    if routine is None:
        raise not_found("Routine")
    return routine


def routine_out(routine: Routine) -> RoutineOut:
    return RoutineOut(
        id=routine.id,
        name=routine.name,
        skin_type=routine.skin_type,
        items=[
            RoutineItemOut(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name,
                slot=item.slot,
            )
            for item in routine.items
        ],
    )


@app.get("/routines", response_model=list[RoutineOut])
def list_routines(db: DB) -> list[RoutineOut]:
    routines = db.scalars(
        select(Routine)
        .order_by(Routine.id)
        .options(selectinload(Routine.items).selectinload(RoutineItem.product))
    )
    return [routine_out(r) for r in routines]


@app.post("/routines", response_model=RoutineOut, status_code=201)
def create_routine(body: RoutineCreate, db: DB) -> RoutineOut:
    routine = Routine(name=body.name, skin_type=body.skin_type)
    db.add(routine)
    db.commit()
    return routine_out(load_routine(db, routine.id))


@app.get("/routines/{routine_id}", response_model=RoutineOut)
def get_routine(routine_id: int, db: DB) -> RoutineOut:
    return routine_out(load_routine(db, routine_id))


@app.post("/routines/{routine_id}/items", response_model=RoutineOut, status_code=201)
def add_routine_item(routine_id: int, body: RoutineItemCreate, db: DB) -> RoutineOut:
    if db.get(Routine, routine_id) is None:
        raise not_found("Routine")
    if db.get(Product, body.product_id) is None:
        raise not_found("Product")
    db.add(RoutineItem(routine_id=routine_id, product_id=body.product_id, slot=body.slot))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Product is already in this routine") from exc
    return routine_out(load_routine(db, routine_id))


@app.delete("/routines/{routine_id}/items/{item_id}", status_code=204)
def remove_routine_item(routine_id: int, item_id: int, db: DB) -> Response:
    item = db.get(RoutineItem, item_id)
    if item is None or item.routine_id != routine_id:
        raise not_found("Routine item")
    db.delete(item)
    db.commit()
    return Response(status_code=204)


@app.delete("/routines/{routine_id}", status_code=204)
def delete_routine(routine_id: int, db: DB) -> Response:
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise not_found("Routine")
    db.delete(routine)
    db.commit()
    return Response(status_code=204)


@app.get("/routines/{routine_id}/conflicts", response_model=list[ConflictOut])
def get_conflicts(routine_id: int, db: DB) -> list[ConflictOut]:
    return routine_conflicts(db, load_routine(db, routine_id))


# ---------------------------------------------------------------- label photos


@app.post("/labels/upload-url", response_model=LabelUploadTicket, status_code=201)
def create_label_upload(
    body: LabelUploadRequest, storage: Storage, settings: AppSettings
) -> LabelUploadTicket:
    object_name = new_object_name(body.content_type)
    return LabelUploadTicket(
        object_name=object_name,
        upload_url=storage.upload_url(object_name, body.content_type),
        headers={"Content-Type": body.content_type},
        expires_in_seconds=settings.signed_url_minutes * 60,
    )


@app.put("/labels/local/{file_name}", status_code=204)
async def put_local_label(
    file_name: str, request: Request, storage: Storage, settings: AppSettings
) -> Response:
    """Development-only target for upload URLs; Cloud Storage replaces it in GCP."""
    if not isinstance(storage, LocalStorage):
        raise not_found("Upload target")
    object_name = f"labels/{file_name}"
    try:
        expected = mime_type_for(object_name)
    except (KeyError, IndexError) as exc:
        raise not_found("Upload target") from exc
    if request.headers.get("content-type") != expected:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Expected {expected}")
    data = await request.body()
    if len(data) > settings.max_label_bytes:
        raise HTTPException(413, "Label image too large")
    try:
        storage.write(object_name, data)
    except ObjectNotFound as exc:
        raise not_found("Upload target") from exc
    return Response(status_code=204)


@app.post("/labels/analyses", response_model=LabelAnalysisResult, status_code=201)
def analyse_label(
    object_name: str,
    body: LabelAnalysisRequest,
    db: DB,
    llm: LLM,
    storage: Storage,
    settings: AppSettings,
) -> LabelAnalysisResult:
    if llm is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Label reading needs LLM_PROVIDER=vertex; paste the ingredient list instead.",
        )
    try:
        image = storage.read(object_name, settings.max_label_bytes)
    except ObjectNotFound as exc:
        raise not_found("Label image") from exc
    except StorageError as exc:
        raise HTTPException(413, str(exc)) from exc
    try:
        text = llm.extract_ingredients(image, mime_type_for(object_name))
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not read the label") from exc
    if len(text) < 2:
        raise HTTPException(422, "No ingredient list found in the image")
    try:
        result = analysis_service.analyse(
            db, llm, text, body.skin_type, settings.max_ingredients_per_request
        )
    except analysis_service.TooManyIngredients as exc:
        raise HTTPException(413, str(exc)) from exc
    return LabelAnalysisResult(**result.model_dump(), extracted_text=text)
