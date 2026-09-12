"""
16x16 pixel items Clawd holds up next to himself.

Two sources:
  * the built-in set below — instant, always on-model, no network
  * API-generated grids for topics the built-in set doesn't cover, cached to
    items_cache.json so each topic costs one call ever

Grid format: 16 strings of 16 characters, one character per pixel, using the
palette keys below. '.' is transparent. Easy to edit by hand — just draw.

Why 16 and not 8: at 8x8 there are 64 pixels total, and after you spend an
outline on the silhouette there is nothing left to say what the thing IS. A
capacitor and a resistor came out as the same grey smudge. 16x16 is four times
the area and is the smallest size at which a generated icon is reliably
recognisable. It is drawn at half a Clawd-pixel per item-pixel, so the icon
occupies exactly the same space on screen as the old 8x8 one did.
"""

from __future__ import annotations

import json
import re

SIZE = 16

PALETTE = {
    "1": "#141414",   # black
    "2": "#FFFFFF",   # white
    "3": "#D9775B",   # clawd orange
    "4": "#A85138",   # dark orange
    "5": "#F2C14E",   # yellow
    "6": "#D6402F",   # red
    "7": "#5B8FD9",   # blue
    "8": "#5BA86B",   # green
    "9": "#8A8A8A",   # grey
    "A": "#7A5230",   # brown
    "B": "#F0DCC8",   # cream
    "C": "#3A3F4B",   # slate (screens, soft outlines)
    "D": "#C9CFDA",   # light grey
    "E": "#9B6BD9",   # purple
    "F": "#E88BB0",   # pink
    "G": "#2E6BB8",   # dark blue
    "H": "#3C7A4A",   # dark green
    "I": "#C08A3E",   # bronze
}

ITEMS: dict[str, list[str]] = {
    "book": [
        "................",
        "................",
        "...AAA....AAA...",
        "..ABBBA..ABBBA..",
        "..AB1BBAAB1BBA..",
        "..AB1BBAAB1BBA..",
        "..ABBBBAABBBBA..",
        "..AB1BBAAB1BBA..",
        "..AB1BBAAB1BBA..",
        "..ABBBBAABBBBA..",
        "..AB1BBAAB1BBA..",
        "..AAAAAAAAAAAA..",
        "...AAAAAAAAAA...",
        "................",
        "................",
        "................",
    ],
    "pdf": [
        "................",
        "...DDDDDDDD.....",
        "...D222222DD....",
        "...D2222222D....",
        "...D2666662D....",
        "...D2222222D....",
        "...D2666662D....",
        "...D2222222D....",
        "...D26662222D...",
        "...D2222222.D...",
        "...D2666662..D..",
        "...D2222222...D.",
        "...DDDDDDDDDDDD.",
        "................",
        "................",
        "................",
    ],
    "laptop": [
        "................",
        "..CCCCCCCCCCCC..",
        "..C7777777777C..",
        "..C7GGGGGGGG7C..",
        "..C7G222222G7C..",
        "..C7G2GGGG2G7C..",
        "..C7G222222G7C..",
        "..C7GGGGGGGG7C..",
        "..C7777777777C..",
        "..CCCCCCCCCCCC..",
        ".DDDDDDDDDDDDDD.",
        ".D999999999999D.",
        "DDDDDDDDDDDDDDDD",
        "................",
        "................",
        "................",
    ],
    "code": [
        "................",
        ".CCCCCCCCCCCCCC.",
        ".C111111111111C.",
        ".C111111111111C.",
        ".C118111111111C.",
        ".C11185111111C..",
        ".C1118551111.1C.",
        ".C111855511111C.",
        ".C1118551111.1C.",
        ".C11185111111C..",
        ".C118111111111C.",
        ".C111177771111C.",
        ".C111111111111C.",
        ".CCCCCCCCCCCCCC.",
        "................",
        "................",
    ],
    "resistor": [
        "................",
        "................",
        "................",
        "................",
        "................",
        "999.........999.",
        "999.........999.",
        "999AAAAAAAAA999.",
        "999A66A6A66A999.",
        "999A66A6A66A999.",
        "999AAAAAAAAA999.",
        "999.........999.",
        "999.........999.",
        "................",
        "................",
        "................",
    ],
    "capacitor": [
        "................",
        ".......DD.......",
        ".......DD.......",
        ".......DD.......",
        ".......DD.......",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        "................",
        "................",
        "DDDDDDDDDDDDDDDD",
        "DDDDDDDDDDDDDDDD",
        ".......DD.......",
        ".......DD.......",
        ".......DD.......",
        ".......DD.......",
        "................",
    ],
    "inductor": [
        "................",
        "................",
        "................",
        "................",
        "..DD...DD...DD..",
        ".D..D.D..D.D..D.",
        ".D..D.D..D.D..D.",
        "DD..DDD..DDD..DD",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "chip": [
        "................",
        "................",
        "...9.9.9.9.9....",
        "...9.9.9.9.9....",
        "..111111111111..",
        "..122222222221..",
        "9.12111111112.19",
        "9.12122222112.19",
        "9.12122222112.19",
        "9.12111111112.19",
        "..122222222221..",
        "..111111111111..",
        "...9.9.9.9.9....",
        "...9.9.9.9.9....",
        "................",
        "................",
    ],
    "transistor": [
        "................",
        "..........DD....",
        "..........DD....",
        "..........DD....",
        "......D...DD....",
        "......D..DD.....",
        "......D.DD......",
        "DDDDDDDDD.......",
        "DDDDDDDDD.......",
        "......D.DD......",
        "......D..DD.....",
        "......D...DD....",
        "..........DD....",
        "..........DD....",
        "..........DD....",
        "................",
    ],
    "diode": [
        "................",
        "................",
        "................",
        "......D.....6...",
        "......DD....6...",
        "......DDD...6...",
        "......DDDD..6...",
        "DDDDDDDDDDD.6DDD",
        "......DDDD..6...",
        "......DDD...6...",
        "......DD....6...",
        "......D.....6...",
        "................",
        "................",
        "................",
        "................",
    ],
    "wave": [
        "................",
        "................",
        "................",
        ".....77.........",
        "....7..7........",
        "...7....7.......",
        "..7......7......",
        ".7........7.....",
        "7..........7...7",
        "............7.7.",
        ".............7..",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "magnet": [
        "................",
        "................",
        "...666....666...",
        "..66666..66666..",
        ".6666666666666..",
        ".666........666.",
        ".666........666.",
        ".666........666.",
        ".666........666.",
        ".666........666.",
        ".222........222.",
        ".222........222.",
        ".222........222.",
        "................",
        "................",
        "................",
    ],
    "antenna": [
        "................",
        ".......77.......",
        "......7..7......",
        "....77....77....",
        "...7...DD...7...",
        "..7....DD....7..",
        ".......DD.......",
        "......D..D......",
        "......D..D......",
        ".....D....D.....",
        ".....D....D.....",
        "....D......D....",
        "....DDDDDDDD....",
        "................",
        "................",
        "................",
    ],
    "battery": [
        "................",
        "................",
        "................",
        ".......111......",
        "..111111111111..",
        "..1222222222.1..",
        "..12888888.2.1..",
        "..12888888.2.1..",
        "..12888888.2.1..",
        "..12888888.2.1..",
        "..1222222222.1..",
        "..111111111111..",
        "................",
        "................",
        "................",
        "................",
    ],
    "scope": [
        "................",
        ".CCCCCCCCCCCCCC.",
        ".C111111111111C.",
        ".C111881111111C.",
        ".C118118111111C.",
        ".C11811811111C..",
        ".C1811.81111.8C.",
        ".C181..811..88C.",
        ".C81...8118.8.C.",
        ".C1.....8888..C.",
        ".C111111111111C.",
        ".CCCCCCCCCCCCCC.",
        "...CC......CC...",
        "..CCCCCCCCCCCC..",
        "................",
        "................",
    ],
    "calculator": [
        "................",
        "..CCCCCCCCCCCC..",
        "..C2222222222C..",
        "..C2888888882C..",
        "..C2222222222C..",
        "..CCCCCCCCCCCC..",
        "..C.D.D.D..D.C..",
        "..CCCCCCCCCCCC..",
        "..C.D.D.D..D.C..",
        "..CCCCCCCCCCCC..",
        "..C.D.D.D..6.C..",
        "..CCCCCCCCCCCC..",
        "..C.DDD.D..6.C..",
        "..CCCCCCCCCCCC..",
        "................",
        "................",
    ],
    "graph": [
        "................",
        "..1.............",
        "..1..........6..",
        "..1.........6...",
        "..1........6....",
        "..1.......6.....",
        "..1..6...6......",
        "..1.6.6.6.......",
        "..16...6........",
        "..1.............",
        "..1.............",
        "..1.............",
        "..111111111111..",
        "................",
        "................",
        "................",
    ],
    "pencil": [
        "................",
        "............555.",
        "...........5555.",
        "..........55I5..",
        ".........55I5...",
        "........55I5....",
        ".......55I5.....",
        "......55I5......",
        ".....55I5.......",
        "....BBI5........",
        "...BBB5.........",
        "..1BB...........",
        "..11............",
        ".1..............",
        "................",
        "................",
    ],
    "ruler": [
        "................",
        "................",
        "................",
        "................",
        ".IIIIIIIIIIIIII.",
        ".IBBBBBBBBBBBBI.",
        ".I1.1.1.1.1.1.I.",
        ".I1.1.1.1.1.1.I.",
        ".IBBBBBBBBBBBBI.",
        ".IBBBBBBBBBBBBI.",
        ".IIIIIIIIIIIIII.",
        "................",
        "................",
        "................",
        "................",
        "................",
    ],
    "atom": [
        "................",
        ".....777777.....",
        "...77......77...",
        "..7..........7..",
        ".7...777777...7.",
        ".7..7......7..7.",
        "7..7...66...7..7",
        "7..7...66...7..7",
        ".7..7......7..7.",
        ".7...777777...7.",
        "..7..........7..",
        "...77......77...",
        ".....777777.....",
        "................",
        "................",
        "................",
    ],
    "flask": [
        "................",
        ".....111111.....",
        ".....1DDDD1.....",
        "......1DD1......",
        "......1DD1......",
        "......1DD1......",
        ".....1DDDD1.....",
        "....1DDDDDD1....",
        "...1D888888D1...",
        "..1D88888888D1..",
        "..188888888881..",
        "..188888888881..",
        "..1D88888888D1..",
        "...1111111111...",
        "................",
        "................",
    ],
    "tv": [
        "................",
        "....D......D....",
        ".....D....D.....",
        "......D..D......",
        "..DDDDDDDDDDDD..",
        "..D2222222222D..",
        "..D2666666662D..",
        "..D2622222262D..",
        "..D2622222262D..",
        "..D2666666662D..",
        "..D2222222222D..",
        "..DDDDDDDDDDDD..",
        "...DD......DD...",
        "................",
        "................",
        "................",
    ],
    "controller": [
        "................",
        "................",
        "................",
        "..DDDDDDDDDDDD..",
        ".DDDDDDDDDDDDDD.",
        "DDD1DDDDDDD6DDDD",
        "DD111DDDDD6.6DDD",
        "DDD1DDDDDDD6DDDD",
        "DDDDDDDDDDDDDDDD",
        ".DDDDDDDDDDDDDD.",
        ".DDD..DDDD..DDD.",
        ".DD....DD....DD.",
        ".DD..........DD.",
        "................",
        "................",
        "................",
    ],
    "phone": [
        "................",
        "....DDDDDDDD....",
        "....D111111D....",
        "....D1CCCC1D....",
        "....D1C88C1D....",
        "....D1CCCC1D....",
        "....D1CFFC1D....",
        "....D1CCCC1D....",
        "....D1C55C1D....",
        "....D1CCCC1D....",
        "....D1CCCC1D....",
        "....D111111D....",
        "....D..DD..D....",
        "....DDDDDDDD....",
        "................",
        "................",
    ],
    "cart": [
        "................",
        ".DD.............",
        ".DD.............",
        ".DD.DDDDDDDDDD..",
        ".DD.D66666666D..",
        ".DD.D66666666D..",
        ".DD..D666666D...",
        ".DD..D666666D...",
        ".DD...DDDDDD....",
        ".DD.............",
        "....DD....DD....",
        "...DDDD..DDDD...",
        "...DDDD..DDDD...",
        "....DD....DD....",
        "................",
        "................",
    ],
    "music": [
        "................",
        "........DDDDDDD.",
        "........DDDDDDD.",
        "........DD....D.",
        "........DD....D.",
        "........DD....D.",
        "........DD....D.",
        "........DD....D.",
        "......DDDD....D.",
        ".....DDDDD..DDD.",
        ".....DDDDD.DDDD.",
        ".....DDDDD.DDDD.",
        "......DDD...DDD.",
        "................",
        "................",
        "................",
    ],
    "popcorn": [
        "................",
        "....BB..BB......",
        "...BBBBBBBB.....",
        "..BB.BBBB.BB....",
        "...BBBBBBBBB....",
        "..1616161616.1..",
        "..1616161616.1..",
        "..1616161616.1..",
        "..1.616161.6.1..",
        "..1616161616.1..",
        "...161616161....",
        "...161616161....",
        "....1616161.....",
        "....1111111.....",
        "................",
        "................",
    ],
    "chat": [
        "................",
        "..CCCCCCCCCCCC..",
        "..C2222222222C..",
        "..C2CC2CC2CC2C..",
        "..C2222222222C..",
        "..C2CCCCCCC22C..",
        "..C2222222222C..",
        "..C2CCCCC2222C..",
        "..C2222222222C..",
        "..CCCCCCCCCCCC..",
        "....CCCC........",
        "....CCC.........",
        "....CC..........",
        "................",
        "................",
        "................",
    ],
    "clock": [
        "................",
        ".....111111.....",
        "...1122222211...",
        "..112222222211..",
        ".11222212222211.",
        ".12222212222221.",
        ".12222212222221.",
        ".12222211112221.",
        ".12222222222221.",
        ".12222222222221.",
        "..112222222211..",
        "...1122222211...",
        ".....111111.....",
        "................",
        "................",
        "................",
    ],
    "coffee": [
        "................",
        "................",
        "....9...9.......",
        "...9...9........",
        "................",
        "..BBBBBBBBB.....",
        "..B2222222B111..",
        "..BAAAAAAAB1.1..",
        "..BAAAAAAAB1.1..",
        "..BAAAAAAAB1.1..",
        "..BAAAAAAAB111..",
        "..BBBBBBBBB.....",
        "...AAAAAAA......",
        "..AAAAAAAAA.....",
        "................",
        "................",
    ],
    "bulb": [
        "................",
        "......5555......",
        ".....555555.....",
        "....55555555....",
        "....55522555....",
        "....55522555....",
        "....55522555....",
        ".....555555.....",
        "......5555......",
        "......1111......",
        ".....111111.....",
        "......1111......",
        "......1111......",
        ".......11.......",
        "................",
        "................",
    ],
    "sparkle": [
        ".......55.......",
        ".......55.......",
        "......5555......",
        "......5555......",
        ".....555555.....",
        ".....555555.....",
        "55.5555555555.55",
        "5555555555555555",
        "5555555555555555",
        "55.5555555555.55",
        ".....555555.....",
        ".....555555.....",
        "......5555......",
        "......5555......",
        ".......55.......",
        ".......55.......",
    ],
    "fire": [
        "................",
        ".......6........",
        "......66........",
        ".....666........",
        "....6665...6....",
        "...666556..66...",
        "...66555566666..",
        "..666555556666..",
        "..66555225566...",
        "..6655522556....",
        "...665522566....",
        "...6655556.6....",
        "....666666......",
        "................",
        "................",
        "................",
    ],
    "trophy": [
        "................",
        "..5555555555....",
        "..5IIIIIIII5....",
        "9.5IIIIIIII5.9..",
        "99.5IIIIII5.99..",
        "9..55IIII55..9..",
        "9...555555...9..",
        "99...5555...99..",
        ".9....55....9...",
        "......55........",
        "......55........",
        "....IIIIII......",
        "...IIIIIIII.....",
        "................",
        "................",
        "................",
    ],
    "warning": [
        "................",
        ".......1........",
        "......151.......",
        "......151.......",
        ".....15551......",
        ".....15151......",
        "....155151......",
        "....1551551.....",
        "...15551551.....",
        "...155555551....",
        "..1555515551....",
        "..15555555551...",
        ".1555555555551..",
        ".11111111111111.",
        "................",
        "................",
    ],
    "zzz": [
        "................",
        "..999999........",
        "......99........",
        ".....99.........",
        "....99..........",
        "..999999........",
        "................",
        "........9999....",
        "..........99....",
        ".........99.....",
        "........9999....",
        "................",
        "............999.",
        "..............9.",
        "............999.",
        "................",
    ],
    "deadline": [
        "................",
        "...11......11...",
        "..1111111111111.",
        "..1666666666661.",
        "..1111111111111.",
        "..1222222222221.",
        "..1211121112221.",
        "..1222222222221.",
        "..1211122212221.",
        "..1222222222221.",
        "..1211122212221.",
        "..1222222222221.",
        "..1111111111111.",
        "................",
        "................",
        "................",
    ],
}


# topic keyword -> built-in item. First match wins, so put the specific ones first.
KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("저항", "resistor", "ohm", "옴의", "전압분배", "kirchhoff", "키르히호프",
      "thevenin", "테브난", "norton", "노턴", "전류", "current", "voltage",
      "전압", "회로해석"), "resistor"),
    (("커패시터", "capacitor", "축전", "충방전", "커패", "rc회로", "rc circuit",
      "rc ", "transient", "과도응답", "시정수"), "capacitor"),
    (("인덕터", "inductor", "코일", "coil", "인덕턴스", "rl회로", "rl circuit",
      "solenoid", "솔레노이드"), "inductor"),
    (("mosfet", "bjt", "transistor", "트랜지스터", "증폭", "amplifier",
      "op-amp", "opamp", "연산증폭"), "transistor"),
    (("diode", "다이오드", "정류", "rectifier", "led", "zener", "제너"), "diode"),
    (("반도체", "semiconductor", "fpga", "verilog", "vhdl", "chip", "집적",
      "logic", "논리회로", "디지털", "마이크로", "microcontroller", "arduino",
      "아두이노", "embedded", "임베디드"), "chip"),
    (("신호", "signal", "fourier", "푸리에", "laplace", "라플라스", "주파수",
      "frequency", "wave", "파형", "convolution", "합성곱", "필터", "filter",
      "bode", "보드선도", "sampling", "표본화", "z-transform"), "wave"),
    (("전자기", "electromagnet", "maxwell", "맥스웰", "자기장", "magnetic",
      "gauss", "가우스", "전기장", "flux", "자속"), "magnet"),
    (("antenna", "안테나", "통신", "communication", "rf", "무선", "wireless",
      "transmission line", "전송선"), "antenna"),
    (("battery", "배터리", "전지", "power supply", "전원", "전력", "충전기"), "battery"),
    (("oscilloscope", "오실로스코프", "스코프", "측정", "measurement",
      "multimeter", "멀티미터", "실험", "lab", "ltspice", "pspice",
      "simulation", "시뮬"), "scope"),
    (("행렬", "matrix", "linear algebra", "선형대수", "eigen", "고유값",
      "calculus", "미적분", "적분", "integral", "미분방정식",
      "differential equation", "확률", "probability", "통계", "statistics",
      "계산", "calculator"), "calculator"),
    (("graph", "그래프", "plot", "차트", "chart", "데이터", "data",
      "matlab", "python", "numpy", "분석", "analysis"), "graph"),
    (("code", "코딩", "코드", "programming", "프로그래밍", "vscode", "pycharm",
      "github", "깃허브", "git", "깃", "debug", "디버깅", "algorithm", "알고리즘",
      "terminal", "터미널", "컴파일", "compile", "함수", "function",
      "파이썬", "자바", "java", "c++", "리팩", "refactor", "pull request",
      "커밋", "commit", "버그", "bug"), "code"),
    (("pdf", "논문", "paper", "arxiv", "ieee", "sciencedirect", "교재",
      "textbook", "강의노트", "lecture note", "slide", "슬라이드", "ppt",
      ".docx", ".pptx", ".hwp", "word", "powerpoint", "한글 20", "문서"), "pdf"),
    (("excel", "엑셀", ".xlsx", ".csv", "spreadsheet", "시트", "표 계산"), "graph"),
    (("명령 프롬프트", "terminal", "cmd.exe", "powershell", "windows terminal",
      "bash", "쉘", "셸"), "code"),
    (("화학", "chemistry", "물리", "physics", "실험실", "reaction", "분자",
      "molecule", "재료", "material"), "flask"),
    (("원자", "atom", "quantum", "양자", "electron", "전자구조", "nuclear",
      "핵", "orbital"), "atom"),
    (("설계", "design", "cad", "도면", "drawing", "kicad", "altium", "pcb",
      "autocad", "inventor", "3d", "모델링"), "ruler"),
    (("klas", "kw.ac.kr", "광운대", "kwangwoon", "학습관리", "lms", "이러닝",
      "e-learning", "출석", "성적", "수강", "강의계획서", "포털"), "laptop"),
    (("claude", "클로드", "chatgpt", "gpt", "gemini", "코파일럿", "copilot"), "chat"),
    (("강의", "lecture", "수업", "class", "공부", "study", "복습", "예습",
      "book", "chapter", "장 ", "단원"), "book"),
    (("과제", "homework", "assignment", "pset", "problem set", "레포트",
      "report", "숙제", "글쓰기", "writing", "toefl", "essay", "작성"), "pencil"),
    (("마감", "deadline", "due", "시험", "exam", "midterm", "기말", "중간고사",
      "일정", "schedule", "달력", "calendar"), "deadline"),
    (("youtube", "유튜브", "video", "영상", "netflix", "넷플", "tiktok",
      "twitch", "치지직", "웹툰", "webtoon", "애니", "anime", "skibidi",
      "compilation", "shorts", "reels", "brainrot", "클립", "edit audio",
      "vlog", "스트리밍", "stream", "movie", "드라마", "예능"), "tv"),
    (("게임", "game", "gaming", "steam", "lol", "league of legends", "롤",
      "valorant", "발로란트", "overwatch", "옵치", "배그", "pubg", "minecraft",
      "마크", "롤체", "genshin", "원신", "메이플", "nexon", "던파", "roblox"), "controller"),
    (("쇼핑", "shopping", "무신사", "musinsa", "쿠팡", "coupang", "11번가",
      "aliexpress", "장바구니", "cart", "sale", "세일", "구매", "택배"), "cart"),
    (("instagram", "인스타", "insta", "twitter", "sns", "카톡", "kakao",
      "reddit", "커뮤", "디시", "에펨", "더쿠", "threads", "facebook",
      "메신저", "디엠", "dm"), "phone"),
    (("음악", "music", "spotify", "노래", "song", "playlist", "플레이리스트",
      "멜론", "melon", "앨범", "album", "kpop", "아이돌"), "music"),
    (("먹방", "mukbang", "asmr eating", "야식", "간식", "snack", "배달",
      "치킨", "food", "먹을", "맛집"), "popcorn"),
    (("채팅", "chat", "discord", "디스코드", "메시지", "message", "댓글",
      "comment", "포럼", "forum", "질문", "슬랙", "slack"), "chat"),
    (("휴식", "break", "커피", "coffee", "쉬어", "쉬자", "물 마", "카페",
      "cafe", "tea", "차 한"), "coffee"),
    (("칭찬", "streak", "praise", "good job", "잘한", "집중", "great",
      "nice", "훌륭"), "sparkle"),
    (("연속", "combo", "불타", "on fire", "몰입", "폭주", "달린다"), "fire"),
    (("우승", "trophy", "성취", "achievement", "합격", "완료", "clear",
      "달성", "1등", "수석"), "trophy"),
    (("경고", "warning", "위험", "danger", "주의", "caution", "오류",
      "error", "실패", "fail"), "warning"),
    (("잠", "sleep", "afk", "졸려", "새벽", "자리 비", "피곤", "tired",
      "취침", "낮잠", "nap"), "zzz"),
    (("아이디어", "idea", "tip", "tidbit", "잡지식", "fact", "사실",
      "발견", "insight", "궁금"), "bulb"),
    (("노트북", "laptop", "컴퓨터", "computer", "화면", "screen", "브라우저",
      "browser", "웹", "web", "검색", "search"), "laptop"),
]

DEFAULT_STUDY = "book"
FALLBACK = {"study": "book", "stray": "tv", "idle": "zzz", "neutral": None}


def _valid(grid) -> bool:
    """A grid is only usable if every row is exactly SIZE known characters."""
    return (isinstance(grid, list) and len(grid) == SIZE
            and all(isinstance(r, str) and len(r) == SIZE for r in grid)
            and all(c in PALETTE or c == "." for row in grid for c in row))


def upscale(grid) -> list[str] | None:
    """
    Turn an old 8x8 grid into a 16x16 one by doubling each pixel.

    Lets an items_cache.json written by the previous version keep working
    instead of being silently thrown away.
    """
    if not (isinstance(grid, list) and len(grid) == 8
            and all(isinstance(r, str) and len(r) == 8 for r in grid)):
        return None
    out = []
    for row in grid:
        doubled = "".join(c * 2 for c in row)
        out.append(doubled)
        out.append(doubled)
    return out if _valid(out) else None


def coerce(grid):
    """Accept a 16x16 grid, or an 8x8 one upscaled. None if it's neither."""
    if _valid(grid):
        return grid
    return upscale(grid)


def builtin_for(text: str) -> str | None:
    """Pick a built-in item name from free text, or None."""
    low = (text or "").lower()
    for words, name in KEYWORDS:
        for w in words:
            if w in low:
                return name
    return None


def grid_of(name: str) -> list[str] | None:
    return ITEMS.get(name)


class ItemCache:
    """Remembers API-generated grids so a topic is only ever generated once."""

    def __init__(self, path: str, log=lambda *a: None):
        self.path = path
        self.log = log
        self.data: dict[str, list[str]] = {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, v in raw.items():
                got = coerce(v)
                if got:
                    self.data[k] = got
        except Exception:
            pass

    @staticmethod
    def key(topic: str) -> str:
        return re.sub(r"\s+", " ", (topic or "").strip().lower())[:60]

    def get(self, topic: str) -> list[str] | None:
        return self.data.get(self.key(topic))

    def put(self, topic: str, grid) -> bool:
        got = coerce(grid)
        if not got:
            return False
        self.data[self.key(topic)] = got
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=1, ensure_ascii=False)
        except Exception as e:
            self.log(f"item cache write failed: {e}")
        return True


def resolve(topic: str, cache: "ItemCache | None" = None,
            fallback: str | None = None) -> list[str] | None:
    """Built-in match first, then anything the API generated earlier, then a fallback."""
    name = builtin_for(topic)
    if name:
        return ITEMS[name]
    if cache:
        got = cache.get(topic)
        if got:
            return got
    if fallback:
        name = FALLBACK.get(fallback, fallback)
        if name in ITEMS:
            return ITEMS[name]
    return None


PALETTE_HELP = (
    "Palette: '.'=transparent 1=black 2=white 3=orange 4=dark-orange 5=yellow "
    "6=red 7=blue 8=green 9=grey A=brown B=cream C=slate D=light-grey "
    "E=purple F=pink G=dark-blue H=dark-green I=bronze"
)
