import streamlit as st

from translator import (
    LANGUAGES,
    MAX_CHARS,
    MSG_NO_KEY,
    TranslationError,
    create_client,
    get_api_key,
    get_model,
    translate,
)

FLAGS = {"en": "🇺🇸", "ja": "🇯🇵", "vi": "🇻🇳"}

st.set_page_config(page_title="AI 번역기", page_icon="🌐", layout="wide")

# 카드 안 결과 블록을 카드 폭에 맞추고, 긴 문장이 가로 스크롤 없이 줄바꿈되게 한다.
st.markdown(
    """
    <style>
    .stCode pre, .stCode code { white-space: pre-wrap !important; word-break: break-word; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_client():
    return create_client()


MSG_EMPTY = "번역할 텍스트를 입력해주세요."
MSG_TOO_LONG = f"텍스트가 너무 깁니다. {MAX_CHARS}자 이하로 줄여주세요."


def reset_output():
    st.session_state.result = None
    st.session_state.error = None
    st.session_state.warning = None


def clear():
    st.session_state.input_text = ""
    st.session_state.pending = False
    reset_output()


def start_translate():
    # 번역하는 동안 버튼을 끄기 위해, 실제 호출은 다음 실행에서 한다.
    st.session_state.pending = True


st.session_state.setdefault("result", None)
st.session_state.setdefault("error", None)
st.session_state.setdefault("warning", None)
st.session_state.setdefault("pending", False)

with st.sidebar:
    st.header("⚙️ 설정")
    st.markdown(f"**모델:** `{get_model()}`")
    st.divider()
    st.header("📖 사용 방법")
    st.markdown(
        "1. 번역할 텍스트를 입력합니다.\n"
        "2. **번역하기** 버튼을 누릅니다.\n"
        "3. 결과 블록의 복사 아이콘으로 복사합니다."
    )

st.title("🌐 AI 번역기")
st.caption("입력한 텍스트를 영어 · 일본어 · 베트남어로 한 번에 번역합니다.")

has_key = get_api_key() is not None
if not has_key:
    st.error(MSG_NO_KEY + " (.env.example 참고)")

# max_chars를 쓰면 제한을 넘는 붙여넣기가 통째로 무시되므로, 길이는 번역할 때 직접 검사한다.
text = st.text_area(
    "번역할 텍스트",
    key="input_text",
    height=180,
    placeholder="번역할 텍스트를 입력하세요...",
    on_change=reset_output,
)
count = f"{len(text)} / {MAX_CHARS}자"
st.caption(f":red[{count}]" if len(text) > MAX_CHARS else count)

with st.container(horizontal=True):
    st.button(
        "번역하기",
        type="primary",
        icon="🌐",
        disabled=not has_key or st.session_state.pending,
        on_click=start_translate,
    )
    st.button("초기화", icon="🔄", on_click=clear)

if st.session_state.pending:
    st.session_state.pending = False
    reset_output()
    if not text.strip():
        st.session_state.warning = MSG_EMPTY
    elif len(text) > MAX_CHARS:
        st.session_state.warning = MSG_TOO_LONG
    else:
        try:
            with st.spinner("번역 중..."):
                st.session_state.result = translate(text, get_client())
        except TranslationError as e:
            st.session_state.error = str(e)
    st.rerun()  # 꺼 둔 번역하기 버튼을 다시 켠다.

if st.session_state.warning:
    st.warning(st.session_state.warning)
if st.session_state.error:
    st.error(st.session_state.error)

st.divider()

result = st.session_state.result
for col, (code, name) in zip(st.columns(3), LANGUAGES.items()):
    with col, st.container(border=True):
        st.markdown(f"#### {FLAGS[code]} {name}")
        if result:
            st.code(result[code], language=None, wrap_lines=True)
        else:
            st.caption("번역 결과가 여기에 표시됩니다.")
