import streamlit as st
import random, time, base64, io
import matplotlib.pyplot as plt
from typing import List, Dict, Optional

# ========= ESTILO LEGO/FLL =========
BRICK_RED   = "#D32F2F"
BRICK_BLUE  = "#1976D2"
BRICK_YELLOW= "#F9A825"
BRICK_GREEN = "#388E3C"
BRICK_GRAY  = "#ECEFF1"
BRICK_DARK  = "#263238"
LEGO_COLORS = [BRICK_RED, BRICK_BLUE, BRICK_YELLOW, BRICK_GREEN]

st.set_page_config(page_title="Roleta Musical FLL", page_icon="🎛", layout="wide")

CSS = f"""
<style>
body {{
  background: radial-gradient(circle at 10px 10px, rgba(0,0,0,0.05) 1px, transparent 1px) 0 0/24px 24px,
              linear-gradient({BRICK_GRAY}, {BRICK_GRAY});
}}
.blocky {{ background:#fff; border-radius:16px; padding:20px; box-shadow:0 10px 24px rgba(0,0,0,.12); border:4px solid {BRICK_BLUE}; }}
.big-button>button {{
  background: linear-gradient(180deg, {BRICK_YELLOW}, #fbd54a);
  border:0; color:#111; font-weight:900; letter-spacing:.5px; border-radius:16px; padding:16px 24px;
  box-shadow: 0 6px 0 #c18f12, 0 10px 24px rgba(0,0,0,.15);
}}
.big-button>button:active {{ box-shadow:0 2px 0 #c18f12; transform:translateY(4px); }}
.tag {{
  display:inline-block; padding:6px 10px; border-radius:12px; font-size:.85rem; margin:4px 6px 0 0;
}}
h1,h2,h3 {{ color:{BRICK_DARK}; font-weight:900; letter-spacing:.3px; }}
hr {{ border:none; border-top:6px dotted {BRICK_RED}; margin:1rem 0; }}

/* PALCO DA ROLETA */
#wheel-stage {{
  position: relative; width:100%; height: 420px;
  display:flex; align-items:center; justify-content:center;
}}
#wheel-img {{ width:360px; height:360px; object-fit:contain; will-change:transform; }}

/* Ponteiro FIXO em CIMA da roleta apontando para DENTRO (para baixo) */
.pointer {{
  position:absolute;
  top: calc(50% - 180px - 8px);    /* centro - raio - folga */
  left: 50%; transform: translateX(-50%);
  width:0; height:0;
  border-left:14px solid transparent; border-right:14px solid transparent;
  border-bottom:22px solid {BRICK_RED};    /* seta para BAIXO, entrando na roleta */
  filter: drop-shadow(0 2px 2px rgba(0,0,0,.25));
}}

/* Giro contínuo e suave: 0deg -> --end-rot */
@keyframes spinContinuous {{
  from {{ transform: rotate(0deg); }}
  to   {{ transform: rotate(var(--end-rot, 1440deg)); }}
}}
.spin-on {{ animation: spinContinuous var(--spin-duration, 3.5s) cubic-bezier(.2,.9,.2,1) forwards; }}
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

# ========= UTIL =========
def add_song(title: str, url: str = "", file=None):
    title = (title or "").strip()
    url = (url or "").strip()
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
        mime = {
            "mp3":"audio/mpeg","wav":"audio/wav","ogg":"audio/ogg","m4a":"audio/mp4","aac":"audio/aac",
        }.get(ext, getattr(file, "type", None) or "audio/mpeg")
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

def wheel_colors(n: int) -> List[str]:
    return [LEGO_COLORS[i % len(LEGO_COLORS)] for i in range(max(1, n))]

def draw_wheel(n_slices: int, highlight_index: int = -1):
    """Disco sem labels; ponteiro fica fora (fixo). Alinhado para ponteiro no TOPO."""
    n = max(1, n_slices)
    colors = wheel_colors(n)
    if 0 <= highlight_index < n: colors[highlight_index] = "#FFD54F"  # destaque claro
    startangle = 90 - (0.5 * 360 / n)   # centro do setor 0 em CIMA (90°)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie([1]*n, labels=None, startangle=startangle, colors=colors,
           wedgeprops=dict(width=0.5, edgecolor="white", linewidth=2))
    ax.add_artist(plt.Circle((0,0), 0.2, fc=BRICK_DARK))
    ax.set(aspect="equal"); plt.tight_layout()
    return fig

def fig_to_data_url(fig) -> str:
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=160); plt.close(fig)
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
    st.markdown(f"""<audio {ctrl} autoplay><source src="data:{mime};base64,{b64}" type="{mime}"></audio>""",
                unsafe_allow_html=True)

def contrast_on(hex_color: str) -> str:
    """preto/branco para legibilidade do chip."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    # luminância aproximada
    y = 0.2126*r + 0.7152*g + 0.0722*b
    return "#000" if y > 160 else "#fff"

# ========= UI =========
init_state()
left, right = st.columns([1,1])

with left:
    st.markdown('<div class="blocky">', unsafe_allow_html=True)
    st.header("🎛 Roleta Musical — FLL")
    st.caption("Adicione músicas, renomeie, gire e deixe o destino escolher!")

    with st.form("add_song_form", clear_on_submit=True):
        title = st.text_input("Nome da música (ou deixe em branco para usar o nome do arquivo)")
        url   = st.text_input("Link (opcional)", placeholder="https://...")
        file  = st.file_uploader("Arquivo de áudio (opcional)", type=["mp3","wav","ogg","m4a","aac"])
        if st.form_submit_button("Adicionar música ➕"):
            add_song(title, url, file)

    st.checkbox("Tocar automaticamente quando sortear", value=st.session_state.autoplay, key="autoplay")

    # Chips coloridos conforme o setor
    if st.session_state.songs:
        st.subheader("🧱 Músicas na roleta")
        cols = wheel_colors(len(st.session_state.songs))
        for i, s in enumerate(st.session_state.songs):
            bg = cols[i]; fg = contrast_on(bg)
            st.markdown(f'<span class="tag" style="background:{bg}; color:{fg}">{s["title"]}</span>',
                        unsafe_allow_html=True)

        st.markdown("#### ✏ Renomear")
        c1, c2, c3 = st.columns([1.2,1.2,0.6])
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

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="blocky">', unsafe_allow_html=True)
    st.header("🎯 Girar")
    labels = [s["title"] for s in st.session_state.songs] if st.session_state.songs else []
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
        st.slider("Duração (s)", 2.0, 6.0, float(st.session_state.spin_duration), 0.5, key="spin_duration")

    st.markdown("---")

    winner = None
    if spin_clicked and len(labels) >= 2:
        idx = random.randrange(len(labels))
        winner = st.session_state.songs[idx]
        st.session_state.last_winner = winner

        final_src = fig_to_data_url(draw_wheel(len(labels), highlight_index=idx))
        full_turns = random.randint(5, 8)             # 5–8 voltas completas
        end_rot    = full_turns * 360                  # termina alinhada ao ponteiro (no topo)

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

st.write("")
st.markdown("<small>Feito para a FLL • Tema LEGO • Streamlit</small>", unsafe_allow_html=True)