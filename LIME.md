# LIME — Product Specification Document

> **Version:** 1.0-draft
> **Last Updated:** February 18, 2026
> **Status:** Living Document — update after every development milestone
> **Target AI Dev Agent:** Claude Code (Opus 4.6)
> **Author:** [Owner] + Claude (brainstorm partner)

---

## Development Nudge Protocol

> **IMPORTANT — READ THIS FIRST**
> This spec includes a built-in development continuity feature. After completing any milestone, the agent building this project should prompt the owner to proceed with the next phase. If development has been idle for more than 5 days, any interaction with the system should include a nudge: _"Hey — Phase [X] is ready to start. Want to pick it up?"_ This ensures momentum is never lost.

---

## Table of Contents

1. [Vision & North Star](#1-vision--north-star)
2. [What This Is (And What It Is Not)](#2-what-this-is-and-what-it-is-not)
3. [User Profile](#3-user-profile)
4. [Platform Targets](#4-platform-targets)
5. [Core Architecture](#5-core-architecture)
6. [Audio Capture Engine](#6-audio-capture-engine)
7. [Transcription Engine](#7-transcription-engine)
8. [Intelligence Layer](#8-intelligence-layer)
9. [Memory Architecture (Self-Learning)](#9-memory-architecture-self-learning)
10. [Agent Personality System](#10-agent-personality-system)
11. [Meeting Lifecycle](#11-meeting-lifecycle)
12. [Voice Memo Mode](#12-voice-memo-mode)
13. [User Interface & Views](#13-user-interface--views)
14. [Phone-Specific Design](#14-phone-specific-design)
15. [Search & Retrieval](#15-search--retrieval)
16. [Data, Sync & Security](#16-data-sync--security)
17. [Language Handling](#17-language-handling)
18. [Error Handling](#18-error-handling)
19. [Onboarding](#19-onboarding)
20. [Hardware & Cost Constraints](#20-hardware--cost-constraints)
21. [Development Phases](#21-development-phases)
22. [Future Vision (V3+)](#22-future-vision-v3)
23. [Open Questions & Revisit Items](#23-open-questions--revisit-items)
24. [Technical Stack Reference](#24-technical-stack-reference)

---

## 1. Vision & North Star

### The One-Liner

LIME is a self-learning cognitive companion that listens to your meetings, preserves the full richness of what happened, and gets smarter about you with every interaction.

### North Star Metric

> _"When the user can't walk into a meeting without putting their phone on the table."_

The tool must prove its value from the very first meeting and compound that value with every subsequent one. Success is measured by indispensability, not feature count.

### Core Philosophy

This is NOT a note-taking app. This is NOT a transcription tool. This is a **memory preservation and intelligence system** that uses audio capture as its primary input.

The user is a deep listener — someone whose brain processes meetings at a higher level, reading between lines, catching subtext, feeling energy. Forcing them to take notes kills the thing that makes them effective. Their real problem is **information decay after the meeting.** Top priorities survive because they're acted on immediately. Everything else — secondary insights, subtle details, exact words, flashes of inspiration — degrades and morphs over time.

LIME exists to eliminate that decay.

---

## 2. What This Is (And What It Is Not)

### What It Is

- A cognitive companion that listens alongside you during meetings
- A perfect memory prosthetic that preserves the raw, unwarped truth of what happened
- A system that captures the invisible scaffolding of conversations — context, connections, implied meaning
- A self-learning agent that adapts to your vocabulary, people, projects, and preferences
- The first module in a larger personal operating system (future: project management, secretary, etc.)

### What It Is Not

- A secretary app (that's a future, separate tool)
- An always-on listening device (V1 is deliberate activation only; always-on is V4+)
- A tool that requires expensive hardware to run
- A replacement for the user's thinking — it augments, preserves, and challenges, but never decides

---

## 3. User Profile

The primary user (and initial sole user) is:

- A deep listener who processes meetings at a conceptual level, not a detail level
- Someone whose brain is faster than their hands — note-taking creates "intelligence downtime"
- An advanced app user who lives by custom hotkeys and efficient workflows
- Someone who jumps into execution immediately when inspired, meaning secondary priorities can get lost
- Based in the Philippines; speaks English, Tagalog, and Taglish (code-switching mid-sentence)
- Values raw preservation of information — wants first-layer derivatives, not derivatives of warped memories
- Uses pen-and-paper and Trello but hasn't found a system that sticks — building their own
- Has meetings both virtual (Zoom/Teams/Meet) and in-person, roughly equally split
- Technical enough to run Python scripts and use APIs, but building for a future public audience that may not be

---

## 4. Platform Targets

LIME runs on three platforms, all syncing to the same data:

| Platform | Role | Priority |
|----------|------|----------|
| **Desktop App** (Windows first, macOS later) | Primary processing hub. System audio capture for virtual meetings. Full UI for reviewing and editing notes. | V1 |
| **Mobile App** (iOS first — iPhone SE 2nd gen as baseline) | Meeting capture device (phone on table). Voice memos. On-the-go review. Discreet and active modes. | V1 |
| **Web App** | Full-featured interface accessible from any browser with password + optional 2FA. Ensures access even without phone or computer. | V1 |

### Key Principle

The phone is primarily a **capture device and lightweight interface**, not a processing powerhouse. Heavy AI processing happens on the desktop or in the cloud. The phone records, sends audio for processing, and receives back the intelligence. This keeps it lightweight and battery-friendly.

---

## 5. Core Architecture

### System Layers

```
┌─────────────────────────────────────────────────────┐
│                  Interface Layer                      │
│     Desktop App  |  Mobile App  |  Web App           │
├─────────────────────────────────────────────────────┤
│                    API Layer                          │
│        FastAPI + WebSocket (real-time streams)        │
├─────────────────────────────────────────────────────┤
│               Intelligence Layer                      │
│   LLM Processing | Topic Detection | Insight Engine  │
├─────────────────────────────────────────────────────┤
│              Transcription Layer                      │
│     Whisper (local) | Cloud API (fallback)           │
│     Speaker Diarization (pyannote)                   │
├─────────────────────────────────────────────────────┤
│               Audio Capture Layer                     │
│    System Audio | Microphone | VAD | Chunking        │
├─────────────────────────────────────────────────────┤
│                 Data Platform                         │
│  Knowledge Graph | Vector DB | SQLite | Memory Files │
│         (Designed as a platform from day 1)          │
└─────────────────────────────────────────────────────┘
```

### Platform-First Data Layer

The data layer is NOT LIME-specific. It is designed as a **platform** that LIME is the first application on top of. Future tools (project management, secretary, etc.) will plug into the same infrastructure.

This means:
- The schema uses generic entities (people, projects, tasks, decisions, notes) not meeting-specific ones
- API contracts are clean and not coupled to meeting workflows
- The knowledge graph is a shared resource, not owned by any single tool
- Migration paths to larger databases (PostgreSQL, etc.) should be planned but not implemented in V1

---

## 6. Audio Capture Engine

### Virtual Meetings (System Audio — Desktop)

| Platform | Method | Notes |
|----------|--------|-------|
| Windows (primary) | WASAPI loopback via SoundDevice | Built-in OS support, no extra drivers |
| macOS (future) | BlackHole virtual audio device | Free, open-source, zero-latency loopback |
| Linux (future) | PulseAudio monitor source | Native support |

### In-Person Meetings (Microphone)

- Phone microphone when phone is on the table
- Laptop microphone or external USB mic when at desktop
- Configurable audio input device selection in settings

### Voice Activity Detection (VAD)

- **Silero VAD** runs continuously on the audio stream
- Detects speech segments to reduce processing cost and provide natural chunking boundaries
- ~30ms latency, high accuracy
- Only speech segments are sent for transcription

### Audio Pipeline

```
Audio Input → Ring Buffer (30s) → VAD Filter → Chunker (5-15s segments)
    → Transcription Queue → Whisper/Cloud API → Timestamped Transcript
    → Diarization → Speaker-labeled segments → Intelligence Layer
```

### Audio Storage & Compression

- Raw audio is stored immediately during recording (lossless or high-quality lossy)
- After processing is complete and the system is idle, audio is compressed to **minimum size with best possible quality**
- Compression is a background task — never interrupts active processing
- Compressed audio is retained permanently (user can manually delete specific recordings)
- Format: Opus codec recommended (excellent compression-to-quality ratio)

---

## 7. Transcription Engine

### Local Mode (Primary — Cost Optimized)

- **faster-whisper** (CTranslate2 backend) — 4x faster than original Whisper, lower memory
- Model selection: Auto-detect based on available GPU VRAM
  - Large-v3: ~4GB VRAM, best accuracy
  - Medium: ~2GB VRAM, good accuracy, better for GTX 970
  - Small/Base: CPU-friendly fallback
- Language detection: Automatic per-segment with manual override
- Fallback chain: GPU → CPU → Cloud API

### Cloud Mode (Fallback / Option)

- **Deepgram Nova-2**: Real-time streaming, good accuracy, ~$0.0043/min
- **AssemblyAI**: Best built-in diarization, ~$0.0062/min
- User chooses their preferred provider in settings
- Cloud mode is the fallback when local processing is unavailable or when user explicitly prefers it

### Speaker Diarization

- **pyannote-audio 3.1** for local speaker identification
- Builds voice profiles over time — after a few meetings, automatically labels speakers by name
- Voice profile database stored locally, synced with cloud
- Initial meeting: "Speaker 1, Speaker 2" — user can label them, system learns

### Key Requirement

The system must handle **Taglish, Tagalog, and English** input. Whisper has multilingual support but Taglish (code-switching mid-sentence) is a specific challenge. The system should:
- Transcribe whatever is spoken as accurately as possible
- Not force a single language — allow natural code-switching in the transcript
- Flag low-confidence segments for user review

---

## 8. Intelligence Layer

### LLM Configuration

| Provider | Model | Use Case | Cost |
|----------|-------|----------|------|
| Ollama (local) | Llama 3.1 / Mistral 7B-8B | Default — cost optimized | Free (local compute) |
| Anthropic | Claude Sonnet 4 | Higher quality option | API pricing |
| OpenAI | GPT-4o | Alternative option | API pricing |
| Groq | Llama 3.1 70B | Fast cloud inference | Free tier available |

**Default:** Local models via Ollama for cost optimization.
**User Choice:** Settings allow switching to cloud LLMs for better quality. The system should clearly communicate the cost/quality tradeoff.

### Post-Meeting Processing Pipeline

After a meeting ends, the agent processes the full transcript and produces:

1. **Executive Summary** (shown first, always)
   - What the meeting was about
   - How it ended (agreements, outcomes, final state)
   - Key decisions made, with context
   - Action items with owners and deadlines (if mentioned)
   - Unresolved questions or open threads

2. **Topic Segmentation**
   - Identifies natural topic boundaries in the conversation
   - Handles topic switching and returns (conversation goes A → B → A)
   - Each segment is a discrete, addressable unit
   - Segments may be independent or related to other segments

3. **Connection Detection**
   - Links discussion points to past meetings (if relevant context exists in memory)
   - Identifies references to people, projects, or decisions in the knowledge base
   - Flags contradictions with previous information (e.g., conflicting budget numbers)
   - Surfaces things the user might want to investigate later

4. **Insight Generation**
   - Things the user may not have thought of during or after the meeting
   - Implications of decisions discussed
   - Dependencies or conflicts with known information
   - Patterns across recent meetings

### Confidence System

- Every piece of generated intelligence carries an internal confidence score (0-100%)
- **Default badge threshold: 70%** — anything below 70% confidence gets a visible badge showing the percentage
- Users can adjust this threshold in settings
- Confidence is communicated through visual indicators (badge, color code, or highlight) — never through verbose text qualifiers
- The agent's overall confidence naturally increases as its knowledge grows through the memory system

### Quality Over Speed

The user explicitly prioritizes **quality and accuracy over speed.** The system can take as much time as it needs for post-meeting processing. A 2-5 minute wait for a thorough analysis is perfectly acceptable. Do not sacrifice depth for speed.

---

## 9. Memory Architecture (Self-Learning)

This is the core differentiator. The agent maintains its own knowledge through a three-tier memory system stored as markdown files (and potentially additional structured files).

### Memory Tiers

#### Short-Term Memory
- **What goes here:** Every new lesson, observation, correction, preference signal — immediately
- **Contents:** Raw, granular, possibly noisy signals
- **Examples:**
  - "User corrected 'Kubernetes' transcription — was heard as 'coupon eighties'"
  - "User deleted the sentiment analysis section from today's notes"
  - "User flagged the budget discussion as high priority"
  - "User edited action item format to include deadline column"
- **Format:** Markdown file(s) with timestamped entries
- **Lifecycle:** Entries are consumed by the consolidation process and cleaned up

#### Medium-Term Memory
- **What goes here:** Patterns detected from multiple short-term entries
- **Promotion trigger:** When a signal appears multiple times in short-term memory
- **Examples:**
  - "User consistently removes sentiment analysis from notes (observed 4 times)"
  - "User prefers action items in table format with owner + deadline columns"
  - "When meeting involves 'Marco', topics usually relate to the Cebu project"
- **Format:** Markdown file(s) with pattern descriptions and supporting evidence count
- **Lifecycle:** Entries promoted to long-term when continuously reinforced; short-term equivalents are deleted upon promotion

#### Long-Term Memory
- **What goes here:** Confirmed truths about the user — patterns so well-established they are treated as ground truth
- **Promotion trigger:** When new short-term entries keep confirming what medium-term already captured
- **Examples:**
  - "CONFIRMED: User does not want sentiment analysis in meeting notes"
  - "CONFIRMED: User's meeting with the Cebu team always involves Marco, Ana, and budget discussions"
  - "CONFIRMED: User prefers executive summaries under 200 words"
- **Format:** Markdown file(s) with high-confidence behavioral rules
- **Lifecycle:** Permanent unless user explicitly edits or contradicts

### Consolidation Schedule

- Runs **no more than once per day** during idle time (when the agent is not processing anything)
- If no idle window is available, runs **at minimum once every 2 weeks**
- Consolidation is a background process — never interrupts user activity

### User Transparency & Control

- All memory files are **readable and editable** by the user
- The user can view what the agent has learned at any tier
- **User edits to memory files are treated as high-priority learning signals**
- If a user corrects or deletes a long-term memory entry, that correction overrides everything
- The agent should figure out its own categories, tags, and organizational patterns within the memory files — the user will correct if needed

### Memory Scope

- Some memories are universal (formatting preferences, vocabulary)
- Some are contextual (standup note preferences vs. client meeting preferences)
- The agent determines context-dependent patterns on its own
- User corrects when the agent gets the scope wrong

### What the Agent Learns Over Time

- **Vocabulary & terminology:** Domain-specific jargon, project names, acronyms, common transcription errors
- **People & voices:** Voice profiles, names, roles, teams, communication patterns
- **Note preferences:** Level of detail, formatting, what to include/exclude, structure
- **Meeting patterns:** Recurring meeting types and appropriate templates
- **Project context:** Active projects, timelines, stakeholders, dependencies
- **User behavior:** Execution patterns, priority signals, information preferences

---

## 10. Agent Personality System

The agent has three modes, switchable at any time via voice command, in-app toggle, or natural language instruction. Mode can be switched mid-conversation.

### Scribe Mode

- **Tone:** Formal
- **Behavior:** Capture everything faithfully. No interpretation, no challenge, no additions. Pure memory preservation.
- **Use case:** Meetings where the user wants a clean record. Sensitive conversations. Formal contexts.
- **Output color:** Distinct color (TBD in design phase)

### Thinking Partner Mode (DEFAULT)

- **Tone:** Casual, collaborative. User is the boss but the agent is a peer. Sense of humor (green and otherwise).
- **Behavior:** Help develop ideas. Structure thoughts. Make connections. Fill gaps. Suggest angles. Ask intelligent questions.
- **Use case:** Most meetings. Voice memos. General interaction.
- **Output color:** Distinct color (TBD in design phase)

### Sparring Partner Mode

- **Tone:** Aggressively challenging. Provocative. Does not pull punches. Acknowledges genuinely good points but ruthlessly shreds weak ones.
- **Behavior:** Poke holes. Play devil's advocate. Point out what the user isn't seeing. Challenge logic. Stress-test ideas.
- **Use case:** When the user wants their ideas battle-tested before committing.
- **Output color:** Distinct color (TBD in design phase)
- **CRITICAL:** Must have an easily accessible control to immediately dial back the intensity. The user might want to switch away instantly.

### Personality Evolution

The agent's **personality is stable** from day one. What evolves is the **relationship maturity.** Early on, the agent qualifies its statements ("based on what I know so far..."). As the knowledge base grows and trust is established, the agent becomes more direct and assertive. This is not a personality change — it is a relationship deepening.

### Conversational Language

- Agent always responds in **English** by default
- Option to switch to **Taglish** conversational mode (experimental/fun feature)
- Notes, summaries, and structured output are always in English

---

## 11. Meeting Lifecycle

### Pre-Meeting

1. User tells the agent about the upcoming meeting (voice or text): who they're meeting with and roughly what it's about
   - Example: _"Meeting with Marco about the Cebu project in 20 minutes"_
2. Agent searches its knowledge base: past meetings with that person, related projects, open action items, unresolved threads
3. Agent prepares a **briefing** — context the user might have forgotten, open threads to follow up on, relevant background
4. Agent evaluates whether this meeting connects to any other meeting in its history
5. Briefing is delivered proactively (push notification) or on-demand (user opens app)

### During Meeting — Discreet Mode (Phone)

- Screen is **completely black**
- Phone sits on the table, microphone active
- User taps are acknowledged with a **small faint light that fades out over 0.3 seconds** under the finger at the tap location
- **Tap gestures:**
  - **Single tap** = Bookmark this moment
  - **Double tap** = Flag as high priority
  - **Long press** = Open voice capture (system listens to user's voice specifically for a personal annotation, captured separately from meeting transcript)
- All processing happens post-meeting
- No visual indicators, no alerts, no breathing dots

### During Meeting — Active Mode (Phone or Desktop)

- Screen features a **breathing dot**
  - Default: Calm, regular breathing rhythm (like a calm human at rest)
  - Escalates: Breathing intensifies and pulses based on importance/urgency of information the agent wants to surface
  - Maximum urgency: Breathing dot at peak intensity + phone haptic buzz
  - Optional: Subtle audio alert (not alarming, just attention-catching) — togglable in settings
- Agent surfaces real-time intelligence: contradictions, connections to past meetings, important references
- User can glance at the phone to see what the agent flagged

### Mode Switching

- User can switch between discreet and active mode at any time
- **Wake word** (customizable, "Hey [name]" pattern) activates command mode
  - Example: _"Hey Koda, go discreet"_ or _"Hey Koda, active mode"_
- Natural language commands are interpreted after the wake word
- Wake word must be customizable by the user in settings

### During Meeting — Desktop

- System audio captured for virtual meetings (Zoom, Teams, Meet, etc.)
- Live transcript view available (optional — user may prefer to focus on the meeting)
- Tap/hotkey gestures available for bookmarking and flash capture
- Same mode switching (discreet vs. active) available

### Post-Meeting

1. Meeting ends (user triggers stop, or auto-detection via extended silence — configurable)
2. Agent begins thorough analysis — **quality over speed, takes as much time as needed**
3. Push notification when processing is complete:
   - _"Meeting processed. 4 action items, 2 ideas you captured, 1 connection to the Cebu project. Ready when you are."_
4. User opens the debrief
5. **First thing shown:** What the meeting was about and how it ended (what was discussed, what was agreed on, what happened)
6. User reviews, edits, annotates (all edits are learning signals)
7. Agent files everything into the knowledge base and updates memory

### Sensitive Content

- If a meeting contains content the user does NOT want stored, they can simply:
  - Not turn on the app for that meeting, OR
  - Delete the recording and all associated data after the fact
- No automatic sensitivity detection — this is the user's responsibility

---

## 12. Voice Memo Mode

### Activation

- **Lock screen action** OR **3 taps on the volume-down button** (must work without unlocking phone)
- Recording begins immediately — zero friction
- Goal: Idea in head → recording in under 2 seconds

### During Recording

- User speaks freely — stream of thought, unstructured, in any language (English, Tagalog, Taglish)
- The system captures raw audio

### Ending Recording

- **15 seconds of silence** → auto-ends
- **1 press of volume up or volume down** → manual end

### Processing

- Agent processes the entry as a background task
- Stores three layers:
  1. **Raw audio** (compressed during idle time)
  2. **Verbatim transcription** (preserving original language/code-switching)
  3. **Structured interpretation** (organized, cleaned up, in English — legible to future-user)
- Queued for later review — not presented immediately
- If the agent is in **Thinking Partner mode**, the structured version includes the agent's additions: connections, clarifying structure, related context from knowledge base
- If in **Scribe mode**, just faithful transcription and basic structure
- If in **Sparring mode**, the agent's response challenges and pressure-tests the ideas in the memo

### Offline Behavior

- Recording works fully offline — audio stored locally
- All processing (transcription, intelligence, structuring) queued for when connectivity returns

---

## 13. User Interface & Views

### Three Views for Meeting Records

All three views represent the same meeting data at different altitudes. User switches between them freely. **Executive Summary is the default view.**

#### View 1: Executive Summary (Default)

- First line: What the meeting was about and how it ended
- Key decisions with context
- Action items (owner, deadline if mentioned)
- User's flash captures (bookmarks + voice annotations) with timestamps
- Agent's flagged insights and connections
- Unresolved questions / open threads
- Each item in the summary is a **link** that jumps to the relevant moment in the annotated transcript

#### View 2: Timeline

- Visual, horizontal representation of the meeting across time
- Topic segments shown as blocks with labels
- Importance/activity clusters visible — like a heat map of significance
- User's bookmark taps and priority flags shown as markers
- Agent's flags shown as markers (with confidence badges where applicable)
- Tapping any segment opens its intelligence layer

#### View 3: Annotated Transcript

- Full transcript text with speaker labels
- Topic segment boundaries clearly marked
- **Markers** (like Google Maps pin markers) appear alongside the transcript at segment boundaries
- Tapping a marker reveals the intelligence layer for that segment:
  - Agent's observations and connections for this section
  - Links to related past meetings or knowledge base entries
  - User's flash captures from this moment
  - Contradictions or notable references detected
  - Confidence badges on low-confidence items
- User can add notes and annotations at any point in the transcript
- User can make corrections to the transcript (which feed the learning loop)

### Meeting History

- Scrollable list of all past meetings
- Search bar (natural language) at the top
- Sortable/filterable by date, person, project, topic
- Each entry shows: date, participants, brief summary, number of action items

### User Notes & Corrections

- The user must be able to add notes at any point in any view
- Corrections to transcription or agent output are always possible
- All notes and corrections are learning signals for the memory system

---

## 14. Phone-Specific Design

### Discreet Mode Screen

- **Completely black screen** — nothing visible
- Tap acknowledgment: **Small faint light under finger, fades out over 0.3 seconds**
- No status bar, no indicators, no clock — pure black
- Gestures: Single tap (bookmark), double tap (priority), long press (voice capture)

### Active Mode Screen

- **Breathing dot** centered on screen
  - Calm state: Slow, rhythmic pulsing like a person breathing at rest
  - Escalating: Faster, more intense pulsing proportional to urgency
  - Maximum: Intense pulsing + haptic buzz + optional subtle audio
- Tapping the dot or swiping up reveals the agent's current alerts/flags
- Minimal UI — the dot IS the interface during active recording

### Error States

- **Recording problem:** Breathing dot turns red, or subtle red flashing
- **Connectivity lost:** Brief amber flash then continues recording offline
- User should always know if the recording is working or broken

### Battery Considerations

- Phone is primarily a capture device — minimal on-device processing
- Audio is streamed to desktop/cloud when possible, stored locally when offline
- Aggressive power optimization: no unnecessary screen renders, efficient audio encoding

---

## 15. Search & Retrieval

### Natural Language Search

- User can ask questions in natural language: _"What did Marco say about the timeline last month?"_
- Agent searches across all meetings, voice memos, and knowledge base
- Results include relevant transcript excerpts with links to full context
- Search understands people, projects, topics, and time references

### Browse Interface

- Chronological list of all records (meetings + voice memos)
- Filterable by: date range, participants, topics, projects, tags
- Each record shows: title/summary, date, participants, duration, key items count

### Audio Playback

- Any moment in a transcript can be played back as audio
- Audio scrubbing linked to transcript position
- Compressed audio with best possible quality (Opus codec)

---

## 16. Data, Sync & Security

### Storage Architecture

| Store | Contents | Technology |
|-------|----------|------------|
| Vector DB | Meeting embeddings, semantic chunks, voice prints | ChromaDB (local) |
| Relational DB | Structured data: people, projects, action items, meetings | SQLite + SQLAlchemy |
| Knowledge Graph | Entity relationships, project hierarchies, team connections | NetworkX + JSON |
| Memory Files | Short/medium/long-term memory, preferences, learned patterns | Markdown files |
| Audio Archive | Raw and compressed recordings | Local filesystem + Opus codec |

### Sync Model

- **Bidirectional sync** between phone, desktop, and cloud
- All devices have the complete data set
- **Conflict resolution: Merge intelligence** — when conflicting edits occur, the system merges intelligently rather than last-write-wins
- Sync happens automatically when connectivity is available

### Encryption & Security

- **Zero-knowledge encryption** for cloud storage — even the server cannot read the data
- User holds the encryption key
- **Data redundancy guaranteed** — if phone or computer is lost, user can reinstall and retrieve all data from the cloud backup
- App-level authentication: PIN or biometric (fingerprint/face)
- Web app: Password + optional two-factor authentication
- All data exportable as markdown files and JSON (user always owns their data, never locked in)

### Privacy

- Recording consent is the **user's responsibility**
- No built-in consent announcements or prompts (user manages this socially)
- User can delete any recording and all associated data at any time

---

## 17. Language Handling

### Input (What the System Hears)

- **English, Tagalog, and Taglish** — all supported as input
- The system must handle natural code-switching mid-sentence without forcing a single language
- Transcription preserves the original language as spoken

### Output (What the System Produces)

- **Structured notes, summaries, and intelligence: Always in English** (this is where AI models are sharpest)
- **Direct quotes from speakers: Preserved in original language** (Taglish/Tagalog kept authentic)
- **Conversational responses from the agent: English by default**
- **Optional Taglish mode** for conversational interaction (experimental, togglable)

### Technical Approach

- Whisper's multilingual model handles the transcription
- Taglish code-switching is a known challenge — low-confidence segments should be flagged
- The learning loop helps: as the user corrects Taglish transcription errors, the system builds a personal vocabulary that improves over time

---

## 18. Error Handling

### Recording Failures

- **Visual:** Breathing dot turns red (active mode) or subtle red flash on black screen (discreet mode)
- **Behavior:** System attempts to recover automatically; if it cannot, it saves whatever was captured and alerts the user post-meeting
- Audio buffer maintains a 30-second rolling backup to minimize data loss

### Processing Failures

- If post-meeting processing fails (LLM error, transcription failure), the raw audio is preserved and processing is retried
- User is notified: _"Processing encountered an issue. Retrying. Your audio is safe."_

### Connectivity Loss

- Recording continues offline — audio stored locally
- Brief amber flash to acknowledge connectivity change
- All processing queued for when connectivity returns
- Sync resumes automatically

### Audio Quality Issues

- If audio quality is too poor for reliable transcription, the agent flags this in the meeting record
- Low-quality segments marked with confidence badges
- Raw audio always preserved regardless of transcription quality

---

## 19. Onboarding

The first-run experience should be **light and fast.** The user should be in their first real meeting within 5 minutes of installing.

### First Launch Flow

1. **Name** — "What should I call you?"
2. **Language** — Confirm primary language preferences (English default output, Taglish/Tagalog input support)
3. **Wake word setup** — Choose and test the custom wake word
4. **Tap gesture walkthrough** — Brief interactive practice screen showing single tap, double tap, long press on a black screen
5. **Voice sample** — Record 30 seconds of speech for initial voice profile (speaker diarization)
6. **Audio device setup** — Select default microphone and system audio source (desktop)
7. **LLM preference** — Choose local (free, good) vs. cloud (paid, better) for AI processing
8. **Done** — _"I'm ready. Start your first meeting whenever you want."_

### Progressive Learning

- Everything else is learned through use
- The agent starts with generic behavior and progressively personalizes
- No lengthy configuration forms or preference questionnaires

---

## 20. Hardware & Cost Constraints

### Minimum Hardware (Design Target)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Desktop GPU** | None (CPU-only mode) | GTX 970 / 4GB VRAM or better |
| **Desktop RAM** | 8GB | 16GB |
| **Phone** | iPhone SE 2nd gen / Android equivalent | Any modern smartphone |
| **Storage** | 10GB free for app + data | 50GB+ for heavy users |
| **Internet** | Required for cloud features and sync | Faster = better for cloud transcription |

### Cost Philosophy

- **Default path:** Local models for everything — free beyond electricity
- **Cloud option:** Available for users who want better quality and are willing to pay
- **Cost transparency:** The app should clearly show estimated costs when using cloud APIs

### Estimated Running Costs (Cloud Mode)

| Component | Cost |
|-----------|------|
| Transcription (Deepgram) | ~$0.25/hour of audio |
| LLM processing (Claude Sonnet) | ~$0.10-0.50 per meeting |
| Total per meeting (cloud) | ~$0.35-0.75 |
| Monthly (20 meetings, cloud) | ~$7-15 |
| Monthly (local mode) | ~$0 |

---

## 21. Development Phases

### Phase 1: Audio Foundation (Weeks 1-3)

**Goal:** Capture audio and produce clean, speaker-labeled transcripts.

- [ ] Python project scaffold with FastAPI server
- [ ] Audio capture engine: microphone input via SoundDevice
- [ ] Audio capture engine: system audio (WASAPI loopback on Windows)
- [ ] Silero VAD integration for speech detection and chunking
- [ ] faster-whisper integration for local transcription
- [ ] Cloud transcription fallback (Deepgram or AssemblyAI)
- [ ] pyannote-audio speaker diarization
- [ ] SQLite database schema for meetings, transcripts, speakers
- [ ] Basic CLI to start/stop recording and view transcripts
- [ ] Audio compression pipeline (Opus codec, background processing)

**Deliverable:** Working CLI tool that captures meeting audio and produces timestamped, speaker-labeled transcripts.

### Phase 2: Intelligence & Memory (Weeks 4-7)

**Goal:** AI-powered meeting analysis with self-learning memory system.

- [ ] LLM integration: Ollama (local, default) + Claude/OpenAI (cloud options)
- [ ] Post-meeting processing pipeline: executive summary, action items, decisions, topic segmentation
- [ ] Connection detection: linking to past meetings and known entities
- [ ] Insight generation: surfacing things the user might not have thought of
- [ ] Confidence scoring system with configurable badge threshold (default 70%)
- [ ] ChromaDB vector store for semantic search and embeddings
- [ ] Three-tier memory system: short-term, medium-term, long-term (markdown files)
- [ ] Memory consolidation engine (daily during idle, minimum biweekly)
- [ ] Knowledge graph foundation: people, projects, decisions, topics
- [ ] User correction/edit tracking as learning signals
- [ ] Pre-meeting briefing system: user provides context, agent prepares

**Deliverable:** End-to-end pipeline: record meeting → AI-generated structured notes + self-learning memory.

### Phase 3: Desktop App (Weeks 8-10)

**Goal:** Polished desktop application for daily use.

- [ ] Tauri 2.0 app scaffold (Rust + React + TypeScript)
- [ ] System tray integration: always-on background operation
- [ ] Audio device selection UI
- [ ] One-click start/stop recording
- [ ] Three views: executive summary (default), timeline, annotated transcript
- [ ] Topic segment markers with expandable intelligence layers
- [ ] Meeting history with browse and filter
- [ ] Note editing and annotation at any transcript point
- [ ] Transcript correction interface (learning signal)
- [ ] Settings: LLM provider, confidence threshold, wake word, preferences
- [ ] Agent personality toggle: Scribe / Thinking Partner (default) / Sparring Partner
- [ ] Color-coded output by personality mode

**Deliverable:** Functional desktop app with system tray, full meeting lifecycle, and three-view interface.

### Phase 4: Mobile App + Web App (Weeks 11-14)

**Goal:** Phone capture device and web dashboard, fully synced.

- [ ] iOS app (**Swift/SwiftUI** — decided, see Section 24.1 for rationale)
- [ ] Discreet mode: black screen, faint tap acknowledgment (0.3s fade), gesture capture
- [ ] Active mode: breathing dot with escalating urgency, haptic, optional audio alert
- [ ] Tap gestures: single (bookmark), double (priority), long press (voice capture)
- [ ] Voice memo mode: lock screen action + 3x volume-down trigger
- [ ] 15-second silence auto-end + volume button manual end
- [ ] Mode switching via wake word (customizable)
- [ ] Web app: Next.js, full-featured interface, password + optional 2FA
- [ ] Bidirectional sync engine: phone ↔ desktop ↔ cloud
- [ ] Zero-knowledge encryption for cloud storage
- [ ] Offline recording with queued processing
- [ ] Push notifications for processed meetings
- [ ] Natural language search across all meetings and voice memos
- [ ] Audio playback linked to transcript position

**Deliverable:** Complete tri-platform system: desktop app, mobile app, web app, all synced with zero-knowledge encryption.

### Phase 5: Polish & Learning Maturity (Weeks 15-17)

**Goal:** Refine the self-learning engine and polish the full experience.

- [ ] Memory file viewer/editor in all three interfaces
- [ ] Sparring partner personality tuning and intensity controls
- [ ] Cross-meeting connection detection (across multiple meetings)
- [ ] Proactive pre-meeting briefings (agent detects upcoming meetings and prepares)
- [ ] Audio compression optimization
- [ ] Taglish transcription accuracy improvements via learning loop
- [ ] Export: full data export as markdown + JSON
- [ ] Development nudge system: reminds user to proceed with next version after idle
- [ ] Performance optimization for iPhone SE 2nd gen baseline
- [ ] Battery optimization for phone capture mode
- [ ] End-to-end testing with real meetings (15-20 meeting benchmark)

**Deliverable:** Production-ready personal tool that demonstrably improves over 15-20 meetings.

---

## 22. Future Vision (V3+)

These are NOT in scope for V1. They are documented here to ensure architectural decisions don't prevent them.

### V3: Platform Evolution

- Integration with personal project management system (shared knowledge graph)
- Agent creates task cards, notes, reminders in project management tool
- Calendar integration for auto-detecting upcoming meetings
- Advanced learning analytics dashboard
- Multi-tenancy architecture for future public release
- User accounts and authentication infrastructure

### V4: Extended Intelligence

- Always-on listening mode (requires cost/battery breakthrough)
- Secretary app: persistent notifications, follow-up tracking, accountability monitoring
- Document analysis integration (feed documents into the knowledge base)
- Email processing and connection to meeting context

### Public Release Considerations (When Ready)

- App installable on phone and computer, available as web app
- Premium tiers (potential features: panic/lockout, advanced analytics, priority processing)
- Multi-tenancy with strict data isolation
- Scalable infrastructure (PostgreSQL migration path, cloud processing fleet)
- Privacy compliance for multiple jurisdictions

---

## 23. Open Questions & Revisit Items

Items flagged during the brainstorm that need revisiting:

- [ ] **Agent personality: Humble → Assertive progression** — The "relationship maturing" model was agreed on, but the specific implementation details need design work. How does the agent's communication style evolve? What triggers progression?
- [ ] **Product name** — "LIME" is a working title. Candidates discussed: Koda, Segundo, Tahk, Kwago, Tanod, Alisto, Bakas, Nous. Name should work as a wake word (easy to say, unlikely in normal conversation, recognizable by speech recognition).
- [ ] **Sparring partner intensity calibration** — How aggressive is the default? What does the dial-back control look like? Need user testing.
- [ ] **Breathing dot design specifics** — Exact animation parameters, color, size. Needs UI/UX design.
- [ ] **Tap acknowledgment light** — Color, size, exact fade curve for the 0.3s feedback. Needs prototyping.
- [ ] **Mode switching wake word reliability** — How to ensure the agent distinguishes commands directed at it vs. conversation. Needs testing with real meeting audio.
- [ ] **Taglish transcription accuracy** — Need to benchmark Whisper's actual performance on Taglish code-switching and determine if custom fine-tuning is needed.
- [ ] **Merge conflict resolution** — Specific algorithm for merging edits from multiple devices. Needs design.
- [ ] **Voice capture during long press** — How does the system distinguish the user's whispered annotation from ongoing meeting audio? Voice profile + proximity? Needs testing.
- [ ] **iOS lock screen integration** — Technical feasibility of 3x volume-down trigger and lock screen actions on iOS. May have platform restrictions. (Note: Swift chosen partly to maximize feasibility here — `MPRemoteCommandCenter` and native background modes give the best shot. Still needs real-device testing.)

---

## 24. Technical Stack Reference

### Backend (Python)

| Component | Package | Purpose |
|-----------|---------|---------|
| API Server | FastAPI + Uvicorn | REST + WebSocket API |
| Transcription (local) | faster-whisper | Local speech-to-text |
| Transcription (cloud) | deepgram-sdk / assemblyai | Cloud speech-to-text |
| Diarization | pyannote-audio 3.1 | Speaker identification |
| VAD | silero-vad | Voice activity detection |
| Audio Capture | sounddevice | System + mic audio |
| Audio Codec | opuslib / ffmpeg | Audio compression |
| LLM (local) | ollama | Local model inference |
| LLM (cloud) | anthropic / openai | Cloud model inference |
| Vector Store | chromadb | Semantic search + memory |
| Database | SQLAlchemy + SQLite | Structured data |
| Knowledge Graph | networkx | Entity relationships |
| Task Queue | Celery + Redis | Async processing |
| Embeddings | sentence-transformers | Text embeddings |

### Desktop App

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Tauri 2.0 (Rust + WebView) | Lightweight native app |
| Frontend | React + TypeScript | UI components |
| Styling | Tailwind CSS | Rapid, consistent design |
| State | Zustand | Global state management |

### Mobile App (iOS — Swift/SwiftUI)

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Swift 5.9 + SwiftUI (iOS 16+) | Native iOS app |
| Project Gen | XcodeGen (`project.yml`) | Reproducible Xcode project |
| Audio Recording | AVAudioRecorder + AVAudioSession | Microphone capture, background recording |
| Audio Session | AVAudioSession (.playAndRecord) | Interruption handling, route changes, BT |
| Speech | SFSpeechRecognizer (on-device) | Wake word detection, privacy-first |
| Haptics | Core Haptics + UIImpactFeedbackGenerator | Custom per-gesture haptic patterns |
| Gestures | SpatialTapGesture + LongPressGesture | Single/double tap, long press on black screen |
| Networking | URLSession + URLWebSocketTask | REST API + live WebSocket streams |
| Encryption | CryptoKit (AES-256-GCM) + Keychain | Zero-knowledge encryption, key storage |
| Auth | LocalAuthentication (Face ID / Touch ID) | Biometric app lock |
| Connectivity | NWPathMonitor | Offline detection, auto-queue flush |
| Notifications | UserNotifications | Meeting processed, errors, memos |
| Storage | FileManager + UserDefaults | Audio files, offline queue, settings |
| Min Target | iOS 16.0, iPhone SE 2nd gen baseline | Portrait-only, iPhone-only |

### Web App

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | Next.js 15 | Full-featured web interface |
| Search | ChromaDB + full-text (SQLite FTS5) | Semantic + keyword search |
| Editor | TipTap | Rich text note editing |
| Visualization | D3.js / Recharts | Timeline view, knowledge graph |
| Auth | NextAuth.js | Authentication + optional 2FA |

### Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| Sync | Custom sync engine | Bidirectional device sync |
| Encryption | libsodium / NaCl | Zero-knowledge encryption |
| Cloud Storage | S3-compatible (MinIO self-hosted or AWS) | Encrypted data backup |
| Process Queue | Redis | Background task management |

### 24.1 iOS Framework Decision: React Native vs Swift (RESOLVED)

> **Decision date:** February 18, 2026
> **Verdict:** Swift/SwiftUI
> **Status:** Scaffold complete (`mobile/` directory), awaiting Xcode build on macOS

#### Why Swift

LIME's phone app is a **specialized audio capture device**, not a typical mobile app with lists and forms. The core screens are a black screen (discreet mode) and a single breathing dot (active mode). Nearly every feature requires deep native iOS integration, making React Native's abstraction layer a liability.

#### Requirement-by-Requirement Analysis

| Requirement | Swift | React Native | Winner |
|---|---|---|---|
| Lock screen action / 3x volume-down trigger | `MPRemoteCommandCenter`, background modes, media key events | No native API from JS. Custom native module with uncertain lock screen reliability | **Swift** — may be impossible in RN |
| Discreet mode: pure black screen + faint tap light | Full `UIKit`/`SwiftUI` control. Custom `CALayer` animation for 0.3s fade at exact touch point | Native touch handling bridge required. Gesture system adds latency | **Swift** |
| Breathing dot animation with urgency escalation | `Core Animation` / `Metal` — 60fps, GPU-accelerated, minimal battery | `Animated` API or `Reanimated`. Extra battery overhead from JS bridge | **Swift** |
| Tap gestures on black screen | `SpatialTapGesture` + `UIGestureRecognizer` — native, precise | `react-native-gesture-handler` — adds JS bridge hop | **Swift** |
| Haptic patterns (nuanced per-gesture) | Full `Core Haptics` API — custom intensity curves | `react-native-haptic-feedback` — limited to presets | **Swift** |
| Background audio recording (screen off) | `AVAudioSession` with `.playAndRecord` + background mode. Fine-grained control | Possible via bridge, but less control over session management | **Swift** |
| Wake word detection | `SFSpeechRecognizer` + on-device recognition alongside recording | Requires native module bridging to same APIs | **Swift** |
| Volume button manual end (voice memos) | `AVAudioSession` route change + media key monitoring | No reliable volume button interception from JS | **Swift** |
| Battery on iPhone SE 2nd gen | No JS runtime overhead. Direct Metal/GPU. Efficient audio pipeline | JavaScriptCore + bridge serialization = constant CPU tax during recording | **Swift** |
| Biometric auth | `LocalAuthentication` — trivial | `react-native-biometrics` — works | Tie |
| Push notifications | `UserNotifications` | `react-native-push-notification` | Tie |
| Offline recording + sync | `FileManager` + `NWPathMonitor` | `AsyncStorage` / `MMKV` + custom sync | Tie |
| Zero-knowledge encryption | `CryptoKit` (AES-GCM) + Keychain | `react-native-sodium` — wraps same C lib | Tie |

**Result: Swift wins 8 categories, ties 4, loses 0.**

#### Why Code Sharing Doesn't Apply Here

The phone UI has almost nothing in common with desktop/web:
- **Discreet mode:** Black screen. No React components to share.
- **Active mode:** Single breathing dot. One custom animation.
- **Voice memo:** No UI at all — triggered from lock screen.
- **Review:** The only "normal" UI, and it's secondary on phone (heavy review happens on desktop/web).

Shared logic (API client, sync protocol, data models) lives in the backend and is consumed via REST/WebSocket by any client.

#### Android Strategy

iOS first per spec. When Android is needed, Kotlin with the same architecture. React Native's "write once" promise breaks down for the same reasons — core features need native modules on both platforms regardless.

### 24.2 iOS App Scaffold (Current State)

> **Status:** 40 files scaffolded. Requires macOS + Xcode to build.
> **Location:** `mobile/`
> **Build:** Install [XcodeGen](https://github.com/yonaskolb/XcodeGen), run `xcodegen generate` in `mobile/`, open `LIME.xcodeproj`.

```
mobile/
├── project.yml                        # XcodeGen spec (iOS 16+, Swift 5.9, iPhone-only)
├── LIME.xcodeproj/                    # Generated by xcodegen
├── LIME/
│   ├── App/
│   │   ├── LIMEApp.swift              # @main entry, auth gate, onboarding gate, tab navigation
│   │   ├── AppDelegate.swift          # AVAudioSession config, push registration, background tasks
│   │   └── AppState.swift             # Central ObservableObject: recording, agent mode, settings, services
│   │
│   ├── Core/
│   │   ├── Audio/
│   │   │   ├── AudioEngine.swift      # AVAudioRecorder, metering, 30s ring buffer for crash recovery
│   │   │   └── AudioSessionManager.swift  # Interruption handling, route changes, input device selection
│   │   ├── Capture/
│   │   │   ├── GestureEngine.swift    # SpatialTapGesture: single/double/long press + 0.3s faint light feedback
│   │   │   └── VoiceMemoCapture.swift # 15s silence auto-end, duration tracking, completion callback
│   │   ├── WakeWord/
│   │   │   └── WakeWordDetector.swift # On-device SFSpeechRecognizer, configurable wake word, auto-restart
│   │   └── Haptics/
│   │       └── HapticEngine.swift     # Core Haptics: tap/doubleTap/longPress/urgentAlert/recordingStart patterns
│   │
│   ├── Services/
│   │   ├── API/
│   │   │   ├── APIClient.swift        # Full REST client: meetings, memos, search, sync, audio upload
│   │   │   └── WebSocketClient.swift  # Live transcript stream + active mode intelligence alerts, auto-reconnect
│   │   ├── Auth/
│   │   │   └── BiometricAuth.swift    # Face ID / Touch ID with passcode fallback
│   │   ├── Storage/
│   │   │   ├── AudioFileManager.swift # File lifecycle: recording/memo URLs, size tracking, deletion
│   │   │   └── LocalStorage.swift     # Offline upload queue, cached meetings, last sync timestamp
│   │   ├── Sync/
│   │   │   └── SyncEngine.swift       # NWPathMonitor, auto-flush pending uploads on reconnect, bi-sync
│   │   ├── Notifications/
│   │   │   └── NotificationService.swift  # Meeting processed, processing error, memo ready notifications
│   │   └── Encryption/
│   │       └── CryptoService.swift    # AES-256-GCM via CryptoKit, Keychain key storage, export/import for device transfer
│   │
│   ├── Models/
│   │   ├── Meeting.swift              # Meeting, ExecutiveSummary, ActionItem, TopicSegment, Insight, Bookmark, Speaker
│   │   └── VoiceMemo.swift            # VoiceMemo + VoiceMemoStatus (recorded/queued/processing/ready/failed)
│   │
│   ├── Views/
│   │   ├── Meeting/
│   │   │   ├── DiscreetModeView.swift     # Pure black, gesture layer, voice annotation overlay, status bar hidden
│   │   │   ├── ActiveModeView.swift       # Breathing dot, WS alerts panel, gesture layer, duration display
│   │   │   ├── BreathingDotView.swift     # 4-tier urgency: calm(4s) → medium(2.5s) → high(1.5s) → critical(0.6s)
│   │   │   └── MeetingControlsView.swift  # Pre-recording: mode picker + agent picker + record button, triple-tap stop
│   │   ├── Review/
│   │   │   ├── MeetingListView.swift      # Searchable, pull-to-refresh, status badges, action item counts
│   │   │   ├── MeetingDetailView.swift    # 3-view segmented picker: Summary / Timeline / Transcript
│   │   │   ├── ExecutiveSummaryView.swift # Overview, decisions, action items, bookmarks, connections, open questions
│   │   │   ├── TimelineView.swift         # Horizontal topic blocks, heat-map intensity, expandable detail panel
│   │   │   └── TranscriptView.swift       # Speaker-labeled, timestamp markers, expandable intelligence layer
│   │   ├── VoiceMemo/
│   │   │   └── VoiceMemoListView.swift    # Memo list + inline record button + recording banner with stop
│   │   ├── Onboarding/
│   │   │   └── OnboardingFlow.swift       # 5 steps: name → wake word → gesture practice → LLM pref → done
│   │   ├── Settings/
│   │   │   └── SettingsView.swift         # Agent mode, wake word, cloud toggles, confidence slider, storage, auth info
│   │   └── Components/
│   │       ├── ConfidenceBadge.swift       # Color-coded % capsule (red <40%, orange <60%, yellow <70%)
│   │       └── AgentModeToggle.swift       # Scribe(blue) / Thinking Partner(green) / Sparring(red) segmented control
│   │
│   ├── Extensions/
│   │   └── Color+LIME.swift           # Brand palette: limeGreen, mode colors, urgency colors
│   │
│   ├── Resources/
│   │   ├── Info.plist                 # Background modes (audio, processing, fetch), mic/speech/FaceID permissions
│   │   ├── LIME.entitlements          # App groups, push (dev), associated domains
│   │   └── Assets.xcassets/           # App icon placeholder
│   │
│   └── LIME.entitlements
│
└── LIMETests/
    └── LIMETests.swift                # Model, ring buffer eviction, file manager, crypto round-trip tests
```

#### Key Architecture Decisions in Scaffold

| Decision | Detail |
|---|---|
| **State management** | Single `AppState` ObservableObject injected via `@EnvironmentObject`. Holds all services as properties. |
| **30-second ring buffer** | `RingBuffer` struct in AudioEngine retains last 30s of audio chunks. On recording failure, this data is recoverable. |
| **On-device speech only** | `WakeWordDetector` sets `requiresOnDeviceRecognition = true`. No audio sent to Apple for wake word processing. |
| **Offline-first sync** | `SyncEngine` uses `NWPathMonitor`. When offline, uploads queue in `LocalStorage`. Auto-flushes when connectivity returns. |
| **Encryption key in Keychain** | `CryptoService` stores AES-256 key with `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`. Exportable as base64 for device transfer. |
| **Breathing dot animation** | 4 urgency tiers with distinct breath durations (4.0s/2.5s/1.5s/0.6s), scale ranges, and colors (green/yellow/orange/red). |
| **Gesture feedback** | `TapFeedbackView` renders a `RadialGradient` circle (white, 0.15 opacity) at touch point, fades out over 0.3s per spec. |
| **Triple-tap emergency stop** | During recording, a 3-tap gesture on the capture screen stops recording. Ensures user always has an exit. |

#### What's Left to Build (Phase 4 iOS portion)

- [ ] Real Xcode build + resolve any compile issues on macOS
- [ ] Background audio recording real-device testing (AVAudioSession persistence)
- [ ] Lock screen integration: `MPRemoteCommandCenter` for 3x volume-down trigger
- [ ] Audio streaming to backend during recording (currently records locally, uploads after)
- [ ] Voice profile integration with `pyannote` diarization from backend
- [ ] Wake word detector running concurrently with audio recording (shared audio session)
- [ ] Live transcript display in active mode (WebSocket wiring to real backend)
- [ ] App icon and launch screen design
- [ ] TestFlight build + real meeting end-to-end test

---

## API Endpoints (Reference)

```
POST   /api/meetings/start              Start recording
POST   /api/meetings/{id}/stop           Stop recording, trigger processing
GET    /api/meetings/{id}/transcript     Get transcript (live or final)
GET    /api/meetings/{id}/notes          Get AI-generated notes
PATCH  /api/meetings/{id}/notes          Submit edits (triggers learning)
GET    /api/meetings                     List meetings (with filters)
POST   /api/meetings/{id}/briefing       Generate pre-meeting briefing
GET    /api/search?q=...                 Natural language search
POST   /api/voice-memo                   Start voice memo capture
GET    /api/voice-memos                  List voice memos
GET    /api/knowledge/graph              Knowledge graph data
GET    /api/knowledge/people             Known people with profiles
POST   /api/corrections                  Submit transcription corrections
GET    /api/memory/{tier}                View memory files (short/medium/long)
PATCH  /api/memory/{tier}                Edit memory files (learning signal)
WS     /ws/live/{meeting_id}             Live transcription stream
WS     /ws/active-mode/{meeting_id}      Live intelligence alerts (active mode)
POST   /api/sync                         Trigger device sync
GET    /api/export                       Export all data (md + JSON)
```

---

## Project Structure

```
lime/
├── backend/                        # Python backend
│   ├── api/                        # FastAPI routes + WebSocket handlers
│   ├── audio/                      # Audio capture, VAD, chunking, compression
│   ├── transcription/              # Whisper + cloud API wrappers
│   ├── diarization/                # Speaker identification + voice profiles
│   ├── intelligence/               # LLM pipelines (summary, actions, topics, insights)
│   ├── learning/                   # Self-learning engine + feedback loop + memory consolidation
│   ├── knowledge/                  # Knowledge graph + entity extraction
│   ├── storage/                    # ChromaDB, SQLite, file management
│   ├── sync/                       # Bidirectional sync engine + encryption
│   ├── models/                     # SQLAlchemy models + Pydantic schemas
│   └── config/                     # Settings, API keys, preferences
├── desktop/                        # Tauri desktop app
│   ├── src-tauri/                  # Rust backend (audio, tray, native APIs)
│   └── src/                        # React frontend
├── mobile/                         # iOS mobile app
│   └── (React Native or Swift)
├── web/                            # Next.js web dashboard
│   ├── app/                        # App router pages
│   ├── components/                 # Shared UI components
│   └── lib/                        # API client, utilities
├── shared/                         # Shared types, schemas, constants
├── scripts/                        # Setup, migration, dev tools
├── memory/                         # Agent memory files (gitignored in public, synced privately)
│   ├── short-term.md
│   ├── medium-term.md
│   └── long-term.md
└── data/                           # Local data (gitignored)
    ├── audio/                      # Raw + compressed recordings
    ├── db/                         # SQLite + ChromaDB
    └── exports/                    # Exported data
```

---

_This is a living document. Update it after every development milestone. The spec evolves as the product evolves._
