import os, json, math, random, asyncio, subprocess, base64, tempfile
from pathlib import Path
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw, ImageFont
import edge_tts

OUT = Path("output")
OUT.mkdir(exist_ok=True)
W, H = 1080, 1920
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
VOICE = os.getenv("TTS_VOICE", "pt-BR-AntonioNeural")

def groq_script():
    key = os.environ["GROQ_API_KEY"]

    prompt = """
Crie um roteiro ORIGINAL em português brasileiro para um YouTube Short
de 40 a 55 segundos sobre um mistério ou curiosidade REAL e verificável.

Não invente fatos, datas, citações ou descobertas.
Use fontes institucionais, universidades, museus ou publicações científicas.
Retorne SOMENTE JSON válido com:
{
 "title":"título com até 70 caracteres",
 "narration":"narração entre 90 e 125 palavras",
 "description":"descrição curta com fontes e #Shorts",
 "scenes":[
  {"headline":"frase curta","subtext":"explicação visual curta"},
  {"headline":"frase curta","subtext":"explicação visual curta"},
  {"headline":"frase curta","subtext":"explicação visual curta"},
  {"headline":"frase curta","subtext":"explicação visual curta"},
  {"headline":"frase curta","subtext":"explicação visual curta"}
 ],
 "sources":["URL de fonte confiável 1","URL de fonte confiável 2"]
}
"""

    url = "https://api.groq.com/openai/v1/chat/completions"

    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.65,
            "response_format": {"type": "json_object"}
        },
        timeout=90
    )

    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    data = json.loads(raw)

    required = ["title", "narration", "description", "scenes", "sources"]

    if any(k not in data for k in required) or len(data["scenes"]) != 5:
        raise ValueError("Resposta do Groq fora do formato esperado.")

    words = len(data["narration"].split())

    if not 75 <= words <= 145:
        raise ValueError(f"Roteiro fora do tamanho esperado: {words} palavras.")

    return data

def get_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def wrap_text(draw, text, font, max_width):
    words, lines, line = text.split(), [], ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_width:
            line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def make_scene(scene, idx, title):
    random.seed(idx + 77)
    im = Image.new("RGB", (W, H), (7, 10, 22))
    px = im.load()
    # Gradiente escuro original, sem imagens de terceiros.
    for y in range(H):
        t = y / H
        for x in range(W):
            glow = max(0, 1 - math.sqrt(((x-W*0.55)/(W*0.9))**2 + ((y-H*0.34)/(H*0.7))**2))
            px[x,y] = (int(7+12*glow), int(10+18*glow), int(22+34*glow))
    d = ImageDraw.Draw(im, "RGBA")
    # Anéis e pontos abstratos
    for j in range(12):
        x = random.randint(-100, W+100); y = random.randint(100, H-100)
        rad = random.randint(80, 330)
        d.ellipse((x-rad,y-rad,x+rad,y+rad), outline=(85,145,190,35), width=3)
    for j in range(90):
        x=random.randrange(W); y=random.randrange(H)
        d.ellipse((x,y,x+3,y+3), fill=(190,210,230,random.randint(25,90)))
    d.rounded_rectangle((68, 110, W-68, 180), radius=24, fill=(15,25,43,220), outline=(92,145,190,110), width=2)
    d.text((100, 130), "ARQUIVO OCULTO  /  INVESTIGAÇÃO", font=get_font(26, True), fill=(150,195,225,255))
    d.text((78, 440), f"ARQUIVO 0{idx+1}", font=get_font(30, True), fill=(100,190,220,255))
    headline = scene.get("headline", "")
    subtext = scene.get("subtext", "")
    y = 560
    for line in wrap_text(d, headline, get_font(72, True), W-160):
        d.text((78,y), line, font=get_font(72, True), fill=(245,247,250,255), stroke_width=1, stroke_fill=(10,15,25,255))
        y += 94
    y += 45
    for line in wrap_text(d, subtext, get_font(39), W-170):
        d.text((82,y), line, font=get_font(39), fill=(180,198,216,255))
        y += 58
    d.rounded_rectangle((78,H-260,W-78,H-180), radius=18, fill=(17,31,50,220))
    d.text((105,H-240), "MISTÉRIOS • CIÊNCIA • HISTÓRIA", font=get_font(25, True), fill=(145,185,215,255))
    path = OUT / f"scene_{idx+1}.png"
    im.save(path, optimize=True)
    return path

async def make_voice(text, path):
    communicate = edge_tts.Communicate(text, VOICE, rate="+2%")
    await communicate.save(str(path))

def build_video(data):
    audio = OUT / "narration.mp3"
    asyncio.run(make_voice(data["narration"], audio))
    probe = subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(audio)
    ], text=True).strip()
    duration = max(30.0, min(60.0, float(probe)))
    scene_duration = duration / 5
    scenes = [make_scene(s, i, data["title"]) for i,s in enumerate(data["scenes"])]
    cmd = ["ffmpeg","-y"]
    for p in scenes:
        cmd += ["-loop","1","-t",f"{scene_duration:.3f}","-i",str(p)]
    cmd += ["-i",str(audio)]
    filters=[]
    for i in range(5):
        filters.append(
            f"[{i}:v]scale=1200:2134,zoompan=z='min(zoom+0.00035,1.08)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:"
            f"s=1080x1920:fps=30,trim=duration={scene_duration:.3f},setpts=PTS-STARTPTS[v{i}]"
        )
    concat = "".join(f"[v{i}]" for i in range(5))
    filters.append(f"{concat}concat=n=5:v=1:a=0,format=yuv420p[vout]")
    cmd += ["-filter_complex",";".join(filters),"-map","[vout]","-map","5:a",
            "-t",f"{duration:.3f}","-r","30","-c:v","libx264","-preset","veryfast",
            "-crf","23","-c:a","aac","-b:a","128k","-movflags","+faststart",
            str(OUT/"arquivo_oculto_short.mp4")]
    subprocess.run(cmd, check=True)
    (OUT/"metadata.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def upload_to_youtube(data):
    encoded = os.environ.get("YT_TOKEN_JSON_B64")
    if not encoded:
        print("YT_TOKEN_JSON_B64 ausente: vídeo gerado, upload ignorado.")
        return
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    info = json.loads(base64.b64decode(encoded).decode("utf-8"))
    creds = Credentials.from_authorized_user_info(info, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    youtube = build("youtube","v3",credentials=creds)
    body = {
        "snippet": {
            "title": data["title"][:100],
            "description": data["description"][:5000],
            "tags": ["mistérios","curiosidades","história","ciência","Arquivo Oculto"],
            "categoryId": "27"
        },
        "status": {"privacyStatus":"private", "selfDeclaredMadeForKids":False}
    }
    media = MediaFileUpload(str(OUT/"arquivo_oculto_short.mp4"), mimetype="video/mp4", resumable=True)
    result = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    print("Vídeo enviado como privado. ID:", result.get("id"))

def main():
    if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("Configure GROQ_API_KEY nos Secrets do GitHub.")
    data = groq_script()
    build_video(data)
    if os.getenv("YOUTUBE_AUTO_UPLOAD","false").lower() == "true":
        upload_to_youtube(data)
    print("SHORT_PRONTO:", OUT/"arquivo_oculto_short.mp4")

if __name__ == "__main__":
    main()
