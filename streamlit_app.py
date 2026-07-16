import time
import os
import hashlib
import requests
import streamlit as st
from google import genai

client = genai.Client(api_key=st.secrets['GEMINI_KEY'])
NASA_KEY = st.secrets['NASA_KEY']

subjects = ['YouTube Coach', 'Asteroid Tutor', 'Business Tutor', 'NASA Live']

for key, default in [('active_subject', subjects[0]), ('chats', {}), ('ratings', {}),
                     ('points', 0), ('pending_test', None), ('quiz_qs', None),
                     ('quiz_done', 0), ('unlocked', []), ('user', None), ('auth_mode', None)]:
    if key not in st.session_state:
        st.session_state[key] = default

def load_users():
    users = {}
    if os.path.exists('users.csv'):
        for line in open('users.csv', encoding='utf-8').read().splitlines():
            if ',' in line:
                u, h, p = line.split(',')[:3]
                users[u] = (h, int(p))
    return users

def save_user(name, pwhash, pts):
    users = load_users()
    users[name] = (pwhash, pts)
    with open('users.csv', 'w', encoding='utf-8') as f:
        for u, (h, p) in users.items():
            f.write(f'{u},{h},{p}\n')

LOGO = '''<svg width="280" height="80" viewBox="0 0 280 80" xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="nova" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#F72585"/><stop offset="50%" stop-color="#7209B7"/><stop offset="100%" stop-color="#4CC9F0"/>
</linearGradient>
</defs>
<ellipse cx="40" cy="40" rx="32" ry="14" fill="none" stroke="url(#nova)" stroke-width="3" transform="rotate(-20 40 40)"/>
<circle cx="40" cy="40" r="16" fill="url(#nova)"/>
<text x="32" y="48" font-family="Georgia, serif" font-style="italic" font-size="24" font-weight="700" fill="white">N</text>
<circle cx="68" cy="22" r="4" fill="#F72585"/>
<circle cx="12" cy="56" r="3" fill="#4CC9F0"/>
<text x="90" y="45" font-family="Segoe UI, sans-serif" font-size="28" font-weight="800" fill="url(#nova)">NovaClip</text>
<text x="92" y="62" font-family="Segoe UI, sans-serif" font-size="10" letter-spacing="4" fill="#999">LEARN · PLAY · LEVEL UP</text>
</svg>'''

QUESTS = [(100, '⚔️ 1 day free NovaClip Pro'), (450, '⚔️ 1 week free NovaClip Pro'),
          (700, '⚔️ 2 weeks free NovaClip Pro'), (1250, '⚔️ 1 month free NovaClip Pro')]
ACHIEVEMENTS = [(30, '🏅 Reached 30 points'), (100, '🏅 Reached 100 points'),
                (250, '🏅 Reached 250 points'), (500, '🏅 Reached 500 points')]

def check_unlocks():
    pts = st.session_state.points
    for need, name in QUESTS + ACHIEVEMENTS:
        if pts >= need and name not in st.session_state.unlocked:
            st.session_state.unlocked.append(name)
            st.toast(f'UNLOCKED: {name}', icon='🎉')
            st.balloons()

with st.sidebar.expander('⚙️ Settings', expanded=True):
    st.caption('Pick your tutor, theme and more')
    picked = st.radio('Subject', subjects, index=subjects.index(st.session_state.active_subject))
    if picked != st.session_state.active_subject:
        st.session_state.active_subject = picked
        st.rerun()
    theme = st.radio('Background', ['Dark', 'Light', 'Blue', 'Red', 'Green', 'Rainbow'])

subject = st.session_state.active_subject
if subject not in st.session_state.chats:
    st.session_state.chats[subject] = []
history = st.session_state.chats[subject]

with st.sidebar.expander('📜 History', expanded=False):
    empty = True
    for subj in subjects:
        msgs = st.session_state.chats.get(subj, [])
        if msgs:
            empty = False
            stars = st.session_state.ratings.get(subj, 0)
            startxt = '⭐' * stars if stars else 'not rated'
            if st.button(f'{subj} ({len(msgs)} msgs, {startxt})', key=f'hist_{subj}', use_container_width=True):
                st.session_state.active_subject = subj
                st.rerun()
    if empty:
        st.caption('No chats yet - start talking!')

with st.sidebar.expander('⚔️ Quests', expanded=False):
    pts = st.session_state.points
    st.markdown(f'### {pts} points | {st.session_state.quiz_done} quizzes')
    for need, name in QUESTS:
        if pts >= need:
            st.markdown(f'{name} — DONE ✅')
        else:
            st.markdown(f'{name} — {need - pts} pts to go 🔒')

with st.sidebar.expander('🏅 Achievements', expanded=False):
    pts = st.session_state.points
    for need, name in ACHIEVEMENTS:
        if pts >= need:
            st.markdown(f'{name} ✅')
        else:
            st.markdown(f'🔒 Reach {need} points (you have {pts})')

themes = {
    'Dark': ('#0E1117', '#1E2130', '#FAFAFA'),
    'Light': ('#FFFFFF', '#F0F2F6', '#111111'),
    'Blue': ('#0A1A3F', '#14295E', '#D6E4FF'),
    'Red': ('#2B0A0A', '#4A1414', '#FFD6D6'),
    'Green': ('#0A2B14', '#14472A', '#D6FFE0'),
    'Rainbow': ('#1A0A2B', '#2B1450', '#FFFFFF'),
}
bg, box, txt = themes[theme]
inputbg, inputtxt = '#1E2130', '#FAFAFA'

rainbow_css = '''.stApp { background: linear-gradient(135deg, #ff0055, #ff9900, #ffee00, #00cc66, #0099ff, #9900ff) fixed !important; }
[data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background: transparent !important; }''' if theme == 'Rainbow' else ''

st.markdown(f'''<style>
.stApp {{ background-color: {bg}; }}
{rainbow_css}
.stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp label, .stApp span {{ color: {txt}; }}
[data-testid="stSidebar"] {{ background-color: {box}; }}
[data-testid="stSidebar"] button {{ text-align: left; }}
.stApp button p {{ color: {txt} !important; }}
[data-testid="stBaseButton-secondary"] {{ background-color: {box}; border: 1px solid {txt}33; }}
[data-testid="stChatMessage"] {{ background-color: {box}; border-radius: 16px; padding: 14px; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
[data-testid="stChatInput"] textarea {{ background-color: {inputbg}; color: {inputtxt}; caret-color: {inputtxt}; }}
[data-testid="stChatInput"] {{ background-color: {inputbg}; border-radius: 20px; border: 2px solid #7209B7; box-shadow: 0 0 10px rgba(114,9,183,0.45); }}
[data-testid="stBottomBlockContainer"] {{ background-color: {bg}; }}
[data-testid="stHeader"] {{ background-color: {bg}; }}
[data-testid="stBottom"] {{ background-color: {bg}; }}
[data-testid="stBottom"] > div {{ background-color: {bg}; }}
[data-testid="stWidgetLabel"] p {{ color: {txt} !important; font-family: 'Segoe UI', sans-serif; font-weight: 700; font-size: 1.05rem; letter-spacing: 0.5px; }}
div[role="radiogroup"]:has(input[value="⚡ Quick"]) {{ background: linear-gradient({box}, {box}) padding-box, linear-gradient(90deg, #F72585, #7209B7, #4CC9F0) border-box; border: 2px solid transparent; border-radius: 12px; padding: 6px 10px; box-shadow: 0 0 14px rgba(76,201,240,0.45); }}
div[role="radiogroup"]:has(input[value="⚡ Quick"]) label p {{ font-family: Consolas, monospace !important; letter-spacing: 1.5px; text-transform: uppercase; font-size: 0.85rem !important; }}
.vline {{ border-left: 2px solid {txt}55; height: 38px; margin: 0 auto; width: 0; }}
* {{ transition: background-color 0.3s ease, color 0.3s ease; }}
@keyframes shootL {{
  0% {{ transform: translate(0, 0) rotate(0deg); opacity: 1; }}
  100% {{ transform: translate(var(--dx), var(--dy)) rotate(720deg); opacity: 0; }}
}}
.boomL span {{ position: fixed; top: 50vh; left: 20px; font-size: 2rem; animation: shootL 1.8s ease-out forwards; z-index: 9999; }}
.boomR span {{ position: fixed; top: 50vh; right: 20px; font-size: 2rem; animation: shootL 1.8s ease-out forwards; z-index: 9999; }}
</style>''', unsafe_allow_html=True)

def ask_ai(p):
    for m in ['gemini-3.1-flash-lite', 'gemini-3.5-flash', 'gemini-2.5-flash']:
        try:
            return client.models.generate_content(model=m, contents=p).text
        except Exception:
            time.sleep(3)
    return None

if st.session_state.quiz_qs:
    st.markdown(LOGO, unsafe_allow_html=True)
    st.title('📝 QUIZ TIME')
    st.caption('10 points per correct answer!')
    picks = []
    quiz = []
    for line in st.session_state.quiz_qs:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 6:
            quiz.append(parts)
    for i, p in enumerate(quiz):
        st.markdown(f'**Q{i + 1}: {p[0]}**')
        picks.append(st.radio('Pick', ['A) ' + p[1], 'B) ' + p[2], 'C) ' + p[3], 'D) ' + p[4]], key=f'mc_{i}', label_visibility='collapsed'))
    if st.button('✅ Submit', use_container_width=True):
        score = sum(1 for p, pick in zip(quiz, picks) if pick.startswith(p[5].upper()))
        earned = score * 10
        st.session_state.points += earned
        st.session_state.quiz_done += 1
        st.session_state.quiz_qs = None
        check_unlocks()
        if st.session_state.user:
            save_user(st.session_state.user, load_users()[st.session_state.user][0], st.session_state.points)
        st.success(f'{score}/{len(quiz)} correct — +{earned} pts! Total: {st.session_state.points}')
        time.sleep(2)
        st.rerun()
    st.stop()

st.markdown(LOGO, unsafe_allow_html=True)

top1, top2, top3 = st.columns([6, 1, 1])
if st.session_state.user is None:
    with top2:
        if st.button('Log in'):
            st.session_state.auth_mode = 'login'
    with top3:
        if st.button('Sign up'):
            st.session_state.auth_mode = 'signup'
else:
    with top2:
        st.markdown(f'👤 {st.session_state.user}')
    with top3:
        if st.button('Log out'):
            save_user(st.session_state.user, load_users()[st.session_state.user][0], st.session_state.points)
            st.session_state.user = None
            st.session_state.points = 0
            st.rerun()

if st.session_state.auth_mode in ('login', 'signup'):
    with st.form('auth'):
        st.subheader('Log in' if st.session_state.auth_mode == 'login' else 'Sign up')
        name = st.text_input('Username')
        pw = st.text_input('Password', type='password')
        if st.form_submit_button('Go'):
            users = load_users()
            h = hashlib.sha256(pw.encode()).hexdigest()
            if st.session_state.auth_mode == 'signup':
                if name in users:
                    st.error('Username taken!')
                elif name and pw:
                    save_user(name, h, 0)
                    st.session_state.user = name
                    st.session_state.auth_mode = None
                    st.rerun()
            else:
                if name in users and users[name][0] == h:
                    st.session_state.user = name
                    st.session_state.points = users[name][1]
                    st.session_state.auth_mode = None
                    st.rerun()
                else:
                    st.error('Wrong username or password')

st.caption(f'Current chat: {subject} | 🏆 {st.session_state.points} pts')

if subject == 'YouTube Coach':
    raw = open('videos.csv', encoding='utf-8').readlines()
    persona = 'You are NovaClip, a YouTube coach for teen creators 13-18.'
elif subject == 'Asteroid Tutor':
    raw = open('dataset.csv', encoding='utf-8').readlines()
    persona = 'You are NovaClip, a fun space tutor for teens.'
elif subject == 'NASA Live':
    raw = open('nasalive.csv', encoding='utf-8').readlines()
    persona = 'You are NovaClip, a space mission expert for teens. The data shows real asteroids passing Earth this week.'
else:
    raw = open('business.csv', encoding='utf-8').readlines()
    persona = 'You are NovaClip, a business and money tutor for teens.'

for role, text in history:
    with st.chat_message(role):
        st.write(text)

if st.session_state.pending_test:
    st.info('🎯 Test yourself on that answer? Earn 10 points per correct question!')
    ca, cb = st.columns(2)
    with ca:
        if st.button('✅ Accept', use_container_width=True):
            qs = ask_ai('Write exactly 3 multiple choice questions about this text. Format each EXACTLY like: QUESTION | option A | option B | option C | option D | correct letter. One per line, nothing else: ' + st.session_state.pending_test)
            if qs:
                st.session_state.quiz_qs = [l.strip() for l in qs.strip().split('\n') if '|' in l][:3]
            st.session_state.pending_test = None
            st.rerun()
    with cb:
        if st.button('❌ Decline', use_container_width=True):
            st.session_state.pending_test = None
            st.rerun()

if history:
    st.write('Rate this chat:')
    rated = st.feedback('stars', key=f'stars_{subject}')
    if rated is not None:
        st.session_state.ratings[subject] = rated + 1

c1, c2, cd, c3 = st.columns([5, 5, 1, 6])
with c1:
    genz = st.toggle('Gen Z mode')
with c2:
    brit = st.toggle('British mode')
with cd:
    st.markdown('<div class="vline"></div>', unsafe_allow_html=True)
with c3:
    mode = st.radio('Mode', ['⚡ Quick', '🎯 Precise'], horizontal=True, label_visibility='collapsed')

def explosion(emojis):
    left = ''
    right = ''
    for i, e in enumerate(emojis):
        dx = 150 + i * 90
        dy = -(250 + (i % 4) * 110) if i % 2 == 0 else (250 + (i % 4) * 110)
        left += f'<span style="--dx:{dx}px; --dy:{dy}px; animation-delay:0.3s">{e}</span>'
        right += f'<span style="--dx:{-dx}px; --dy:{dy}px; animation-delay:0.3s">{e}</span>'
    st.markdown(f'<div class="boomL">{left}</div><div class="boomR">{right}</div>', unsafe_allow_html=True)

if 'genz_prev' not in st.session_state:
    st.session_state.genz_prev = False
if 'brit_prev' not in st.session_state:
    st.session_state.brit_prev = False
if genz and not st.session_state.genz_prev:
    explosion('🔥💯😎🚀✨🗿💀🤙')
if brit and not st.session_state.brit_prev:
    explosion('🍵☕🫖🍵☕🫖🍵☕')
st.session_state.genz_prev = genz
st.session_state.brit_prev = brit

if brit and genz:
    tone = 'Mix british slang (innit, mate, bloody, cheers, proper) AND gen z slang (fr, no cap, lowkey, W, bet).'
elif brit:
    tone = 'Talk in british slang: innit, mate, bloody, cheers, proper, mental, dodgy, gutted, chuffed.'
elif genz:
    tone = 'Talk in gen z slang: fr, no cap, lowkey, W, bet, vibe - a lot but keep it readable.'
else:
    tone = 'Talk in a normal friendly way.'

if mode == '⚡ Quick':
    data = ''.join(raw[:60])
    length = 'Under 120 words.'
else:
    data = ''.join(raw[:200])
    length = 'Up to 300 words, detailed.'

q = st.chat_input('Ask NovaClip anything...')
if q:
    history.append(('user', q))
    with st.chat_message('user'):
        st.write(q)
    answer = ask_ai(f'{persona} {tone} Use emojis at topic starts. {length} Data: {data} Question: {q}')
    if answer:
        history.append(('assistant', answer))
        st.session_state.pending_test = answer
        space_words = ['asteroid', 'space', 'nasa', 'planet', 'orbit', 'comet', 'moon', 'mars', 'star']
        if any(w in (q + answer).lower() for w in space_words):
            try:
                apod = requests.get('https://api.nasa.gov/planetary/apod', params={'api_key': NASA_KEY}).json()
                if apod.get('media_type') == 'image':
                    history.append(('assistant', '🖼️ Bonus NASA space photo: ' + apod.get('url', '')))
            except Exception:
                pass
    st.rerun()
