import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Perfume

app = FastAPI(title="Perfume Shop API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Perfume Shop API is running"}


# Helpers to serialize Mongo docs
class PerfumeOut(BaseModel):
    id: str
    name: str
    brand: str
    description: Optional[str] = None
    price: float
    image: Optional[str] = None
    notes: Optional[List[str]] = None
    category: Optional[str] = None
    gender: Optional[str] = None
    rating: Optional[float] = None
    stock: int

    class Config:
        from_attributes = True


def to_perfume_out(doc) -> PerfumeOut:
    return PerfumeOut(
        id=str(doc.get("_id")),
        name=doc.get("name"),
        brand=doc.get("brand"),
        description=doc.get("description"),
        price=float(doc.get("price", 0)),
        image=doc.get("image"),
        notes=doc.get("notes"),
        category=doc.get("category"),
        gender=doc.get("gender"),
        rating=doc.get("rating"),
        stock=int(doc.get("stock", 0)),
    )


@app.get("/api/perfumes", response_model=List[PerfumeOut])
def list_perfumes(q: Optional[str] = None, limit: int = 50):
    filter_dict = {}
    if q:
        # basic text search on name/brand using regex
        filter_dict = {
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"brand": {"$regex": q, "$options": "i"}},
            ]
        }
    docs = get_documents("perfume", filter_dict, limit)
    return [to_perfume_out(d) for d in docs]


@app.post("/api/perfumes", response_model=dict)
def create_perfume(perfume: Perfume):
    inserted_id = create_document("perfume", perfume)
    return {"id": inserted_id}


@app.get("/api/perfumes/{perfume_id}", response_model=PerfumeOut)
def get_perfume(perfume_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["perfume"].find_one({"_id": ObjectId(perfume_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Perfume not found")
    return to_perfume_out(doc)


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db as _db

        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
