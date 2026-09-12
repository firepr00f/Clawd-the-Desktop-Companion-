"""
Clawd's offline vocabulary.

Everything here works with no API key and no internet. Placeholders that get
filled in at runtime: {what} {mins} {task} {due} {course} {streak}

Tone rule for anyone editing this file: Clawd is a gremlin, not a bully. He is
allowed to be dramatic, disappointed, and unbearably smug. He is not allowed to
be cruel about you as a person -- the joke is always about the tab, never about
you being lazy or stupid. The last escalation tier deliberately goes soft.
"""

GREETING = [
    "clawd online. i see everything. get to work",
    "good evening. or morning. i don't have windows",
    "booting up… ok what are we pretending to study today",
    "i'm awake and i'm watching. no pressure",
    "hi :) i'm your problem now",
    "reporting for duty. my duty is judging your tab bar",
]

# --- studying ---------------------------------------------------------------

STUDY_START = [
    "oh?? actual studying?? go on then",
    "ok this is a good tab. i approve",
    "{what} — respectable. carry on",
    "look at you. genuinely",
    "locked in. i'll be quiet. mostly",
]

STUDY_PRAISE = [   # ~15-25 min streak
    "{mins} minutes straight. that's a real streak",
    "{mins} min in and you haven't opened youtube once. suspicious. proud though",
    "steady. keep going, don't look at me",
    "{mins} minutes. this is the version of you i tell other apps about",
    "no notes. literally. you're doing great",
]

STUDY_DEEP = [    # 45+ min
    "{mins} MINUTES. hello?? who is this",
    "ok {mins} minutes is genuinely a lot. drink water",
    "you've been at this {mins} min. blink twice if you're alive",
    "{mins} minutes deep. i'd clap but i have no hands. i have claws",
]

BREAK_SUGGEST = [
    "{mins} min without a break. go look at something 6 meters away for 20 seconds",
    "stretch. seriously. your neck is doing the thing",
    "break time. 5 minutes. i will be counting and i will be strict",
    "water. go. i'll hold your spot",
]

RETURN_TO_STUDY = [
    "OH you came back. i wasn't worried. i was worried",
    "welcome back. we don't have to talk about the last {mins} minutes",
    "there he is. there's my scholar",
    "ok. clean slate. i've forgotten everything (i haven't)",
]

# --- straying ---------------------------------------------------------------

STRAY_NUDGE = [   # tier 1, gentle
    "{what}? hm. ok. i'm noting it",
    "that's not your notes but ok",
    "quick break? i'll allow it. clock's running though",
    "i see the tab. i'm choosing peace. for now",
    "{what} — 2 minutes. i'm timing you btw",
]

STRAY_ANNOYED = [  # tier 2
    "{mins} minutes of {what}. we said 'quick break' {mins} minutes ago",
    "still {what}?? gang.",
    "ok that's {mins} minutes. the pdf is right there. it misses you",
    "i'm not mad i'm just — no actually i'm a little mad",
    "{mins} min. your assignment is aging like milk",
]

STRAY_DISAPPOINTED = [  # tier 3
    "{mins} minutes. i've stopped counting. (i haven't. it's {mins})",
    "you told me you were studying. i believed you. that's on me",
    "{what} for {mins} minutes :( i'm not angry i'm disappointed which is worse",
    "genuinely what is the plan here",
    "{mins} minutes gone. that was a whole lecture's worth",
]

STRAY_CONCERNED = [  # tier 4 -- deliberately kind, not harsher
    "ok real talk, {mins} minutes usually means you're tired or stuck, not lazy. which is it",
    "you've been avoiding it for {mins} min. sometimes that means the task is scary. want to just open it and read one line",
    "{mins} minutes. no lecture from me. just open the file for 5 min and i'll leave you alone",
    "if today's a write-off that's allowed. just tell me and i'll go quiet",
]

STRAY_RECHECK = [   # he looked at your screen again and you're still there
    "ok i looked again. still {what}. {mins} minutes now",
    "checked back in. nothing has changed. {mins} min",
    "{mins} minutes. new video, same problem",
    "i keep looking over and it's still this",
    "update: {mins} min. still not the pdf",
    "another one? that's a whole other video",
    "{mins} minutes deep into {what}. i'm keeping count out loud now",
    "autoplay got you. i can see it happening in real time",
    "still here. still watching. so are you",
]

BRAINROT = [
    "how old are you gang :(",
    "skibidi. in this economy. with a deadline",
    "gang… GANG. put it down",
    "i watched you choose this. willingly",
    "this is what you're spending your one life on. ok",
    "be so fr right now",
    "the algorithm is not your friend. i am your friend. i'm saying close it",
    "0 aura. negative aura. aura debt",
]

GAMING = [
    "one more game. that's what you said. that was 3 games ago",
    "the ranked ladder will be there. the deadline won't",
    "carry your gpa instead",
]

SHOPPING = [
    "buying things doesn't count as productivity. i checked",
    "cart full, assignment empty",
]

SOCIAL = [
    "they're not doing anything interesting. i promise",
    "scrolling is just standing in place with extra steps",
]

# --- idle / afk -------------------------------------------------------------

IDLE = [
    "hello? {mins} min of nothing. did you leave me",
    "you're afk. i'm just going to sit here. alone. it's fine",
    "screen's been still for {mins} minutes. nap or existential crisis",
]

# --- schedule ---------------------------------------------------------------






# --- fun tidbits (offline; API mode generates fresher ones) -----------------

TIDBITS = [
    "tidbit: honey found in Egyptian tombs was still edible. it basically never spoils",
    "tidbit: octopuses have three hearts, and two of them stop when they swim",
    "tidbit: Iceland has no mosquitoes. nobody is entirely sure why",
    "tidbit: bananas are berries. strawberries are not. botany is not okay",
    "tidbit: the shortest war on record lasted 38 minutes. Zanzibar, 1896",
    "tidbit: wombat poo is cube-shaped so it doesn't roll off the rocks they leave it on",
    "tidbit: Oxford University is older than the Aztec Empire. by about 200 years",
    "tidbit: 'set' has more definitions than any other English word. over 400",
    "tidbit: sea otters hold hands while sleeping so they don't drift apart",
    "tidbit: Cleopatra lived closer to the moon landing than to the building of the pyramids",
    "tidbit: a day on Venus is longer than its year. it spins that slowly",
    "tidbit: there are more possible chess games than atoms in the observable universe",
    "tidbit: Scotland's national animal is the unicorn. officially",
    "tidbit: sloths can hold their breath longer than dolphins. about 40 minutes",
    "tidbit: the Eiffel Tower gets about 15cm taller in summer. metal expands",
    "tidbit: Nintendo was founded in 1889, making playing cards",
    "tidbit: a group of flamingos is called a flamboyance. that is the real word",
    "tidbit: the fear of long words is called hippopotomonstrosesquippedaliophobia. yes, really",
    "tidbit: cows have best friends and get stressed when separated from them",
    "tidbit: Norway knighted a penguin. he is a colonel-in-chief now",
    "tidbit: the inventor of the Pringles can is buried in one",
    "tidbit: there's a species of jellyfish that can revert to a juvenile state. biologically immortal",
    "tidbit: Finland has more saunas than cars",
    "tidbit: humans share about 60% of their DNA with bananas",
    "tidbit: the dot over a lowercase i or j is called a tittle",
    "tidbit: Venus is the only planet named after a female Roman god",
    "tidbit: hot water freezes faster than cold under some conditions. nobody fully agrees why",
    "tidbit: a snail can sleep for three years straight",
    "tidbit: the Great Wall is not visible from space with the naked eye. that one is a myth",
    "tidbit: Antarctica is technically the largest desert on earth",
]

# --- quizzing (offline fallback) -------------------------------------------

QUIZ_INTRO = [
    "pop quiz. you can't stop me",
    "ok quick check. no scrolling up",
    "answer this or i get louder",
]

QUIZ_OFFLINE = [
    ("what does a capacitor do to a sudden change in voltage across it?",
     "it resists it — voltage across a cap can't change instantly, current spikes instead"),
    ("in an RC circuit, what's the time constant and what happens at t = τ?",
     "τ = RC; the response has covered about 63.2% of its final change"),
    ("state Kirchhoff's current law in one line.",
     "sum of currents into a node = sum of currents out (charge doesn't pile up)"),
    ("what does the Fourier transform actually give you?",
     "how much of each frequency is present in a signal — amplitude and phase per frequency"),
    ("why is the ideal op-amp assumption 'V+ = V−' valid in negative feedback?",
     "infinite open-loop gain + feedback forces the differential input to ~0 (virtual short)"),
    ("what's the difference between BJT and MOSFET control?",
     "BJT is current-controlled (base current), MOSFET is voltage-controlled (gate voltage, ~no gate current)"),
    ("what does the Laplace variable s represent physically?",
     "complex frequency σ + jω — σ is growth/decay, ω is oscillation"),
    ("in a Bode plot, what does a single pole do to slope and phase?",
     "−20 dB/decade on magnitude, −90° of phase (−45° at the corner)"),
    ("why does maximum power transfer want R_load = R_source?",
     "differentiate power w.r.t. load resistance and set to zero — it peaks at the match (efficiency is only 50% though)"),
    ("what is the depletion region in a pn junction?",
     "the carrier-free zone at the junction where diffused charges recombined, leaving fixed ions and a built-in field"),
]

QUIZ_CORRECT = [
    "correct. show-off",
    "yeah that's it. ok you HAVE been reading",
    "right. i'm putting a star next to your name",
    "correct :) carry on",
]

QUIZ_WRONG = [
    "not quite — {answer}",
    "close-ish. the real answer: {answer}",
    "nope. {answer}. go re-read that bit",
    "hm. {answer} — worth another look",
]

QUIZ_SKIP = [
    "coward. answer: {answer}",
    "fine. it was: {answer}",
]

# --- misc -------------------------------------------------------------------

LATE_NIGHT = [
    "it's past {hour}. sleep is a study technique. genuinely, memory consolidates in sleep",
    "{hour}h. whatever you're cramming, tired-you retains about half of it",
    "late. one more topic then bed, deal?",
]

FAREWELL = [
    "logging off. today: {streak} focused minutes. not bad",
    "bye. {streak} min of study logged. see you tomorrow",
]


# ============================================================================
# 한국어 (Korean)
#
# Not a literal translation — the same character speaking Korean. Casual 반말,
# no formal endings, the joke still aimed at the tab and never at the person.
# The last escalation tier goes soft here too.
#
# Placeholders are identical to the English ones, so nothing else has to change:
# {what} {mins} {task} {due} {course} {streak} {hour} {answer}
# ============================================================================

KO = {
    "GREETING": [
        "클로드 접속. 다 보고 있음. 공부해",
        "안녕. 나는 창문이 없어서 지금 몇 시인지 몰라",
        "부팅 완료… 오늘은 뭘 공부하는 척할 거야",
        "일어났고 보고 있음. 부담 갖지 말고",
        "왔다 :) 이제 내가 니 문제야",
        "출근했음. 내 업무는 니 탭 감시",
    ],
    "STUDY_START": [
        "오?? 진짜 공부?? 계속해봐",
        "이건 좋은 탭이네. 인정",
        "{what} — 훌륭하다. 계속",
        "봐라 이거. 진심으로 잘하고 있어",
        "몰입 시작. 조용히 있을게. 아마도",
    ],
    "STUDY_PRAISE": [
        "{mins}분 연속. 이건 진짜 기록이다",
        "{mins}분째인데 유튜브 한 번도 안 켰네. 수상한데. 자랑스럽다",
        "꾸준하다. 계속해, 나 쳐다보지 말고",
        "{mins}분. 다른 앱들한테 자랑하는 버전의 너다 이게",
        "지적할 게 없다. 진짜로. 잘하고 있어",
    ],
    "STUDY_DEEP": [
        "{mins}분?? 저기요?? 누구세요",
        "{mins}분이면 진짜 많이 한 거야. 물 마셔",
        "{mins}분째 이러고 있네. 살아있으면 두 번 깜빡여",
        "{mins}분 몰입. 박수 쳐주고 싶은데 손이 없어. 집게발은 있음",
    ],
    "BREAK_SUGGEST": [
        "{mins}분 동안 안 쉬었어. 6미터 앞에 있는 거 20초만 봐",
        "스트레칭. 진심이야. 니 목 지금 그거 하고 있어",
        "쉬는 시간. 5분. 내가 세고 있을 거고 엄격할 거야",
        "물. 가. 자리는 내가 지킬게",
    ],
    "RETURN_TO_STUDY": [
        "오 돌아왔네. 걱정 안 했어. 걱정했어",
        "어서 와. 지난 {mins}분 얘기는 안 해도 돼",
        "왔다 내 학자님",
        "자 백지 상태. 다 잊었어 (안 잊음)",
    ],
    "STRAY_NUDGE": [
        "{what}? 흠. 그래. 기록해둘게",
        "그건 니 필기가 아닌데 뭐 그래",
        "잠깐 쉬는 거지? 허락함. 근데 시계는 돌아가고 있어",
        "탭 봤어. 오늘은 평화를 택할게. 일단은",
        "{what} — 2분. 참고로 나 재고 있어",
    ],
    "STRAY_ANNOYED": [
        "{what} {mins}분째. '잠깐만'이라고 한 게 {mins}분 전이야",
        "아직도 {what}?? 야.",
        "{mins}분이야 이거. pdf 바로 거기 있어. 걔가 널 그리워해",
        "화 안 났어 그냥 — 아니 좀 났다",
        "{mins}분. 니 과제가 상해가고 있어",
    ],
    "STRAY_DISAPPOINTED": [
        "{mins}분. 세는 거 그만뒀어. (안 그만둠. {mins}분이야)",
        "공부한다며. 믿었잖아. 내 잘못이지",
        "{what} {mins}분 :( 화난 게 아니라 실망한 거야 그게 더 나빠",
        "진짜 계획이 뭐야 지금",
        "{mins}분 날아갔다. 강의 하나 통째로였는데",
    ],
    "STRAY_CONCERNED": [
        "솔직히 {mins}분이면 보통 게으른 게 아니라 지쳤거나 막힌 거야. 뭐야 둘 중에",
        "{mins}분째 피하고 있네. 그건 보통 그 일이 무섭다는 뜻이야. 그냥 열어서 한 줄만 읽어볼래",
        "{mins}분. 잔소리 안 할게. 파일만 5분 열어두면 조용히 있을게",
        "오늘 망한 날이면 그것도 괜찮아. 말만 해주면 조용히 있을게",
    ],
    "STRAY_RECHECK": [
        "다시 봤어. 아직도 {what}. 이제 {mins}분",
        "다시 확인함. 바뀐 게 없어. {mins}분",
        "{mins}분. 영상만 바뀌고 문제는 그대로",
        "자꾸 쳐다보는데 계속 이거네",
        "속보: {mins}분. 아직 pdf 아님",
        "또 하나? 그거 완전 다른 영상이잖아",
        "{what} {mins}분째. 이제 소리 내서 셀 거야",
        "자동재생한테 잡혔네. 실시간으로 보인다",
        "아직 여기 있고. 아직 보고 있어. 너도",
    ],
    "BRAINROT": [
        "너 몇 살이야 진짜 :(",
        "스키비디. 이 시국에. 마감 두고",
        "야… 야. 그거 내려놔",
        "니가 저걸 고르는 걸 내가 봤어. 자발적으로",
        "한 번뿐인 인생을 저기에 쓰는구나. 그래",
        "제발 진지해져 봐",
        "알고리즘은 니 친구가 아니야. 내가 니 친구야. 그래서 끄라고 하는 거야",
        "아우라 0. 마이너스. 아우라 빚졌어",
    ],
    "GAMING": [
        "한 판만. 그렇게 말했지. 세 판 전에",
        "랭크는 도망 안 가. 마감은 도망가",
        "학점을 캐리해",
    ],
    "SHOPPING": [
        "사는 건 생산성이 아니야. 확인해봤어",
        "장바구니는 가득, 과제는 텅",
    ],
    "SOCIAL": [
        "쟤네 별거 안 해. 진짜야",
        "스크롤은 제자리걸음인데 손가락만 바쁜 거야",
    ],
    "IDLE": [
        "여보세요? {mins}분째 아무것도 안 하네. 나 두고 갔어?",
        "자리 비웠네. 나는 그냥 여기 앉아있을게. 혼자. 괜찮아",
        "{mins}분째 화면이 멈춰있어. 낮잠이야 현타야",
    ],
    "TIDBITS": [
        "잡지식: 이집트 무덤에서 나온 꿀이 아직 먹을 수 있었대. 꿀은 사실상 안 상해",
        "잡지식: 문어는 심장이 세 개고, 헤엄칠 땐 그중 두 개가 멈춰",
        "잡지식: 아이슬란드엔 모기가 없어. 이유는 아직 아무도 확실히 몰라",
        "잡지식: 바나나는 베리인데 딸기는 아니야. 식물학은 정상이 아니야",
        "잡지식: 기록상 가장 짧은 전쟁은 38분이었어. 1896년 잔지바르",
        "잡지식: 웜뱃 똥은 정육면체야. 바위 위에 놔둬도 안 굴러떨어지게",
        "잡지식: 옥스퍼드 대학이 아즈텍 제국보다 오래됐어. 200년쯤",
        "잡지식: 영어에서 뜻이 가장 많은 단어는 'set'이야. 400개 넘어",
        "잡지식: 해달은 잘 때 서로 손을 잡아. 떠내려가지 않으려고",
        "잡지식: 클레오파트라는 피라미드 건설보다 달 착륙에 더 가까운 시대를 살았어",
        "잡지식: 금성은 하루가 1년보다 길어. 그만큼 느리게 돌아",
        "잡지식: 체스 게임 경우의 수가 관측 가능한 우주의 원자 수보다 많아",
        "잡지식: 스코틀랜드 국가 동물은 유니콘이야. 공식적으로",
        "잡지식: 나무늘보는 돌고래보다 오래 숨을 참아. 40분쯤",
        "잡지식: 에펠탑은 여름에 15cm 정도 키가 커져. 쇠가 늘어나서",
        "잡지식: 닌텐도는 1889년에 화투 만들면서 시작했어",
        "잡지식: 홍학 무리를 부르는 단어는 'flamboyance'야. 진짜 그 단어야",
        "잡지식: 긴 단어 공포증의 이름이 34글자야. 일부러 그렇게 지은 거 맞아",
        "잡지식: 소도 절친이 있어서, 떨어뜨려 놓으면 스트레스를 받아",
        "잡지식: 노르웨이가 펭귄한테 기사 작위를 줬어. 지금 대령이야",
        "잡지식: 프링글스 통을 발명한 사람은 프링글스 통에 묻혔어",
        "잡지식: 어린 상태로 되돌아갈 수 있는 해파리가 있어. 생물학적으로 불멸이야",
        "잡지식: 핀란드엔 자동차보다 사우나가 많아",
        "잡지식: 사람은 바나나랑 DNA를 60% 정도 공유해",
        "잡지식: 소문자 i랑 j 위의 점은 'tittle'이라는 이름이 있어",
        "잡지식: 로마 신 이름을 딴 행성 중 여신은 금성 하나뿐이야",
        "잡지식: 어떤 조건에선 뜨거운 물이 찬 물보다 빨리 얼어. 이유는 아직 논쟁 중",
        "잡지식: 달팽이는 3년을 내리 잘 수 있어",
        "잡지식: 만리장성은 맨눈으로 우주에서 안 보여. 그건 헛소문이야",
        "잡지식: 남극이 지구에서 제일 큰 사막이야. 기술적으로",
    ],
    "QUIZ_INTRO": [
        "깜짝 퀴즈. 못 막아",
        "빠르게 확인 좀. 위로 스크롤 금지",
        "이거 답해. 아니면 더 시끄러워질 거야",
    ],
    "QUIZ_CORRECT": [
        "정답. 잘난 척쟁이",
        "그래 그거야. 진짜로 읽고 있었구나",
        "맞았어. 니 이름 옆에 별 하나 붙여둘게",
        "정답 :) 계속해",
    ],
    "QUIZ_WRONG": [
        "아쉽다 — {answer}",
        "비슷했어. 진짜 답: {answer}",
        "땡. {answer}. 그 부분 다시 읽어봐",
        "흠. {answer} — 한 번 더 볼 만해",
    ],
    "QUIZ_SKIP": [
        "겁쟁이. 답: {answer}",
        "그래 알았어. 답은: {answer}",
    ],
    "LATE_NIGHT": [
        "{hour}시 넘었어. 잠도 공부법이야. 진짜로 기억은 자면서 굳어",
        "{hour}시. 뭘 벼락치기하든 피곤한 너는 절반쯤만 기억해",
        "늦었다. 한 챕터만 더 하고 자기, 콜?",
    ],
    "FAREWELL": [
        "종료. 오늘 집중 {streak}분. 나쁘지 않아",
        "잘 가. 공부 {streak}분 기록됨. 내일 봐",
    ],
    # (question, ideal answer) — the answer text is shown to you when you skip
    "QUIZ_OFFLINE": [
        ("커패시터는 양단 전압이 갑자기 변하려 할 때 어떻게 반응해?",
         "저항해 — 커패시터 전압은 순간적으로 못 변하고, 대신 전류가 튄다"),
        ("RC 회로의 시정수는 뭐고 t = τ에서 무슨 일이 일어나?",
         "τ = RC. 최종 변화량의 약 63.2%까지 진행된 상태"),
        ("키르히호프 전류법칙을 한 줄로 말해봐.",
         "한 노드로 들어가는 전류의 합 = 나오는 전류의 합 (전하는 쌓이지 않는다)"),
        ("푸리에 변환이 실제로 알려주는 게 뭐야?",
         "신호에 각 주파수가 얼마나 들어있는지 — 주파수별 크기와 위상"),
        ("부귀환에서 이상적 연산증폭기의 'V+ = V−' 가정이 왜 성립해?",
         "개방루프 이득이 무한대라 귀환이 차동입력을 0으로 만든다 (가상 단락)"),
        ("BJT와 MOSFET의 제어 방식 차이는?",
         "BJT는 전류 제어(베이스 전류), MOSFET은 전압 제어(게이트 전압, 게이트 전류 거의 0)"),
        ("라플라스 변수 s가 물리적으로 뭘 뜻해?",
         "복소 주파수 σ + jω — σ는 증가/감쇠, ω는 진동"),
        ("보드 선도에서 극점 하나는 기울기와 위상에 어떤 영향을 줘?",
         "크기는 −20 dB/decade, 위상은 −90° (코너에서 −45°)"),
        ("최대 전력 전달에서 왜 R_load = R_source여야 해?",
         "부하 저항으로 전력을 미분해서 0으로 두면 정합점에서 최대 (효율은 50%뿐이지만)"),
        ("pn 접합의 공핍층이 뭐야?",
         "확산된 전하가 재결합해 캐리어가 없어진 접합부 영역. 고정 이온과 내부 전계가 남는다"),
    ],
}

# ---------------------------------------------------------------------------

LANGUAGES = ("en", "ko")


def _english() -> dict:
    """Every uppercase list in this module, as a name -> lines dict."""
    return {k: v for k, v in globals().items()
            if k.isupper() and isinstance(v, list) and k not in ("LANGUAGES",)}


EN = _english()


def pool(name: str, lang: str = "en") -> list:
    """
    The lines for `name` in `lang`, falling back to English.

    Falling back rather than failing means a half-translated bank still runs:
    add a Korean key and it is used, leave it out and you get the English one.
    """
    if lang == "ko":
        got = KO.get(name)
        if got:
            return got
    return EN.get(name) or KO.get(name) or []


def missing(lang: str = "ko") -> list[str]:
    """Names that have no translation yet — used by the tests."""
    table = KO if lang == "ko" else EN
    return sorted(k for k in EN if k not in table)


# ---------------------------------------------------------------------------
# Idle chatter: the same window, still there, five minutes later.
# No screenshot, no API call — he just keeps you company on a timer.
# {what} is the window/topic he last recognised.

KEEP_STUDY = [
    "still going. good",
    "you're doing it. i'll shut up",
    "{what} — still at it. respect",
    "no notes. keep going",
    "i'm just watching. this is nice",
    "steady. i like this version of you",
]

KEEP_STRAY = [
    "study. please",
    "still {what}. i'm still here",
    "hey. the pdf. remember it",
    "i'm not going anywhere until you switch tabs",
    "this is the same tab as five minutes ago",
    "go on. one page. that's all i'm asking",
]

KEEP_NEUTRAL = [
    "still here. what are we doing",
    "nothing's happening. that's fine i guess",
    "waiting. patiently. mostly",
]

KO.update({
    "KEEP_STUDY": [
        "열심히 하고 있어",
        "잘하고 있어. 조용히 있을게",
        "{what} — 계속 하고 있네. 인정",
        "지적할 거 없음. 계속해",
        "그냥 보고만 있을게. 보기 좋다",
        "꾸준하다. 이 버전의 너 좋아",
    ],
    "KEEP_STRAY": [
        "공부하라고....",
        "아직도 {what}. 나 아직 여기 있어",
        "야. pdf. 기억나?",
        "탭 바꿀 때까지 안 갈 거야",
        "5분 전이랑 똑같은 화면인데",
        "한 페이지만. 그거면 돼",
    ],
    "KEEP_NEUTRAL": [
        "아직 여기 있어. 뭐 하는 중이야?",
        "아무 일도 안 일어나네. 뭐 괜찮아",
        "기다리는 중. 인내심 있게. 대충",
    ],
})

# ---------------------------------------------------------------------------
# Ten minutes without the mouse moving. Fireworks, then one of these.

WAKE_UP = [
    "🎆 hey. ten minutes of nothing. still alive?",
    "that's ten minutes without moving. blink twice",
    "fireworks because i couldn't think of anything else. come back",
    "ten minutes still. either you're deep in a book or you left",
]

KO.update({
    "WAKE_UP": [
        "🎆 야. 10분째 아무것도 안 움직였어. 살아있어?",
        "10분 동안 미동도 없었어. 두 번 깜빡여봐",
        "불꽃놀이. 딴 방법이 안 떠올랐어. 돌아와",
        "10분째 그대로다. 책에 빠졌거나 자리를 떴거나",
    ],
})

EN = _english()          # rebuild, now that the new pools exist

# ---------------------------------------------------------------------------
# Double-click: he looks at your screen and calls it. Three ways it can land.
# Used when there is no API key, or the model came back without a line.
# {what} is what he managed to make out, or "" if he could not tell.

CHECK_STUDY = [
    "ok. you're actually working. carry on",
    "{what}. yeah, that counts. good",
    "checked. you're fine. i'll go away",
    "nothing to nag about. annoying, honestly",
    "still on it. i had a whole speech ready. wasted",
]

CHECK_STRAY = [
    "that is not studying and we both know it",
    "{what}. really. in the middle of the day",
    "i looked. i regret looking",
    "wow. ok. put it away",
    "this is what you switched to? bold",
    "not the pdf. not even close to the pdf",
]

CHECK_UNSURE = [
    "...are you actually studying right now",
    "i can't tell what this is. explain yourself",
    "{what}? is that studying? be honest",
    "hm. this could go either way. which is it",
    "i genuinely cannot call this one. help me out",
]

KO.update({
    "CHECK_STUDY": [
        "인정. 진짜 하고 있네. 계속해",
        "{what}. 응 이건 공부 맞다",
        "확인 완료. 문제 없음. 갈게",
        "잔소리할 게 없네. 솔직히 좀 아쉽다",
        "아직 하고 있구나. 할 말 준비했는데 아깝다",
    ],
    "CHECK_STRAY": [
        "이건 공부 아니야. 너도 알잖아",
        "{what}. 진짜로? 이 시간에?",
        "봤어. 안 볼 걸 그랬어",
        "와. 그래. 그만 봐",
        "이거 보려고 창을 바꾼 거야? 대단하다",
        "pdf 아니잖아. 근처도 아니야",
    ],
    "CHECK_UNSURE": [
        "...너 지금 진짜 공부하는 거 맞아?",
        "이게 뭔지 모르겠는데. 설명해봐",
        "{what}? 이게 공부야? 솔직히 말해",
        "음. 이건 애매한데. 뭐야 이거",
        "이건 진짜 판단이 안 서네. 도와줘",
    ],
})

EN = _english()          # rebuild, now that the new pools exist

# ---------------------------------------------------------------------------
# Sites and apps he reacts to on sight, by name, with no warm-up.
# {what} is what he caught you on — "YouTube", "Steam", "TikTok".

HATED_OPEN = [
    "{what}. no. close it",
    "oh, {what} is open. cool. cool cool cool",
    "not even a full minute before {what}. impressive",
    "{what}? we JUST started",
    "i saw that. {what}. i'm writing it down",
    "{what} again. at this point it's a hobby",
    "absolutely not. {what}. go back",
    "opening {what} is a decision and you made it in front of me",
]

KO.update({
    "HATED_OPEN": [
        "{what}. 아니. 닫아",
        "아 {what} 켰네. 그래. 그래그래",
        "1분도 안 돼서 {what}. 대단하다",
        "{what}? 방금 시작했잖아",
        "봤어. {what}. 적어놓을게",
        "또 {what}이야. 이쯤 되면 취미지",
        "절대 안 돼. {what}. 돌아가",
        "{what} 켜는 건 선택이고 넌 내 앞에서 그걸 했어",
    ],
})

EN = _english()          # rebuild, now that the new pools exist

# ---------------------------------------------------------------------------
# He was cross about this window, looked properly, and it turned out to be
# coursework. The anger comes off and stays off for that window.

PARDON = [
    "oh. it's an actual lecture. my mistake, carry on",
    "fine. that IS studying. i'll stop",
    "ok i looked and i was wrong. as you were",
    "huh. {what}. i take it back",
    "withdrawn. i'll leave this tab alone",
    "alright, that counts. i'll shut up about it",
    "my bad. lecture on youtube is still a lecture",
]

KO.update({
    "PARDON": [
        "아 진짜 강의네. 내가 잘못했다, 계속해",
        "인정. 이건 공부 맞네. 그만할게",
        "확인해보니 내가 틀렸어. 하던 거 해",
        "오. {what}. 취소할게",
        "철회. 이 탭은 안 건드릴게",
        "그래, 이건 쳐준다. 조용히 있을게",
        "미안. 유튜브에 있어도 강의는 강의지",
    ],
})

EN = _english()          # rebuild, now that the new pools exist


# ---------------------------------------------------------------------------
# --- schedule: deadlines, classes and the todo list -------------------------

DUE_TODAY = [
    "‼ {task} is due TODAY. that's today. this day",
    "{task} — due today. i'd start now if i were you and i basically am",
    "reminder: {task}, due today, currently not done",
    "{task}. today. {due} left. i'll stop talking now",
]

DUE_SOON = [
    "{task} is due in {due}. just so it's in your head",
    "heads up — {task}, {due} away",
    "{due} until {task}. plenty of time. said everyone ever",
]

OVERDUE = [
    "{task} was due {due} ago. we need to talk about it",
    "still not done: {task}. it's been {due}",
    "{task}. {due} past. i'm not angry, i'm — no, i am a bit",
]

TODO_POKE = [
    "have you emailed about this yet — {task}",
    "{task}. still sitting there. still pending",
    "small thing: {task}. takes 5 minutes. has taken you 5 days",
    "did you actually do {task} or did you just think about doing it",
]

CLASS_SOON = [
    "{course} starts in {due}. move",
    "{course} in {due}. are you dressed",
    "{due} until {course}. i'm just the messenger",
]

KO.update({
    "DUE_TODAY": [
        "‼ {task} 오늘 마감. 오늘. 바로 이 날",
        "{task} — 오늘까지야. 나라면 지금 시작해. 사실상 나야 지금",
        "알림: {task}, 오늘 마감, 현재 안 함",
        "{task}. 오늘이야. {due} 남았어. 말 그만할게",
    ],
    "DUE_SOON": [
        "{task} 마감 {due} 남았어. 머리에 넣어두라고",
        "미리 말해줌 — {task}, {due} 남음",
        "{task}까지 {due}. 시간 충분하지. 다들 그렇게 말했지",
    ],
    "OVERDUE": [
        "{task} 마감 {due} 지났어. 이거 얘기 좀 하자",
        "아직 안 함: {task}. {due} 됐어",
        "{task}. {due} 지남. 화 안 났어. 아니 좀 났어",
    ],
    "TODO_POKE": [
        "이거 메일 보냈어? — {task}",
        "{task}. 아직 그대로 있네. 아직 대기중",
        "작은 거: {task}. 5분이면 되는데 5일째야",
        "{task} 진짜 한 거야 아니면 할 생각만 한 거야",
    ],
    "CLASS_SOON": [
        "{course} {due} 후에 시작. 움직여",
        "{course} {due} 남음. 옷은 입었어?",
        "{course}까지 {due}. 난 전달만 할게",
    ],
})

EN = _english()          # rebuild, now that the new pools exist
