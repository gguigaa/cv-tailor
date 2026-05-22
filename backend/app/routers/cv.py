from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.cv import CVProfile, GeneratedCV
from app.schemas.schemas import (
    GenerateRequest, AdjustRequest, GenerateOut, GeneratedCVListItem
)

router = APIRouter(prefix="/api/cv", tags=["cv"])
settings = get_settings()

DEFAULT_PROMPT = """Você é um especialista em recrutamento técnico e redação de currículos para a área de tecnologia.

Abaixo está o currículo mestre do candidato, que contém TODA a sua experiência:

<curriculo_mestre>
{CV}
</curriculo_mestre>

Abaixo está a descrição da vaga para a qual ele está se candidatando:

<vaga>
{VAGA}
</vaga>

Sua tarefa é gerar um currículo otimizado para essa vaga específica, seguindo estas diretrizes:

1. **Seleção de conteúdo**: Inclua apenas as experiências, projetos e habilidades mais relevantes para essa vaga. Omita o que não contribui para o match.

2. **Palavras-chave ATS**: Use as mesmas palavras-chave e terminologia presentes na descrição da vaga — isso é crítico para passar por sistemas de rastreamento de candidatos.

3. **Linguagem**: Escreva em {IDIOMA}. Mantenha o idioma consistente em todo o documento.

4. **Métricas e impacto**: Preserve e destaque todas as métricas quantitativas do currículo original. Se não há métrica, use verbos de impacto forte.

5. **Tom**: Adapte o tom ao perfil da empresa. Se a vaga é em startup, seja mais dinâmico. Se é em enterprise, seja mais formal.

6. **Formato**: Retorne o currículo em Markdown bem estruturado, com seções claras. Não inclua explicações ou comentários — apenas o currículo pronto.

Gere o currículo agora:"""


def _build_prompt(profile: CVProfile, req: GenerateRequest) -> str:
    base = req.prompt_override or profile.base_prompt or DEFAULT_PROMPT
    cv_content = profile.cv_pt if req.lang == "pt" else profile.cv_en
    if not cv_content:
        raise HTTPException(
            status_code=400,
            detail=f"Master CV em {'português' if req.lang == 'pt' else 'inglês'} não encontrado. Salve-o primeiro no perfil."
        )
    idioma = "português brasileiro" if req.lang == "pt" else "inglês"
    return base.replace("{CV}", cv_content).replace("{VAGA}", req.job_description).replace("{IDIOMA}", idioma)


async def _call_anthropic(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": messages,
            },
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Erro ao chamar a API da Anthropic")
    data = response.json()
    return "".join(b["text"] for b in data["content"] if b["type"] == "text")


@router.post("/generate", response_model=GenerateOut, status_code=201)
async def generate_cv(
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(CVProfile).filter(CVProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Perfil não encontrado")

    prompt = _build_prompt(profile, body)
    result = await _call_anthropic([{"role": "user", "content": prompt}])

    record = GeneratedCV(
        user_id=current_user.id,
        job_description=body.job_description,
        result=result,
        lang=body.lang,
        prompt_used=prompt,
        cv_snapshot=profile.cv_pt if body.lang == "pt" else profile.cv_en,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/adjust", response_model=GenerateOut, status_code=201)
async def adjust_cv(
    body: AdjustRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate original belongs to user
    original = db.query(GeneratedCV).filter(
        GeneratedCV.id == body.generated_cv_id,
        GeneratedCV.user_id == current_user.id,
    ).first()
    if not original:
        raise HTTPException(status_code=404, detail="Currículo não encontrado")

    history = body.conversation_history + [{"role": "user", "content": body.instruction}]
    result = await _call_anthropic(history)

    record = GeneratedCV(
        user_id=current_user.id,
        job_description=original.job_description,
        result=result,
        lang=original.lang,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/history", response_model=list[GeneratedCVListItem])
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.user_id == current_user.id)
        .order_by(GeneratedCV.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        GeneratedCVListItem(
            id=r.id,
            lang=r.lang,
            created_at=r.created_at,
            job_snippet=r.job_description[:80],
        )
        for r in records
    ]


@router.get("/history/{cv_id}", response_model=GenerateOut)
def get_generated_cv(
    cv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(GeneratedCV).filter(
        GeneratedCV.id == cv_id,
        GeneratedCV.user_id == current_user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return record
