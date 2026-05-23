from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import Response
import markdown as md
from weasyprint import HTML as WeasyHTML
import httpx

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.cv import CVProfile, GeneratedCV
from app.schemas.schemas import (
    GenerateRequest, AdjustRequest, GenerateOut, GeneratedCVListItem, ExportPDFRequest
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


@router.post("/export-pdf-content")
async def export_pdf_content(
    body: ExportPDFRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(CVProfile).filter(CVProfile.user_id == current_user.id).first()
    accent = body.accent_color or (profile.accent_color if profile else None) or "#2a5f4b"

    # Converter Markdown para HTML
    html_content = md.markdown(body.content, extensions=['extra'])

    # Template HTML completo com CSS profissional
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<style>
  @page {{
    size: A4;
    margin: 18mm 18mm 18mm 18mm;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    font-family: 'DejaVu Serif', Georgia, serif;
    font-size: 9.5pt;
    line-height: 1.6;
    color: #1a1814;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
  }}

  h1 {{
    font-size: 16pt;
    font-weight: bold;
    color: #1a1814;
    border-bottom: 2px solid {accent};
    padding-bottom: 5px;
    margin-bottom: 4px;
    text-align: left;
  }}

  h2 {{
    font-size: 11pt;
    font-weight: bold;
    color: {accent};
    border-bottom: 1px solid #d4d0ca;
    padding-bottom: 3px;
    margin-top: 14px;
    margin-bottom: 5px;
    text-align: left;
    page-break-after: avoid;
  }}

  h3 {{
    font-size: 9.5pt;
    font-weight: bold;
    color: #1a1814;
    margin-top: 8px;
    margin-bottom: 2px;
    text-align: left;
    page-break-after: avoid;
  }}

  p {{
    margin-bottom: 4px;
    text-align: justify;
    hyphens: auto;
    orphans: 3;
    widows: 3;
  }}

  ul {{
    padding-left: 16px;
    margin-bottom: 4px;
  }}

  li {{
    margin-bottom: 2px;
    text-align: justify;
    hyphens: auto;
  }}

  hr {{
    border: none;
    border-top: 1px solid #d4d0ca;
    margin: 8px 0;
  }}

  a {{
    color: {accent};
    text-decoration: none;
  }}

  strong {{
    font-weight: bold;
  }}

  h2, h3 {{
    page-break-inside: avoid;
  }}

  h2 + *, h3 + * {{
    page-break-before: avoid;
  }}
</style>
</head>
<body>
{html_content}
</body>
</html>"""

    pdf_bytes = WeasyHTML(string=html).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={{
            "Content-Disposition": "attachment; filename=curriculo.pdf"
        }}
    )

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
