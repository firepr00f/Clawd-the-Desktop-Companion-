> **This is the full reference manual.** For what Clawd is and why, start at the
> [README](../README.md). Everything below is the option-by-option detail.

# Clawd - desktop study buddy (v3)

**New in v3**

- **Paste your API key into Clawd, not into a file.** No key on startup and he
  asks for it in a small box, saves it outside this folder, and works
  immediately. Right-click → *set api key…* any time.
- **He's in the system tray too**, bottom-right, with the same menu plus
  *bring Clawd back here* — so he is reachable even when the sprite isn't.
  No extra package needed.
- **Double-click him and he checks on you.** One screenshot, one verdict —
  studying, straying, or he genuinely can't tell — and a reaction to match:
  a compliment, a telling off, or a suspicious *...are you actually studying*.
  This is the only screenshot in the whole app.
- **Bubbles are ~2.2x bigger** and every size is config-driven; the window
  resizes itself around them.
- **DPI fixed.** He was cropping the top-left corner of scaled displays and only
  ever seeing browser chrome. Now he reads the actual page.
- **Icons redrawn at 16x16**, 37 of them, none a black-on-black silhouette.
  8x8 was too few pixels to recognise anything.
- **Real animation** - a 4-beat walk cycle, squash and stretch, directional
  facing, and 4-8 frame idle loops per mood. Still whole pixels only.
- **The answer box can no longer trap him.** Escape, an empty Enter, a second
  click or any menu item drops the question.
- **한/영 switch** - his whole vocabulary and the entire interface, on the menu.
- **He can no longer walk off the monitor.** Both clamps bounded the *window*,
  which on a scaled display is mostly transparent bubble space above him — so
  his sprite could sit 600+ px below the bottom edge, invisible and impossible
  to right-click. They now bound the sprite. A bad saved position heals on
  launch and the frame loop rescues him if anything ever slips through.
- **Icons are back, driven by what you're doing** - the window title picks one
  of the 37 built-ins on every poll, free and instant. Off while you're idle.
- **Study is an allowlist.** KLAS, the Claude app, Adobe PDF, Word and
  PowerPoint. Everything else — Excel, a terminal, your bank — gets the YouTube
  treatment.
- **A line every five minutes** even when nothing changes, from the offline
  bank: no screenshot, no API call, no cost.
- **Pixel fireworks** after ten minutes without the mouse moving.
- **Faster answers** - smaller capture, shorter prompt and reply, shorter pause.
- **A window must hold still for 2s** before he reacts, so a page mid-load
  can't set him off.
- **Long lines resize the bubble** — wider, then smaller type — instead of
  losing their ending. Tidbits are ~30% shorter at the source too.
- **He kicks when you pick him up** — legs splaying diagonally, mood intact.
- **The bubble stays next to him** - it used to right-align to the canvas edge,
  which stranded short messages hundreds of pixels away with the tail pointing
  at nothing.

---

A small pixel Clawd who sits in the corner of your screen, watches which window
is in front, and reacts. He praises focus streaks, quizzes you on what you're
actually reading, throws out tidbits,
and gets progressively more disappointed the longer you're on YouTube.

Windows, Python 3.9+. Everything works offline; an optional API key makes him
smarter.

---

## Setup

```bat
cd path\to\clawd
pip install -r requirements.txt      :: only needed for screenshot/API mode
run_clawd.bat                        :: or: pythonw clawd.pyw
```

He appears bottom-right. **Drag** him anywhere, **left-click** for a status
check, **right-click** for the menu.

To start him with Windows: press `Win+R`, run `shell:startup`, and drop a
shortcut to `run_clawd.bat` in the folder that opens.

---

## How he decides what you're doing

He reads the **title of the foreground window** plus the process name every 5
seconds — which on Windows already includes your browser tab title, so
`skibidi toilet compilation - YouTube - Google Chrome` is fully visible without
any screenshot.

**With `focus.allowlist_mode` on (the default)** the verdict is short:

| verdict | what |
|---|---|
| **study** | the allowlist below — KLAS, Claude, PDF, Word, PowerPoint |
| **stray** | literally everything else |
| **idle** | no keyboard or mouse for 3 minutes |
| **neutral** | the desktop, Explorer, Windows Search, Clawd's own windows |

See *What counts as studying* for the list and how to extend it.

**With it off**, the original keyword lists apply instead: PDF readers,
OneNote/Obsidian/Notion, MATLAB, LTspice, KiCad, VS Code, Overleaf, your LMS and
any title with `강의`, `과제`, `회로`, `fourier`, `mosfet`, `pset`… count as
study; YouTube, Instagram, 무신사/쿠팡, Steam and friends count as stray. In that
mode a study video on YouTube (`MIT 6.002 Circuits Lecture 4`) counts as
studying.

**Brainrot is caught separately in both modes.** `skibidi`, `rizz`, `gyatt`,
`tier list`, `shorts`, `mukbang` skip the gentle tier and get the
"how old are you gang :(" treatment immediately.

`extra_study_keywords` / `extra_stray_keywords` in `config.json` beat every
built-in rule, in either mode.

## The escalation ladder

| off-task for | he gets | flavour |
|---|---|---|
| 2 min | curious | "quick break? i'll allow it. clock's running though" |
| 5 min | annoyed | "still {what}?? gang." |
| 12 min | disappointed | "you told me you were studying. i believed you. that's on me" |
| 25 min | **softer, not harsher** | "25 min usually means you're tired or stuck, not lazy. which is it" |

The last tier drops the bit on purpose — an hour of guilt-tripping is not a
study tool. He also stops escalating and just reminds you what's actually due.
Every threshold is in `config.json` under `stray`.

### Things he hates on sight

Straying and *hating* are different. Anything off the allowlist is straying and
gets the grace period; a handful of things get named the moment the window
settles, with no warm-up, opening at the **annoyed** tier — which also puts him
in your way, since `motion.block_at_tier` is 1.

Built in: YouTube, Steam, TikTok, Instagram, Twitch, Netflix, League, Valorant,
Maple, Battle.net, 쿠팡, 무신사. Add your own with `focus.hated` (title words)
and `focus.hated_processes` (executables); `stray.hated_seconds` is how long he
waits first, and 0 means immediately.

A lecture that happens to live on YouTube is **not** hated — "전자기학 3강",
"12주차", "Fourier transform lecture" and the rest of the study markers rescue
it. It is still off the allowlist, so it still counts as straying; he just
doesn't spit the site's name at you for it.

### Talking him down

The title is a guess. The screen is not. If he is cross about a window,
**double-click him** — and if the look comes back *studying*, he takes it back
and leaves that window alone:

> 아 진짜 강의네. 내가 잘못했다, 계속해

The pardon is filed against that window's normalised title, so it survives a
running video clock, a changing unread badge and an editor's unsaved-changes
dot, and it lasts `focus.pardon_hours` (default 6). Everything else is
untouched: a different YouTube tab is hated exactly as before. Double-clicking
the same window later and getting *straying* takes the pardon straight back.

On the study side: praise every 20 min, a fun tidbit after ~half of those, a
break nudge at 50 min, and a quiz every 25 focused minutes.

## Quizzes

He asks a question and a text box appears under him — type an answer, press
Enter. Offline he uses a built-in EE question bank and grades by keyword.
With an API key he writes the question **from what's on your screen right now**
and grades your answer properly. Type `skip` if you want the answer.


## API mode (optional)

**You don't have to edit any file.** Start him with no key and he says he needs
one and opens a box to paste it into. You can also open it any time from
right-click → **set api key…**. Get one at console.anthropic.com → API keys.

What changes: he comments on the actual material on screen ("oh, Thevenin
equivalents"), writes real quiz questions from it, grades your answers, and
generates fresh tidbits. Cost is a few cents a day on the default
`claude-haiku-4-5` for comments (`claude-sonnet-5` for quizzes/grading).

### Where the key goes

He looks in three places, in order, on **every** call — so pasting one into the
box works immediately, with no restart:

| # | source | notes |
|---|---|---|
| 1 | `api.api_key` in `config.json` | explicit, but this folder syncs to OneDrive, so the key syncs with it |
| 2 | the `ANTHROPIC_API_KEY` environment variable | best. Nothing about the key is on disk here at all |
| 3 | what you typed into his box | `core/secrets.py` → `%LOCALAPPDATA%\Clawd\api_key` |

**test api key** tells you which of the three he is currently reading, and
**forget my saved api key** deletes the file in (3).

The box has a checkbox to *also* run `setx ANTHROPIC_API_KEY`, which registers
it for your whole Windows account so other tools see it — that one only affects
programs started afterwards.

**Why not save it into the code?** `core/` lives inside your OneDrive folder. A
key written into a `.py` file syncs to the cloud, travels with every copy of the
project, and lands in any git commit or zip you share. `%LOCALAPPDATA%` is
outside the synced folder and local to one machine. It is still **plain text** —
readable by anyone who can read your user profile — so on a shared PC use the
environment variable instead. The key is never printed in a speech bubble and
`clawd.log` records only a redacted stub like `sk-ant-api…4f2c`.

**Capture policy: manual only, and there is no other code path.** Clawd takes a
screenshot **only** when you **double-click him**. Nothing runs in the
background — no periodic capture, no automatic triggers, not even the local
never-transmitted fingerprint that an earlier version used to notice the screen
had changed. The background watcher has been deleted rather than switched off,
so there is no setting that could turn one back on. One double-click, one
screenshot, one reaction, then silence until you ask again.

He waits `api.manual_delay_seconds` (default 1.2) and *then* reads whatever
window is in front. That delay is the useful part: double-click him, click back
into the PDF or the tab you want him to read, and he photographs that. If
Clawd's own window is still in front when the timer fires, he falls back to the
last real window you were in.

**What he does with it.** He judges the picture himself rather than trusting the
window title, and lands on one of three:

| verdict | face | what he says |
|---|---|---|
| studying | proud | a compliment, or a nudge to keep going |
| straying | annoyed | a telling off, or a snark at the actual thing on screen |
| can't tell | **confused** — a question mark over his head | asks you outright whether this counts |

"Can't tell" is a real answer, not a failure: an unreadable, blank or honestly
ambiguous screen comes back `unsure` rather than being forced into one of the
other two. With no API key he still reacts, judging from the window title with
the same allowlist the nagging uses.

The window goes straight from memory to the API and is never written to disk. He
ducks out of frame first so he isn't in his own screenshot, and a blue pixel eye
blinks over his head for 1.6s every time, so you always know when he looked.

| key | default | what it does |
|---|---|---|
| `manual_delay_seconds` | 0.35 | pause between the double-click and the capture. Short on purpose: his window never takes focus, so clicking him does not move you off what you were reading |
| `check_timeout_seconds` | 18 | if no answer by then he reacts from the window title anyway, so a double-click never does nothing |
| `send_screenshots` | true | false = no capture at all, even manually (quizzes and nags still work) |
| `screenshot_max_width` | 880 | capture resolution. Smaller is quicker to encode, send and read; below ~700 he starts missing small text |
| `screenshot_quality` | 72 | JPEG quality |
| `hide_self_while_capturing` | true | he ducks out of frame so he isn't in his own screenshots |
| `stray_recheck_minutes` | 3 | how often he re-nags while you're off-task (window titles only — no capture) |

You can leave `api_key` empty and set the `ANTHROPIC_API_KEY` environment
variable instead, which keeps the key out of a file that syncs to the cloud.
**If Clawd says "no api key", check that — a variable set with `setx` is only
visible to programs started afterwards, so he needs a fresh launch.**

### If he only ever says "a browser"

That was a DPI bug and it is fixed: Clawd now calls
`SetProcessDpiAwarenessContext` before Tk starts. Without it `GetWindowRect`
reports *logical* pixels while the screen grab returns *physical* ones, so on a
125%/150%/175% display every capture was cropped to the top-left corner of the
screen - which on a maximised browser is the tab strip and nothing else.

`clawd.log` now records the display scale at startup and notes whether each API
call carried a screenshot and how big it was.

## What leaves your machine

Nothing at all with `api.enabled` false. With it on, and only when **you
double-click him** (or on a quiz or nag, which send no image):

| what | where it comes from | how to switch it off |
|---|---|---|
| a JPEG of the foreground window | `capture.py`, memory only, never written to disk. Manual clicks only. | `api.send_screenshots: false` |
| the window title | the OS | it never leaves unless a line is being written about it |
| a free-text line about you | `about_me` in `config.json` | leave it `""` |
| focused minutes today | `state.json` | it is a single number, and only sent with a line |

`context_line()` in `core/app.py` builds that context string and is the single
place any of it is assembled — read it if you want the exact wording.

**On disk:** the API key if you typed it into his box (in `%LOCALAPPDATA%\Clawd`,
outside this folder — see *Where the key goes*), `clawd.log` (activity),
`state.json` (focused seconds today),
`spend.json` (API cost counters), `items_cache.json` (topics he has drawn icons
for). `privacy.log_screen_details` is `false` by default, which keeps window
titles and page topics out of the log — set it `true` only while debugging.

**The API key** belongs in the `ANTHROPIC_API_KEY` environment variable, not in
`config.json`, if this folder syncs to OneDrive/Dropbox/git. Leave `api_key`
empty and Clawd reads the variable — or paste it into his box, which stores it
outside this folder. He never puts it in a bubble, and the log gets a redacted
stub only.

## Tray icon

Clawd has no title bar, no taskbar button, and a click-through window, so
right-clicking the sprite is normally the only way to reach him. When he is
behind a maximised window, on a monitor you unplugged, or just somewhere you
cannot find, there is nothing left to click.

So he also sits in the **notification area**, bottom-right of the taskbar, with
the same menu on right-click plus **bring Clawd back here** at the top — which
puts him in the corner of your main monitor whatever state he had got into. Left
or right click both open it. The icon is drawn from the same orange and the
same two eyes as the sprite; there is no `.ico` file to keep in sync.

**Only one Clawd runs at a time.** Starting him twice is easy — a shortcut, the
.bat, a stray double-click on the .pyw — and two copies fight over
always-on-top, both put an icon in the tray so quitting one orphans the other's,
both write `state.json`, and every nag and screen check happens twice at twice
the API cost. The second copy says so in a message box and closes. The lock is a
named mutex, which Windows releases even if the process is killed.

**The icon puts itself back.** Explorer restarting wipes every tray icon and
expects each app to re-add its own; one that doesn't just disappears for the
rest of the session. Clawd listens for `TaskbarCreated` and also checks every
20 seconds that the shell still knows about him, re-adding if not.

**No package to install and no thread.** It talks to `Shell_NotifyIcon` through
ctypes, the same way `watcher.py` and `dpi.py` already talk to user32, so it
works on any Python that can run the rest of Clawd. The icon owns a
message-only window whose messages the animation loop pumps, so a click arrives
on the Tk thread and simply opens the menu — the same `on_menu` the sprite
uses, so there is one menu and one code path. If any Win32 call refuses,
`clawd.log` says so and Clawd runs exactly as before with one fewer way to
reach him.

The icon is Clawd, drawn from `sprite.py` rather than copied, and rendered at
whatever size Windows asks for. At tray size he is cropped to his face —
eighteen cells of sprite into sixteen pixels is mush — and shown whole above
28px.

## Menu (right-click, and the tray)

(트레이 전용: 클로드 여기로 불러오기) · 퀴즈 내줘 · 잡지식 하나 · 됐어 질문 취소 · **언어: 한국어 / English** ·
(더블클릭 = 화면 한 번 보고 반응 · 우클릭 두 번 = 전부 취소하고 중립 상태로) ·
config.json 편집 · 로그 열기 ·
설정 다시 읽기 · api 키 입력… · api 키 테스트 · 저장된 api 키 삭제 ·
지금까지 api 비용 · 종료

(The menu is in whichever language he's set to; the English labels are the same
list.) **Removed for good:** *shush for 15 min / 1 hour*, *come back*, and
*this window is study / straying*. The `extra_study_keywords` /
`extra_stray_keywords` lists those wrote to still work — edit them by hand in
`config.json`.

**Every menu item wins.** Clicking one drops whatever was open — the quiz, the
answer box, the bubble on screen — disowns any API call still in flight, and
resets the rate limiter, so it always does something. ('fun tidbit' used to
silently do nothing while a quiz was up: the menu cleared the *mode* but left
the old bubble, so `can_speak()` refused and it returned without a word.)

**Double right-click** anywhere on him is the same reset on its own: back to
neutral from any state. A single right-click still opens the menu — it is held
back ~220ms so the two gestures can share a button, because `tk_popup` grabs the
pointer and a second click would otherwise go to the menu instead of to him.

A disowned request still costs what it was going to cost — urllib has no
cancel, so the HTTP call finishes in its worker thread. What's guaranteed is
that its answer is thrown away instead of arriving late and overwriting whatever
you asked for next.

**Double-clicking him** is the only thing in the whole app that takes a
screenshot. It waits `manual_delay_seconds` — use them to click into the window
you want read — then captures once and reacts. One double-click, one reaction,
no repeat. While he is looking he says nothing and just shows `....`, with the
blue pixel eye blinking over his head; the verdict replaces it when it lands.

## What counts as studying

`focus.allowlist_mode` is **true**, which inverts the old keyword lists: a short
allowlist is study and *everything else* is straying.

| study | how it matches |
|---|---|
| KLAS (klas.kw.ac.kr) and anything under it | title words `klas`, `kw.ac.kr`, `광운대`, `kwangwoon`, `학습관리`, `이러닝`, plus the login page title `광운대학교 로그인 페이지` |
| the Claude app | `claude.exe`, or `claude` in the title |
| Adobe PDF readers | `acrord32.exe`, `acrobat.exe`, and other PDF readers |
| Word | `winword.exe`, `.docx`, `.hwp` |
| PowerPoint | `powerpnt.exe`, `.pptx` |

Everything else is stray and gets the full escalation ladder. **That is a lot**
— Excel, VS Code, a terminal, a shopping site and your email are all "get back
to work" now. Add your own with `focus.allow_title_words` and
`focus.allow_processes`, or set `allowlist_mode: false` to go back to the old
keyword lists.

The desktop, Explorer, Windows Search and Clawd's own dialogs stay **neutral**
— nagging about the desktop would be unbearable. `focus.ignore_processes` adds
to that list.

## Reacting to a window

`window_settle_seconds` (default 2). A new window has to still be the same
window two seconds later before he acts on it. A page mid-load is not the page
it becomes — the KLAS lecture viewer spends its first moment as a blank or
placeholder title, and reacting to that instantly is why an online lecture got
interrupted before it had finished opening. The same guard covers alt-tabbing
past windows and a browser between tabs.

## When a line is too long

`_fit()` in `core/ui.py` tries three things before it throws anything away:

1. widen the bubble, up to what the canvas can hold
2. step the font down, to 70% of normal
3. only then trim, with an ellipsis

On top of that, `api.max_line_chars` (default 200) caps anything the model says
and cuts at the **last sentence break** under the cap — losing a whole sentence
reads far better than a word ending in `li…`. The tidbit prompt now asks for one
sentence under 30 words, and the 15 built-in tidbits were rewritten about 30%
shorter in both languages.

## The five-minute check-in

Same window, nothing changed, five minutes gone: he says something anyway.
`keep_alive_minutes` (default 5). Encouraging while studying
(*열심히 하고 있어*), nagging while straying (*공부하라고….*), flavoured with
whatever he last recognised.

**No screenshot and no API call** — it runs entirely off the offline bank, so
it costs nothing and never adds latency. He rotates through the pool rather
than repeating one line, and stays quiet while you're idle.

## Fireworks

`wake_after_minutes` (default 10) without the **mouse** moving and he sets off
pixel fireworks above his head, then says something. Deliberately the mouse and
not the system idle timer: reading a PDF without touching anything is exactly
when a nudge helps, and Windows' idle timer counts the keyboard too.

Three shells on a stagger, rings of single cells expanding outward, one ring per
frame. Whole pixels only, like everything else. They sit up and to his left, so
the speech bubble doesn't cover them.

## 한국어 / English

Right-click → **언어: 한국어로 바꾸기** (or **Language: switch to English**).
It takes effect on his very next line — nothing restarts.

Two halves, in two places:

- **His lines** live in `core/bank.py`, which has an `EN` list and a `KO` list
  per pool. The Korean is a rewrite, not a translation — same gremlin, speaking
  반말. All 29 pools are done, and a test fails if any English pool loses its
  Korean twin or if a `{placeholder}` goes missing in translation.
- **The interface** — menu, dialogs, status lines — is the table in
  `core/lang.py`, where a literal translation is what you want.

In Korean, every API prompt also gets a rule appended telling Claude to answer
in 반말, so his screen comments and quiz questions come back in Korean too.
Setting: `"language": "en" | "ko"` in `config.json`.

## Size

One size. The old 거대 / 보통 / 꼬깃 cycle is gone, and the double-click that
drove it now checks your screen instead. `appearance.pixel_size`, `font_size`
and `bubble_width` still scale him if you want him bigger — they just are not
something you flip through at runtime any more, and they need a restart.

## Bubble, sprite and animation

All under `appearance` in `config.json`. **These need a full restart, not
`reload settings`.**

| key | default | what it does |
|---|---|---|
| `pixel_size` | 9 | size of one Clawd pixel, in screen px |
| `font_size` | 16 | bubble text size |
| `bubble_width` | 640 | max text column inside the bubble |
| `bubble_max_height` | 460 | how tall the bubble may grow before text is trimmed |
| `sticker_outline` | false | white half-cell halo behind his silhouette |
| `auto_dpi_scale` | true | multiply the sizes above by your display scaling |

The window sizes itself around whatever those add up to, so raising
`bubble_width` is enough — there is no canvas size to keep in sync.

### The animation

Same 18×11 silhouette as always, and every offset in `sprite.py` is a whole
number of cells — nothing moves by a fraction of a pixel, and a test enforces it.
What changed:

- a **4-beat walk cycle** — contact, passing, contact, passing — with the legs
  alternating in pairs, the body rising on the passing beats, and the arms
  swinging opposite the legs. (The legs alternate by *height*, not by striding
  sideways: they sit one cell apart, so a sideways stride just fused them into a
  blob.)
- **squash and stretch**, one cell each, when he starts and stops moving, so
  setting off and planting have weight
- **he faces the way he walks** — the body leans a cell and the eyes shift a cell
- **idle loops of 4–8 frames per mood** instead of a 2-frame bob, each with its
  own character: annoyed shakes, disappointed sinks, sleepy breathes slowly,
  curious tilts side to side
- **three-frame blinks** (half, shut, open) rather than an on/off flicker
- **a kick loop while you drag him** — each leg becomes a diagonal staircase
  reaching out and down, flipping direction every frame, at the fastest tempo he
  has. His mood, eyes, held item and fireworks all carry on unchanged: an
  annoyed Clawd being dragged is still an annoyed Clawd.

`python tests/preview_anim.py out.png` renders every state as a frame strip so
you can check a change without running the app.

### Where the bubble sits

Its **left** edge is anchored just left of his head, so the tail always lands on
him; a bubble too wide to fit from there slides back left and the tail clamp
still finds his head. It used to right-align every bubble to the canvas edge —
invisible on a long line, but a short one like `....` ended up at the far right
with its tail pointing at empty space. A bubble narrower than its own tail is
widened around the text so it can't come out malformed.

### The icons he holds up — off

`appearance.show_items` is **false**, so he never holds anything up, in any
state. The frame loop clears the slot every tick rather than trusting each
caller, so nothing can leave one on screen. Set it `true` to bring them back.

Everything below still exists behind that switch.

The built-in set is **37 hand-drawn 16×16 icons** (was 16 at 8×8). At 8×8 there
are 64 pixels total and, once the outline is drawn, nothing left to say what the
thing is — a capacitor and a resistor came out as the same grey smudge. Each item
pixel is half a Clawd pixel, so the icon takes exactly the same space on screen
as before with four times the detail.

Nothing in the set is a pure-black silhouette, because black vanishes against a
dark desktop; structural lines use light grey or white. A test enforces that too.

Topics the built-in set doesn't cover are drawn by the API once and cached in
`items_cache.json`, so each topic costs one call ever. Old 8×8 cache entries are
upscaled rather than discarded. To add your own, just draw one in `ITEMS` in
`core/items.py` — 16 strings of 16 characters, palette key per pixel, `.` for
transparent — and add keywords for it to `KEYWORDS`.

## If he ever disappears

He shouldn't be able to any more, but if he is not on screen: **quit and
relaunch.** The saved position is re-clamped at startup, so he comes back to a
visible spot on his own. If that somehow isn't enough, delete the `position`
line from `appearance` in `config.json` and he starts in the bottom-right
corner.

What went wrong before, for the record: both the window clamp and the walking
clamp were written against the *window* rectangle. The window is mostly empty
space above him — `CLAWD_OY` is over a thousand pixels on a 200% display — so
"the window overlaps the screen" was true while his sprite was hundreds of
pixels below the bottom edge. Chasing a *minimised* window made it worse:
Windows reports those at (-32000, -32000), and he walked straight for it. Both
clamps now bound the sprite, bogus window rects are ignored, and `clawd.log`
records the desktop bounds and his position at every launch.

## Tuning how much he moves

`motion` in `config.json`:

| key | default | what it does |
|---|---|---|
| `enabled` | true | false keeps him parked in his corner |
| `speed_px_per_sec` | 260 | walking speed |
| `follow_after_seconds` | 8 | seconds off-task before he starts shadowing your cursor |
| `block_at_tier` | 1 | tier at which he occupies the middle of your window (1 = 2 min) |
| `patrol_at_tier` | 2 | tier at which he starts pacing (2 = 5 min) |
| `block_seconds` | 40 | every 40s of blocking he steps aside for 14s on his own |

If he's too much, raise `block_at_tier` to 3 or set `enabled` to false. Dragging
him somewhere makes that spot his new home.

## Tuning his personality

`core/bank.py` is the entire offline vocabulary, plainly editable - 125 lines
across greetings, praise, the four nag tiers, brainrot, gaming/shopping/social
variants, tidbits, quizzes. Placeholders `{what} {mins}
{course} {hour} {answer}` are filled at runtime.

There is a tone note at the top of that file worth keeping: he's a gremlin, not
a bully — the joke is always about the tab, never about you.

## Files

```
clawd.pyw          entry point
config.json        settings (edit freely)
state.json         focused minutes per day (auto)
items_cache.json   cache of API-generated pixel icons (auto)
clawd.log          errors + session summaries (auto)
core/watcher.py    foreground window + idle time, pure ctypes
core/classify.py   study / stray / idle rules
core/bank.py       the offline comment bank
core/brain.py      line selection + Anthropic API calls
core/sprite.py     the pixel Clawd
core/items.py      8x8 pixel icon set, topic mapping, generation cache
core/motion.py     cursor following / window blocking / patrolling
core/single.py     one-at-a-time lock
core/tray.py       notification-area icon (Windows)
core/ui.py         overlay window + speech bubble
core/app.py        the state machine
tests/test_logic.py    headless checks — python tests/test_logic.py
tests/preview.py       renders clawd_moods.png
tests/simulate.py      fast-forward demo of the whole ladder in ~2 min
```

## Privacy

Everything runs locally. With API mode **off**, nothing leaves your machine at
all. With it on, what's sent is: the foreground window title, and — only when
you double-click him — a downscaled JPEG of the window in front.
Nothing is stored anywhere except `state.json` (a daily minute count) and
`clawd.log`.
