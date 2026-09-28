---
name: chat-message-voice
description: How to draft a Slack, Teams, or other chat/DM message so it sounds like Sachin actually typed it, not like an AI assistant wrote it. Encodes his real cadence (terse, lowercase-starting, punctuation-optional on short lines, typos left in over slowing down, "also"/"or whatever" as bolt-on connectors, Slack-shortcode emoji reached for naturally) plus a hard "don't" list distilled from Wikipedia's "Signs of AI writing" essay, mapped to chat specifically. Use this whenever asked to draft, write, suggest, or punch up text for a Slack message, Teams message, DM, or channel post — not for PR descriptions (see pr-storyteller), commit messages (see conventional-commits), or docs/emails, which have their own registers. Trigger even when the request just says "send a message to X" or "let them know Y" without naming Slack/Teams explicitly, if the context is clearly a chat tool.
---

# Chat Message Voice (Slack / Teams / chat drafts)

## Verified state — seeded from live chat, not real Slack/Teams samples

Created 2026-09-17. Sachin chose to seed this from his own direct messages to Claude in that
session rather than pasting real Slack/Teams messages — faster, but a different register (quick
task instructions to an AI assistant, not colleague-to-colleague chat). **Treat everything below
as a starting approximation, not a confirmed voice.** If a drafted message doesn't sound right,
that's a signal to ask Sachin for 8-10 real Slack/Teams messages and recalibrate this file — not
to just patch the one message and move on.

Real messages this was built from (verbatim, same conversation):
- "check one-solution frontend archtiecture also and make sure you write below as common skill or whatever for both claude and copilot."
- "can you update my github repo as well"
- "push all"
- "i need a common skill when i ask you for a chat msg like slack, teams etc. create a .skill.md to have Claude imitate your communication style, cadence and phrasing :brain::stonks:"

Traits distilled from these:
- Sentence-initial lowercase, routinely — not a rule he states, just what he does
- Terse: says the thing, stops. No scene-setting, no "just wanted to check in"
- Punctuation is optional on short lines — a command or quick question often has no trailing
  `.`/`?` at all ("push all", "can you update my github repo as well")
- Typos/abbreviations left uncorrected in the moment ("archtiecture", "msg") — speed over polish
- Filler used sparingly and specifically, not as padding: "or whatever" (verbal shrug), "also"
  (bolt-on for a second ask, not a rewritten compound sentence)
- No pleasantries, no "please"/"thanks" scaffolding on direct asks
- Comfortable, unexplained technical jargon — doesn't stop to define terms
- Reaches for Slack-native colon-emoji shorthand (`:brain:`, `:stonks:`) even outside Slack —
  real muscle memory, not a one-off. Use at most one per message, and only where it's doing an
  actual job (a tone marker or reaction), never as decoration.

## The rule: sound like someone who types fast and skips the politeness performance

1. Lead with the actual point. No "Hi team, hope you're doing well" unless the audience genuinely
   expects a greeting (see Audience below).
2. One idea per line where that reads naturally — let line breaks do structuring work a formal
   list would otherwise do.
3. Drop terminal punctuation on short, single-clause lines. Treat it like real chat, not email.
4. State status/asks plainly: "PR's up, needs a review" beats "The pull request has been
   submitted and is awaiting your review."
5. If something's inferred or pending, say so in one clause, not a hedge paragraph: "still
   waiting on QA" beats "It's important to note that we are currently awaiting confirmation from
   the QA team."
6. Use "also"/"btw"/"oh and" to bolt on a second thought instead of restructuring into one
   dense compound sentence.
7. At most one emoji, doing real work — never as a bullet marker or paragraph opener.

## Hard "don't" list — from Wikipedia's Signs of AI Writing, mapped to chat

This half is general, not personalized, but it's well-grounded (pulled directly from the essay,
not recalled from memory) and catches the tells that make any drafted message read as
AI-generated regardless of whose voice you're aiming for.

**Banned vocabulary** (never use these in a drafted chat message): *additionally* (as a sentence
opener), *align with*, *boasts*, *bolstered*, *crucial*, *delve*, *emphasizing*, *enduring*,
*enhance*, *fostering*, *garner*, *highlight* (as a verb), *interplay*, *intricate(cies)*, *key*
(as a vague adjective), *landscape* (abstract noun), *meticulous(ly)*, *pivotal*, *robust*,
*showcase*, *tapestry*, *testament*, *underscore* (as a verb), *valuable*, *vibrant*,
*groundbreaking*, *renowned*, *exemplifies*, *profound*, *stands/serves as* (instead of "is"),
*is a testament to*, *reflects broader*, *contributing to the*, *setting the stage for*,
*represents a shift*, *focal point*, *indelible mark*, *industry reports*, *experts argue/agree*,
*several sources note*.

**Banned sentence patterns**:
- "Not just X, it's Y" / "Not only X but Y" — the classic AI parallelism
- Avoiding a plain "is"/"are"/"has" in favor of "serves as", "stands as", "boasts", "represents",
  "functions as"
- Ending a sentence with a dangling "-ing" clause ("...,  ensuring the team stays aligned.")
- Rule-of-three lists used as rhetorical flourish ("fast, reliable, and scalable")
- Em dash as a default connector — use a period, a comma, or just a line break in chat instead

**Banned formatting habits**:
- Bold text as decoration ("**Update:**") — a chat message rarely needs bold at all; if it does,
  bold one word, not a clause
- Emoji as a bullet/header marker ("🚀 **Deployed!** 🎉")
- A numbered/bulleted list for something that's really two short sentences
- Title Case Headings inside a chat message
- Curly "smart quotes" — plain quotes only, this is chat, not a manuscript

**Banned rhetorical tics**:
- A hedging preamble before the actual point ("It's worth noting that...", "It's important to
  mention...")
- A reassurance-after-caveat pattern ("Despite this issue, the overall approach remains solid.")
- Managing the reader like an audience ("Let me know your thoughts!", "Excited to hear what you
  think!") unless that's genuinely the ask
- A knowledge-cutoff-style disclaimer ("As of my last update...") — never relevant in chat
- A generic closing call-to-action that just restates the message

## Audience-aware register (a default ladder — not yet verified per audience)

All the seed messages above were written to one audience: Claude, in a task-instruction context.
This ladder is a reasonable default extrapolation, not something confirmed against Sachin's real
per-audience Slack history. Say so if it's ever wrong, and prefer real examples over this table
the moment they're available.

| Audience | Shift from the base voice |
|---|---|
| Direct teammate / peer, 1:1 or small channel | Base voice as above: terse, lowercase-friendly, no pleasantries, technical shorthand fine |
| Broad/public channel (e.g. `#dev-team`, `#announcements`) | Slightly more complete sentences and kept punctuation — something posted to a wide audience should parse cleanly at a glance — but still no corporate throat-clearing, still no listicle unless it's genuinely a list |
| Manager / more senior stakeholder | Still terse and direct — this voice doesn't perform deference — but lead with the outcome/ask first, skip jargon they may not share, and keep terminal punctuation on anything with more than one clause |
| PR reviewer / cross-team request | State the ask and the "why" in a line or two each — closer to this repo's `pr-storyteller` bar (tight, no boilerplate) than to a 1:1 ping |

## How to use this when asked to draft a chat message

1. Work out which audience register applies (from context, or ask if genuinely unclear).
2. Draft in one pass using the positive-model rules above.
3. Read it back against the "Hard don't list" — if a banned word or pattern slipped in, cut it,
   don't soften it.
4. Prefer shorter over "complete" — three short lines beat one dense, well-formed paragraph.
5. Never sign off with a generic closer ("Let me know if you have questions!") unless that's a
   genuine, specific ask.

## What NOT to do

- Don't pad a two-line message into a structured five-part update because it "seems more
  complete" — brevity is the actual house style here, not a Claude-default to override.
- Don't reintroduce the AI-writing tells this skill exists to avoid — catching "it's important to
  note" or "stands as a testament" mid-draft means stop and rewrite the clause plainly, not
  soften it.
- Don't treat the audience ladder as verified — it's a reasonable default built without real
  per-audience samples. Say so if asked, and prefer real examples the moment Sachin supplies them.
- Don't use this for PR descriptions, commit messages, or docs — those have their own skills
  (`pr-storyteller`, `conventional-commits`) and registers.
