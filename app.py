import streamlit as st
import random, time, base64, io
import matplotlib.pyplot as plt
from typing import List, Dict, Optional

# ========= CORES =========
NAVY_BG     = "#00112A"  # azul-escuro puro
WHITE       = "#FFFFFF"
LEGO_COLORS = ["#D32F2F", "#1976D2", "#FBC02D", "#388E3C"]

st.set_page_config(page_title="Roleta Musical FLL", page_icon="🎛", layout="wide")

# ========= ESTILO GLOBAL =========
CSS = f"""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stSidebar"], section.main {{
  background-color: {NAVY_BG} !important;
  color: {WHITE} !important;
}}
label, p, span, div, input, textarea, select {{
  color: {WHITE} !important;
}}
.stButton>button {{
  background: linear-gradient(180deg, #FBC02D, #FDD835);
  color: #111; font-weight:900; border-radius:10px; padding:12px 20px; border:none;
}}
.stButton>button:hover {{
  background: #FFEE58;
}}
.blocky {{
  background: rgba(255,255,255,0.05);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255,255,255,0.2);
}}
h1,h2,h3,h4,h5,h6 {{ color: {WHITE} !important; font-weight:900; }}
.tag {{
  display:inline-block; padding:6px 10px; border-radius:12px;
  font-size:.85rem; margin:4px 6px 0 0;
}}
/* ROLETTA */
#wheel-stage {{
  position: relative; width:100%; height: 460px;
  display:flex; align-items:center; justify-content:center;
}}
#wheel-img {{ width:380px; height:380px; object-fit:contain; will-change:transform; }}
.pointer {{
  position:absolute; top: calc(50% - 190px - 10px);
  left: 50%; transform: translateX(-50%);
  width:0; height:0;
  border-left:14px solid transparent; border-right:14px solid transparent;
  border-bottom:24px solid #FF5252; /* seta vermelha */
}}
@keyframes spinContinuous {{
  from {{ transform: rotate(0deg); }}
  to   {{ transform: rotate(var(--end-rot, 1440deg)); }}
}}
.spin-on {{
  animation: spinContinuous var(--spin-duration, 3.5s) cubic-bezier(.2,.9,.2,1) forwards;
}}
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

# ========= FUNÇÕES =========
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
        colors[highlight_index] = "#FFD54F"
    startangle = 90 - (0.5 * 360 / n)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie([1]*n, labels=None, startangle=startangle, colors=colors,
           wedgeprops=dict(width=0.5, edgecolor="white", linewidth=2))
    ax.add_artist(plt.Circle((0,0), 0.2, fc=NAVY_BG))
    ax.set(aspect="equal"); plt.tight_layout()
    return fig

def fig_to_data_url(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
    plt.close(fig)
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

def render_autoplay_audio(audio_bytes: bytes, mime: str):
    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    st.markdown(f"""
    <audio autoplay controls>
      <source src="data:{mime};base64,{b64}" type="{mime}">
    </audio>""", unsafe_allow_html=True)

def add_song(title: str, url: str = "", file=None):
    title = (title or "").strip()
    url   = (url or "").strip()
    if not title and file is not None:
        title = (file.name or "Sem título").rsplit(".", 1)[0]
    if not title: st.warning("Digite o nome da música ou envie um arquivo."); return
    if any(s["title"].lower() == title.lower() for s in st.session_state.songs):
        st.info("Essa música já está na lista."); return
    audio_bytes, mime = (None, None)
    if file is not None:
        audio_bytes = file.read()
        ext = file.name.lower().rsplit(".", 1)[-1] if "." in file.name else ""
        mime = {"mp3":"audio/mpeg","wav":"audio/wav","ogg":"audio/ogg","m4a":"audio/mp4","aac":"audio/aac"}.get(
            ext, getattr(file, "type", None) or "audio/mpeg")
    st.session_state.songs.append({"title": title, "url": url, "audio": audio_bytes, "mime": mime})

def rename_song(old, new):
    new = (new or "").strip()
    if not old or not new: return
    for s in st.session_state.songs:
        if s["title"] == old: s["title"] = new; return

def remove_songs(titles):
    st.session_state.songs = [s for s in st.session_state.songs if s["title"] not in titles]

# ========= APP =========
init_state()
st.sidebar.title("🎛 Roleta Musical FLL")
page = st.sidebar.radio("Navegar", ["Roleta", "Gerenciar músicas"], index=0)

if page == "Gerenciar músicas":
    st.markdown('<div class="blocky">', unsafe_allow_html=True)
    st.header("🎵 Gerenciar músicas")

    with st.form("add_song_form", clear_on_submit=True):
        title = st.text_input("Nome da música")
        file  = st.file_uploader("Arquivo de áudio", type=["mp3","wav","ogg","m4a","aac"])
        url   = st.text_input("Link (opcional)")
        if st.form_submit_button("Adicionar ➕"): add_song(title, url, file)

    if st.session_state.songs:
        st.subheader("Músicas na roleta")
        cols = wheel_colors(len(st.session_state.songs))
        for i, s in enumerate(st.session_state.songs):
            st.markdown(f'<span class="tag" style="background:{cols[i]};color:{contrast_on(cols[i])}">{s["title"]}</span>', unsafe_allow_html=True)

        st.markdown("---")
        old = st.selectbox("Escolha a música", [s["title"] for s in st.session_state.songs])
        new = st.text_input("Novo nome")
        if st.button("Renomear"): rename_song(old, new); st.rerun()
        st.markdown("---")
        remove = st.multiselect("Selecione para remover", [s["title"] for s in st.session_state.songs])
        if st.button("Remover selecionadas"): remove_songs(remove); st.rerun()
    else:
        st.info("Nenhuma música ainda. Adicione pelo menos duas.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== ROLETA =====================
if page == "Roleta":
    st.markdown('<div class="blocky">', unsafe_allow_html=True)
    st.header("🎯 Roleta Musical")
    labels = [s["title"] for s in st.session_state.songs]
    n = max(1, len(labels))

    hi = labels.index(st.session_state.last_winner["title"]) if (st.session_state.last_winner and st.session_state.last_winner["title"] in labels) else -1
    still_src = fig_to_data_url(draw_wheel(n, highlight_index=hi))
    wheel_area = st.empty()
    wheel_area.markdown(wheel_html(still_src), unsafe_allow_html=True)

    colA, colB = st.columns([1,1])
    with colA:
        spin = st.button("GIRAR ROLETA 🚀", use_container_width=True, disabled=len(labels) < 2)
    with colB:
        st.slider("Duração", 2.0, 8.0, float(st.session_state.spin_duration), 0.5, key="spin_duration")

    winner = None
    if spin and len(labels) >= 2:
        idx = random.randrange(len(labels))
        winner = st.session_state.songs[idx]
        st.session_state.last_winner = winner
        final_src = fig_to_data_url(draw_wheel(len(labels), highlight_index=idx))
        end_rot = random.randint(6, 10) * 360
        wheel_area.markdown(
            wheel_html(final_src, duration_s=float(st.session_state.spin_duration), end_rot_deg=end_rot, animate=True),
            unsafe_allow_html=True)
        time.sleep(float(st.session_state.spin_duration))
        st.balloons()
    elif st.session_state.last_winner:
        winner = st.session_state.last_winner

    if winner:
        st.subheader("🏆 Música sorteada")
        st.success(f"{winner['title']}")
        if winner.get("audio"): render_autoplay_audio(winner["audio"], winner.get("mime") or "audio/mpeg")
        if winner.get("url"): st.markdown(f"[Abrir link da música]({winner['url']})")
    st.markdown("</div>", unsafe_allow_html=True)
