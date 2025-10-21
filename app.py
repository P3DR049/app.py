import streamlit as st
import random, time, base64, io
import matplotlib.pyplot as plt
from typing import List, Dict, Optional

# ========= TEMA / CORES =========
NAVY_BG     = "#0B1E3A"   # azul escuro de fundo
BRICK_RED   = "#EF5350"
BRICK_BLUE  = "#42A5F5"
BRICK_YELLOW= "#FDD835"
BRICK_GREEN = "#66BB6A"
BRICK_DARK  = "#0A0F1A"
LEGO_COLORS = [BRICK_RED, BRICK_BLUE, BRICK_YELLOW, BRICK_GREEN]

st.set_page_config(page_title="Roleta Musical FLL", page_icon="🎛", layout="wide")

CSS = f"""
<style>
/* Fundo azul escuro com textura sutil */
body {{
  background: radial-gradient(circle at 8px 8px, rgba(255,255,255,0.06) 1px, transparent 1px) 0 0/20px 20px,
              {NAVY_BG};
  color: #F2F6FC;
}}
/* containers */
.blocky {{
  background:#0F2346;
  border-radius:16px;
  padding:20px;
  box-shadow: 0 10px 24px rgba(0,0,0,.35);
  border: 2px solid rgba(255,255,255,.12);
}}
h1,h2,h3 {{ color:#FFFFFF; font-weight:900; letter-spacing:.3px; }}
hr {{ border:none; border-top:6px dotted rgba(255,255,255,.2); margin:1rem 0; }}
.small {{ color:#BFD3FF; }}

.big-button>button {{
  background: linear-gradient(180deg, {BRICK_YELLOW}, #ffe066);
  border:0; color:#111; font-weight:900; letter-spacing:.5px;
  border-radius:16px; padding:16px 24px;
  box-shadow: 0 6px 0 #b99b19, 0 10px 24px rgba(0,0,0,.35);
}}
.big-button>button:active {{ box-shadow:0 2px 0 #b99b19; transform:translateY(4px); }}

/* chips coloridos */
.tag {{
  display:inline-block; padding:6px 10px; border-radius:12px; font-size:.85rem;
  margin:4px 6px 0 0; border:1px solid rgba(0,0,0,.15);
}}

/* PALCO DA ROLETA */
#wheel-stage {{
  position: relative; width:100%; height: 460px;
  display:flex; align-items:center; justify-content:center;
}}
#wheel-img {{ width:380px; height:380px; object-fit:contain; will-change:transform; }}

/* Ponteiro FIXO em CIMA apontando para DENTRO */
.pointer {{
  position:absolute;
  top: calc(50% - 190px - 10px);    /* centro - raio - folga */
  left: 50%; transform: translateX(-50%);
  width:0; height:0;
  border-left:14px solid transparent; border-right:14px solid transparent;
  border-bottom:24px solid {BRICK_RED};
  filter: drop-shadow(0 2px 2px rgba(0,0,0,.5));
}}

/* Giro contínuo e suave */
@keyframes spinContinuous {{
  from {{ transform: rotate(0deg); }}
  to   {{ transform: rotate(var(--end-rot, 1440deg)); }}
}}
.spin-on {{ animation: spinContinuous var(--spin-duration, 3.5s) cubic-bezier(.2,.9,.2,1) forwards; }}

/* Sidebar mais escura */
section[data-testid="stSidebar"] > div {{ background:#09162E; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ========= ESTADO =========
def init_state():
    if "songs" not in st.session_state:
        st.session_state.songs: List[Dict] = []
    if "last_winner" not in st.session_state:
        st.session_state.last_winner: Optional[Dict] = None
    if "autoplay" not in st.session_state:
        st.session_state.autoplay = True
    if "spin_duration" not in st.session_state:
        st.session_state.spin_duration = 3.5

# ========= HELPERS =========
def wheel_colors(n: int) -> List[str]:
    return [LEGO_COLORS[i % len(LEGO_COLORS)] for i in range(max(1, n))]

def contrast_on(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    y = 0.2126*r + 0.7152*g + 0.0722*b
    return "#000" if y > 160 else "#fff"

def draw_wheel(n_slices: int, highlight_index: int = -1):
    n = max(1, n_slices)
    colors = wheel_colors(n)
    if 0 <= highlight_index < n:
        colors[highlight_index] = "#FFD54F"  # destaque
    # Ponteiro está no TOPO (90°): centralizar setor 0 no topo
    startangle = 90 - (0.5 * 360 / n)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie([1]*n, labels=None, startangle=startangle, colors=colors,
           wedgeprops=dict(width=0.5, edgecolor="white", linewidth=2))
    ax.add_artist(plt.Circle((0,0), 0.2, fc="#0b0f1a"))
    ax.set(aspect="equal"); plt.tight_layout()
    return fig

def fig_to_data_url(fig) -> str:
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=180); plt.close(fig)
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

def wheel_html(img_src: str, duration_s: float = 0.0, end_rot_deg: float = 0.0, animate=False) -> str:
    cls = "spin-on" if animate else ""
    return f"""
<div id="wheel-stage">
  <div class="pointer"></div>
  <img id="wheel-img" src="{img_src}" class="{cls}"
       style="--spin-duration:{duration_s}s; --end-rot:{end_rot_deg}deg;" />
</div>
"""

def render_autoplay_audio(audio_bytes: bytes, mime: str, show_controls: bool = True):
    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    ctrl = "controls" if show_controls else ""
    st.markdown(f'''<audio {ctrl} autoplay>
      <source src="data:{mime};base64,{b64}" type="{mime}">
    </audio>''', unsafe_allow_html=True)

def add_song(title: str, url: str = "", file=None):
    title = (title or "").strip()
    url   = (url or "").strip()
    if not title and file is not None:
        title = (file.name or "Sem título").rsplit(".", 1)[0]
    if not title:
        st.warning("Digite o nome da música ou envie um arquivo."); return
    if any(s["title"].lower() == title.lower() for s in st.session_state.songs):
        st.info("Essa música já está na lista."); return
    audio_bytes, mime = (None, None)
    if file is not None:
        audio_bytes = file.read()
        ext = file.name.lower().rsplit(".", 1)[-1] if "." in file.name else ""
        mime = {"mp3":"audio/mpeg","wav":"audio/wav","ogg":"audio/ogg","m4a":"audio/mp4","aac":"audio/aac"}.get(
            ext, getattr(file, "type", None) or "audio/mpeg"
        )
    st.session_state.songs.append({"title": title, "url": url, "audio": audio_bytes, "mime": mime})

def rename_song(old_title: str, new_title: str):
    new_title = (new_title or "").strip()
    if not old_title or not new_title:
        st.warning("Selecione a música e informe o novo nome."); return
    if any(s["title"].lower() == new_title.lower() for s in st.session_state.songs):
        st.info("Já existe uma música com esse nome."); return
    for s in st.session_state.songs:
        if s["title"] == old_title: s["title"] = new_title; return

def remove_songs(titles: List[str]):
    st.session_state.songs = [s for s in st.session_state.songs if s["title"] not in titles]

# ========= APP =========
init_state()

# --- Navegação (páginas separadas) ---
st.sidebar.title("🎛 Roleta Musical FLL")
page = st.sidebar.radio("Navegar", ["Roleta", "Gerenciar músicas"], index=0)

if page == "Gerenciar músicas":
    st.markdown('<div class="blocky">', unsafe_allow_html=True)
    st.header("🎵 Gerenciar músicas")
    st.caption("Adicione, renomeie e remova. Os arquivos podem ser MP3/WAV/OGG/M4A/AAC.")

    with st.form("add_song_form", clear_on_submit=True):
        c1, c2 = st.columns([1,1])
        with c1:
            title = st.text_input("Nome da música (ou deixe em branco para usar o nome do arquivo)")
            file  = st.file_uploader("Arquivo de áudio (opcional)", type=["mp3","wav","ogg","m4a","aac"])
        with c2:
            url   = st.text_input("Link (opcional)", placeholder="https://...")
        if st.form_submit_button("Adicionar música ➕"):
            add_song(title, url, file)

    st.checkbox("Tocar automaticamente quando sortear", value=st.session_state.autoplay, key="autoplay")

    if st.session_state.songs:
        st.subheader("🧱 Músicas na roleta")
        cols = wheel_colors(len(st.session_state.songs))
        for i, s in enumerate(st.session_state.songs):
            bg = cols[i]; fg = contrast_on(bg)
            st.markdown(f'<span class="tag" style="background:{bg}; color:{fg}">{s["title"]}</span>',
                        unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### ✏ Renomear")
        c1, c2, c3 = st.columns([1.4,1.4,0.8])
        with c1:
            old = st.selectbox("Escolha a música", [s["title"] for s in st.session_state.songs], key="rename_old")
        with c2:
            new = st.text_input("Novo nome", key="rename_new", placeholder="Nome curto")
        with c3:
            if st.button("Renomear ✅"): rename_song(old, new); st.rerun()

        st.markdown("#### 🗑 Remover")
        to_remove = st.multiselect("Selecione para remover", [s["title"] for s in st.session_state.songs])
        if st.button("Remover selecionadas"): remove_songs(to_remove); st.rerun()
    else:
        st.info("Nenhuma música ainda. Adicione pelo menos duas.")

    st.markdown('<div class="small">Dica: as cores dos chips seguem a mesma ordem dos setores na roleta.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------ PÁGINA ROLETA ------------------------
if page == "Roleta":
    st.markdown('<div class="blocky">', unsafe_allow_html=True)
    st.header("🎯 Roleta")
    labels = [s["title"] for s in st.session_state.songs]
    n = max(1, len(labels))

    # estado parado (destaca última vencedora)
    hi = labels.index(st.session_state.last_winner["title"]) if (st.session_state.last_winner and st.session_state.last_winner["title"] in labels) else -1
    still_src = fig_to_data_url(draw_wheel(n, highlight_index=hi))
    wheel_area = st.empty()
    wheel_area.markdown(wheel_html(still_src), unsafe_allow_html=True)

    cA, cB = st.columns([1,1])
    with cA:
        st.markdown('<div class="big-button">', unsafe_allow_html=True)
        spin_clicked = st.button("GIRAR ROLETA 🚀", type="primary", use_container_width=True, disabled=len(labels) < 2)
        st.markdown('</div>', unsafe_allow_html=True)
    with cB:
        st.slider("Duração (s)", 2.0, 8.0, float(st.session_state.spin_duration), 0.5, key="spin_duration")

    st.markdown("---")

    winner = None
    if spin_clicked and len(labels) >= 2:
        idx = random.randrange(len(labels))
        winner = st.session_state.songs[idx]
        st.session_state.last_winner = winner

        final_src = fig_to_data_url(draw_wheel(len(labels), highlight_index=idx))
        full_turns = random.randint(6, 10)   # 6–10 voltas completas
        end_rot    = full_turns * 360

        wheel_area.markdown(
            wheel_html(final_src, duration_s=float(st.session_state.spin_duration), end_rot_deg=end_rot, animate=True),
            unsafe_allow_html=True
        )

        time.sleep(float(st.session_state.spin_duration))
        st.balloons()
    elif st.session_state.last_winner:
        winner = st.session_state.last_winner

    if winner:
        st.subheader("🏆 Música sorteada")
        st.success(f"{winner['title']}")
        if winner.get("audio"):
            if st.session_state.autoplay: render_autoplay_audio(winner["audio"], winner.get("mime") or "audio/mpeg")
            else:                         st.audio(winner["audio"], format=winner.get("mime") or "audio/mpeg")
        if winner.get("url"): st.markdown(f"[Abrir link da música]({winner['url']})")

    st.markdown("</div>", unsafe_allow_html=True)

# Rodapé
st.write("")
st.markdown('<div class="small">Feito para a FLL • Fundo azul-escuro • Páginas separadas</div>', unsafe_allow_html=True)
