import os
import json
import asyncio
import subprocess
from pathlib import Path

import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# CONFIGURAÇÕES
# ==========================================

OUT = Path("output")
OUT.mkdir(exist_ok=True)

W = 1080
H = 1920

VOICE = os.getenv("TTS_VOICE", "pt-BR-AntonioNeural")

VIDEO_PATH = OUT / "arquivo_oculto_short.mp4"
AUDIO_PATH = OUT / "narracao.mp3"
METADATA_PATH = OUT / "metadata.json"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ==========================================
# GERAR ROTEIRO COM GROQ
# ==========================================

def groq_script():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY não encontrada nos Secrets do GitHub."
        )

    prompt = """
Crie um roteiro ORIGINAL em português brasileiro para um
YouTube Short sobre um mistério ou curiosidade real e verificável.

Regras:
- Entre 90 e 125 palavras na narração.
- Linguagem simples e envolvente.
- Comece com uma frase que desperte curiosidade.
- Explique o assunto sem enrolação.
- Termine com uma conclusão interessante.
- Não invente fatos, datas ou descobertas.
- Não apresente teorias conspiratórias como fatos.
- Não invente endereços de fontes.

Retorne SOMENTE um JSON válido neste formato:

{
  "title": "Título do vídeo",
  "narration": "Texto completo da narração",
  "description": "Descrição do vídeo",
  "scenes": [
    {
      "headline": "Frase curta",
      "subtext": "Explicação curta"
    },
    {
      "headline": "Frase curta",
      "subtext": "Explicação curta"
    },
    {
      "headline": "Frase curta",
      "subtext": "Explicação curta"
    },
    {
      "headline": "Frase curta",
      "subtext": "Explicação curta"
    },
    {
      "headline": "Frase curta",
      "subtext": "Explicação curta"
    }
  ],
  "sources": []
}

Use exatamente cinco cenas.
Se não souber uma fonte confiável, deixe a lista sources vazia.
"""

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.65,
                "response_format": {
                    "type": "json_object"
                }
            },
            timeout=90
        )

        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)

    except requests.RequestException as error:
        raise RuntimeError(
            f"Erro ao conectar com o Groq: {error}"
        ) from error

    except (KeyError, IndexError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Não foi possível interpretar o roteiro: {error}"
        ) from error

    required = [
        "title",
        "narration",
        "description",
        "scenes",
        "sources"
    ]

    for field in required:
        if field not in data:
            raise ValueError(
                f"O roteiro não contém o campo: {field}"
            )

    if len(data["scenes"]) != 5:
        raise ValueError(
            "O roteiro precisa conter exatamente cinco cenas."
        )

    return data

# ==========================================
# FONTES E DESIGN
# ==========================================

def get_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()

def create_background():
    image = Image.new("RGB", (W, H))
    pixels = image.load()

    for y in range(H):
        progress = y / H
        r = int(8 + progress * 8)
        g = int(10 + progress * 5)
        b = int(25 + progress * 18)

        for x in range(W):
            pixels[x, y] = (r, g, b)

    return image

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), test, font=font)[2]

        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines

def draw_centered_text(draw, text, y, font, fill, max_width=850, spacing=25):
    lines = wrap_text(draw, text, font, max_width)

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = (W - width) // 2

        draw.text((x, y), line, font=font, fill=fill)
        y += height + spacing

    return y

# ==========================================
# CRIAR IMAGENS DAS CENAS
# ==========================================

def create_scene(scene, index):
    image = create_background()
    draw = ImageDraw.Draw(image)

    title_font = get_font(38, True)
    headline_font = get_font(72, True)
    subtext_font = get_font(42)

    draw.text(
        (75, 90),
        "ARQUIVO OCULTO",
        font=title_font,
        fill=(160, 165, 190)
    )

    draw.line(
        (75, 155, 1005, 155),
        fill=(75, 85, 120),
        width=3
    )

    draw.text(
        (75, 210),
        f"ARQUIVO Nº 00{index + 1}",
        font=get_font(30),
        fill=(115, 145, 220)
    )

    headline = str(scene["headline"])
    subtext = str(scene["subtext"])

    draw_centered_text(
        draw,
        headline,
        650,
        headline_font,
        (245, 245, 255),
        max_width=880,
        spacing=30
    )

    draw_centered_text(
        draw,
        subtext,
        1050,
        subtext_font,
        (180, 190, 215),
        max_width=850,
        spacing=25
    )

    draw.line(
        (75, 1740, 1005, 1740),
        fill=(75, 85, 120),
        width=3
    )

    draw.text(
        (75, 1780),
        "NEM TUDO É O QUE PARECE.",
        font=get_font(27, True),
        fill=(130, 145, 180)
    )

    path = OUT / f"scene_{index + 1}.png"
    image.save(path)
    return path

# ==========================================
# GERAR NARRAÇÃO
# ==========================================

async def generate_audio(text):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(AUDIO_PATH))

def create_audio(text):
    asyncio.run(generate_audio(text))

# ==========================================
# DESCOBRIR DURAÇÃO DO ÁUDIO
# ==========================================

def get_audio_duration():
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(AUDIO_PATH)
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return float(result.stdout.strip())

# ==========================================
# MONTAR VÍDEO
# ==========================================

def build_video(data):
    print("Criando narração...")
    create_audio(data["narration"])

    duration = get_audio_duration()
    scene_duration = duration / 5

    print("Criando cenas...")
    scene_paths = []

    for index, scene in enumerate(data["scenes"]):
        path = create_scene(scene, index)
        scene_paths.append(path)

    concat_file = OUT / "scenes.txt"

    with open(concat_file, "w", encoding="utf-8") as file:
        for path in scene_paths:
            file.write(f"file '{path.resolve()}'\n")
            file.write(f"duration {scene_duration:.3f}\n")
        file.write(f"file '{scene_paths[-1].resolve()}'\n")

    print("Montando vídeo...")

    command = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-i", str(AUDIO_PATH),
        "-vf", "scale=1080:1920,fps=30,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(VIDEO_PATH)
    ]

    subprocess.run(command, check=True)
    print("Vídeo criado com sucesso!")

# ==========================================
# SALVAR INFORMAÇÕES
# ==========================================

def save_metadata(data):
    metadata = {
        "title": data["title"],
        "description": data["description"],
        "sources": data["sources"],
        "video": str(VIDEO_PATH)
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=4)

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================

def main():
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Configure GROQ_API_KEY nos Secrets do GitHub.")

    print("Iniciando Arquivo Oculto...")

    data = groq_script()

    print("Roteiro criado:")
    print(data["title"])

    build_video(data)
    save_metadata(data)

    print("--------------------------------")
    print("SHORT PRONTO!")
    print(f"Vídeo: {VIDEO_PATH}")
    print(f"Metadados: {METADATA_PATH}")
    print("--------------------------------")

if __name__ == "__main__":
    main()
