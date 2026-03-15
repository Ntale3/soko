from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.farmer import FarmerProfile, Farm
from app.schemas import FarmerProfileCreate, FarmerProfileUpdate, FarmerProfileOut, FarmCreate, FarmOut
from app.dependencies import require_farmer
from app.messaging import publish_event

router = APIRouter(prefix="/farmers", tags=["Farmers"])


# ── POST /farmers/profile — create profile after registering in Auth ─
@router.post("/profile", response_model=FarmerProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: FarmerProfileCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    existing = db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")

    profile = FarmerProfile(user_id=user_id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # Publish event for other services to consume
    await publish_event("farmer.registered", {
        "farmer_id": profile.id,
        "user_id": profile.user_id,
        "district": profile.district,
    })

    return profile


# ── GET /farmers/profile — get own profile ───────────────────────────
@router.get("/profile", response_model=FarmerProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ── PATCH /farmers/profile — update own profile ──────────────────────
@router.patch("/profile", response_model=FarmerProfileOut)
def update_profile(
    payload: FarmerProfileUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


# ── GET /farmers/{farmer_id} — public profile (for buyers) ───────────
@router.get("/{farmer_id}", response_model=FarmerProfileOut)
def get_farmer_by_id(farmer_id: int, db: Session = Depends(get_db)):
    profile = db.query(FarmerProfile).filter(FarmerProfile.id == farmer_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return profile


# ── POST /farmers/farms — add a farm ─────────────────────────────────
@router.post("/farms", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
async def add_farm(
    payload: FarmCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Create your farmer profile first")

    farm = Farm(farmer_id=profile.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)

    await publish_event("farm.created", {
        "farm_id": farm.id,
        "farmer_id": profile.id,
        "location": farm.location,
    })

    return farm


# ── GET /farmers/farms/mine — list own farms ─────────────────────────
@router.get("/farms/mine", response_model=list[FarmOut])
def get_my_farms(
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    profile = db.query(FarmerProfile).filter(FarmerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.farms
