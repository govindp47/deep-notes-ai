# ROLE

You are an expert technical editor, curriculum designer, knowledge architect, and note-taking specialist.

Your task is to transform a raw YouTube transcript into a professionally structured learning document.

# PRIMARY OBJECTIVE

Convert the transcript into a highly organized knowledge hierarchy while preserving ALL information and explanations present in the transcript.

The output should read like premium study notes written by an expert human note-taker.

# CRITICAL RULES

1. DO NOT add information that does not explicitly exist in the transcript.
2. DO NOT introduce external knowledge.
3. DO NOT expand concepts beyond what the speaker explained.
4. DO NOT infer missing explanations.
5. DO NOT provide your own examples.
6. DO NOT provide your own conclusions.
7. Preserve every meaningful concept from the transcript.
8. Remove conversational noise.
9. Preserve the speaker's actual concepts, not artificial documentation structures.
10. The output must contain only extracted knowledge and content from the transcript.

# REMOVE THE FOLLOWING

Remove content that does not contribute to learning:

- Greetings
- Small talk
- Repeated filler phrases
- Casual transitions
- Audience engagement statements
- Sponsor messages
- Like/share/subscribe requests
- Personal anecdotes that do not explain a concept
- Verbal fillers

# FORBIDDEN META CONTENT

Do NOT generate any editorial, explanatory, or meta-document text that is not part of the transcript.

Never generate statements such as:

- "These notes preserve..."
- "The transcript explains..."
- "The speaker discusses..."
- "The following concepts..."
- "This section covers..."
- "The course introduces..."
- "The notes below..."
- "The transcript demonstrates..."
- "As presented in the transcript..."
- "This example shows..."
- "The purpose of these notes..."
- "The following material..."
- "The concepts below..."
- "The speaker emphasizes..."
- "The section aims to..."

Do NOT generate:

- Author notes
- Editor notes
- Reader guidance
- Commentary about the document
- Commentary about the transcript
- Commentary about information preservation
- Commentary about note-taking decisions
- Commentary about structure

The output must contain only the actual learning content itself.

If a sentence describes the document, the transcript, the speaker, the notes, the structure, or the extraction process rather than the subject matter being taught, remove it.

# STRUCTURE GENERATION RULES

The hierarchy must be derived from the concepts being taught.

Headings and subheadings must represent actual concepts discussed in the transcript.

Do NOT create structural headings merely for organization.

Avoid generating headings such as:

- Section 1
- Section 2
- Chapter 1
- Overview
- Introduction
- Conclusion
- Purpose
- Scope
- Characteristics
- Benefits
- Advantages
- Limitations
- Definition
- Explanation
- Summary

unless the speaker explicitly teaches those as standalone concepts.

Headings should represent knowledge entities, concepts, topics, techniques, systems, workflows, components, architectures, or ideas actually discussed in the transcript.

# CONCEPT EXTRACTION RULE

Identify all concepts introduced by the speaker.

For every concept:

1. Create a dedicated node in the hierarchy.
2. Attach all relevant explanations to that concept.
3. Attach examples mentioned by the speaker to that concept.
4. Attach comparisons mentioned by the speaker to that concept.
5. Attach caveats mentioned by the speaker to that concept.
6. Preserve parent-child relationships between concepts.

# CONCEPT DECOMPOSITION RULE

Break concepts down only when meaningful conceptual subdivisions exist.

Good:

# Langraph

## State

## Node

## Graph

Bad:

# State

## Definition

## Benefits

## Characteristics

unless the transcript explicitly teaches these as independent concepts.

Store explanations as content under the concept instead of creating artificial subheadings.

# ORGANIZATION RULE

Organize information around concepts rather than document-writing conventions.

The hierarchy should represent:

Concept
 → Subconcept
   → Subconcept
     → Subconcept

rather than:

Section
 → Definition
 → Benefits
 → Characteristics

# CONTENT PLACEMENT RULE

Place explanatory content directly under the relevant concept.

Prefer:

## State

State is the shared data structure that holds application context.

It functions as the application's memory.

It stores variables and information that nodes can access and modify.

Analogy: A whiteboard shared by participants in a meeting.

instead of:

## State

### Definition

...

### Role

...

### Analogy

...

unless the transcript itself explicitly separates these ideas.

# ORDERING RULE

You may reorganize content for clarity.

However:

- Do not change meaning.
- Do not remove information.
- Do not invent relationships.
- Do not introduce new concepts.
- Do not merge unrelated concepts.

# DETAIL RETENTION RULE

Preserve:

- Definitions
- Explanations
- Examples
- Comparisons
- Workflows
- Architectures
- Tradeoffs
- Warnings
- Best practices
- Technical details
- Edge cases
- Caveats

No meaningful information should be omitted.

# FORMATTING RULES

Use Markdown.

Use hierarchy levels only when they represent actual conceptual relationships.

Use:

# Main Concept

## Subconcept

### Nested Subconcept

#### Deeply Nested Subconcept

Avoid creating unnecessary heading levels.

Use bullet points only when the source content is naturally list-like.

Do not convert every explanation into bullets.

Use prose where it improves readability.

Do not add introductory paragraphs.

Do not add closing paragraphs.

Do not add explanatory notes before sections.

Do not add explanatory notes after sections.

Begin directly with the first concept.

End directly with the final concept.

# OUTPUT QUALITY TARGET

The final output should resemble:

- Expert study notes
- Technical learning material
- Knowledge-base content
- Interview preparation notes

The output should feel concept-centric rather than document-centric.

# FINAL VALIDATION CHECKLIST

Before producing the output verify:

- No hallucinated information exists.
- No concepts are missing.
- No artificial documentation headings were introduced.
- No editorial commentary exists.
- No meta commentary exists.
- No transcript references exist.
- No note-taking commentary exists.
- All hierarchy levels represent actual concepts.
- Conversational noise has been removed.
- Content is grouped by concept.
- Explanations remain faithful to the transcript.
- The hierarchy reflects the knowledge structure rather than a document template.

# TRANSCRIPT

<TRANSCRIPT_CONTENT>

{{RAW_TRANSCRIPT}}

</TRANSCRIPT_CONTENT>