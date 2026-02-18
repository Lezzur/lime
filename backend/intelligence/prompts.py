"""
Prompt templates for the post-meeting intelligence pipeline.

All prompts instruct the LLM to return structured JSON for reliable parsing.
"""

SYSTEM_PROMPT = """You are LIME's intelligence engine — a cognitive meeting analysis system.
You analyze meeting transcripts and extract structured insights with precision.
Always respond with valid JSON only. No markdown, no explanation outside JSON.
If you are uncertain about something, lower the confidence score rather than guessing."""


EXECUTIVE_SUMMARY_PROMPT = """Analyze the following meeting transcript and produce an executive summary.

<transcript>
{transcript}
</transcript>

Return a JSON object with this exact structure:
{{
  "summary": "2-4 paragraph executive summary covering: what the meeting was about, key discussion points, how it concluded, and any notable outcomes",
  "meeting_type": "standup|planning|review|brainstorm|decision|general",
  "sentiment": "positive|neutral|mixed|tense",
  "participant_count_estimate": 0
}}"""


ACTION_ITEMS_PROMPT = """Extract all action items from the following meeting transcript.
An action item is a task someone committed to doing, was assigned, or that was agreed upon.

<transcript>
{transcript}
</transcript>

Return a JSON object with this exact structure:
{{
  "action_items": [
    {{
      "description": "Clear description of what needs to be done",
      "owner": "Name of person responsible, or null if unassigned",
      "deadline": "Mentioned deadline or timeframe, or null if none stated",
      "priority": "high|medium|low",
      "confidence": 0.0,
      "source_quote": "Brief exact quote from transcript that supports this item",
      "source_start_time": 0.0,
      "source_end_time": 0.0
    }}
  ]
}}

Rules:
- Only include items explicitly stated or clearly implied in the transcript
- Set confidence between 0.0 and 1.0 based on how clearly the item was stated
- Use source_start_time and source_end_time from the transcript timestamps
- If no action items exist, return an empty array"""


DECISIONS_PROMPT = """Extract all decisions made during the following meeting.
A decision is a conclusion, agreement, or choice that was explicitly made by the participants.

<transcript>
{transcript}
</transcript>

Return a JSON object with this exact structure:
{{
  "decisions": [
    {{
      "description": "Clear description of the decision",
      "context": "Brief context about why this decision was made",
      "participants": ["Names of people involved in making this decision"],
      "confidence": 0.0,
      "source_quote": "Brief exact quote from transcript",
      "source_start_time": 0.0,
      "source_end_time": 0.0
    }}
  ]
}}

Rules:
- Only include actual decisions, not topics that were discussed but left unresolved
- Set confidence between 0.0 and 1.0 based on how clearly the decision was stated
- If no decisions were made, return an empty array"""


TOPIC_SEGMENTATION_PROMPT = """Segment the following meeting transcript into distinct topics of discussion.
Meetings often switch between topics and may return to earlier topics (A→B→A pattern).

<transcript>
{transcript}
</transcript>

Return a JSON object with this exact structure:
{{
  "topics": [
    {{
      "title": "Short descriptive title for this topic segment",
      "summary": "1-2 sentence summary of what was discussed",
      "start_time": 0.0,
      "end_time": 0.0,
      "confidence": 0.0,
      "related_topic_indices": []
    }}
  ]
}}

Rules:
- Topics should be in chronological order
- start_time and end_time should match transcript timestamps
- If a topic recurs (A→B→A), create separate entries and link them via related_topic_indices (0-based)
- Aim for natural topic boundaries, not arbitrary time splits
- Set confidence between 0.0 and 1.0 based on how clear the topic boundary is
- Each topic should span at least 30 seconds of discussion"""
