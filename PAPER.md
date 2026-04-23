Final Version 1.0 - Date: 4/14/2026
This is the final version of this requirements document.

# Project 2 Final Paper Requirements

This document defines the required format and expectations for the final project paper.

## Purpose

The paper is a technical report of the system your team actually built, tested, and demonstrated.

## Required Format

- Required final file: PDF
- Layout: single-column
- Font size: 11pt or 12pt (use a reasonable, readable font)
- Page numbers: required
- Writing style: concise, technical, evidence-based
- Citation style: IEEE numeric citations (for example, [1], [2])
- Do not include a Table of Contents, Table of Figures, or Table of Tables
- You may use whatever word processing tool you choose (Word, LaTeX, etc) as long as you produce a PDF for final submission.

## Tool Use Policy

- You may use any tools you want (including AI agents) for drafting, editing, formatting, and polishing.
- You are ultimately responsible for ALL contents including text, images, technical claims, citations, and reported results.
- It is your responsibility to review and correct any tool-generated content for accuracy.
- Revise tool-generated writing so it sounds natural and reflects your own voice; make this easier on yourself by providing the agent with some examples of your own writing.
- Do not fabricate experiments, references, or outcomes.

## Reuse Policy

- You may reuse writing from your own approved proposal.
- Reused text must be revised to match what you actually built and evaluated.
- If major project decisions changed, document those changes in the Proposal Delta section.

## Word Count Requirements

- Target: 2200-2500 words
- Word count applies to the main paper text
- The abstract is excluded from the 2200-2500 word target
- Exclude references, figure/table captions, and appendices from the word count
- Papers substantially outside this range will be penalized unless approved in advance

## Required Sections (In Order)

1. Title and Team Members
2. Abstract (150-250 words)
3. Introduction
4. System Architecture
5. Module Implementation Summary
6. Evaluation Methodology
7. Results
8. Proposal Delta
9. Limitations and Failure Analysis
10. Individual Contributions
11. Conclusions and Future Work
12. References

## Section Expectations

### 1) Title and Team Members

- Clear project title that is evocative of the system; nothing cute.
- Names of all team members

### 2) Abstract (150-250 words)

- Problem and system goal
- Core approach
- Main outcome

### 3) Introduction

- Problem context and motivation
- Scope of the project
- What the system does and does not do

### 4) System Architecture

- High-level description of the full system
- How modules interact
- Data flow through the pipeline

### 5) Module Implementation Summary

- One subsection per module
- For each module: purpose, inputs/outputs, and key design choices
- Briefly describe integration dependencies

### 6) Evaluation Methodology

- What was evaluated
- Metrics used
- Test setup and data used
- How results were collected

### 7) Results

- Report outcomes with concrete evidence
- Include both strengths and weaknesses
- Use figures/tables where appropriate

### 8) Proposal Delta

- This must be a named section titled "Proposal Delta"
- Summarize what changed from the original proposal
- Explain why each major change was made
- Identify any dropped, merged, or rescaled modules

### 9) Limitations and Failure Analysis

- At least 2 concrete limitations or failure cases
- Explain likely causes
- Explain possible improvements

### 10) Individual Contributions

- This must be a named section titled "Individual Contributions"
- List each team member and their concrete contributions
- Include a relative effort estimate for each member (percentages totaling 100%)
- Contribution imbalances may affect individual grades
- As a guideline, an imbalance is significant when a member's share differs from an equal split by more than 20 percentage points

### 11) Conclusions and Future Work

- Summarize what was achieved
- Prioritize realistic next steps

### 12) References

- Cite libraries, APIs, datasets, papers, and tools used
- Use IEEE citation format consistently
- Any external source cited in the paper must appear in this references section
- All references will be checked using agents to determine (1) existence and (2) appropriateness. You should do the same.

## Appendix Guidance

- Appendices are optional.
- Suitable appendix content includes extended results, long tables, extra figures, selected prompts, and non-essential implementation details.
- Do not place core claims or required evaluation evidence only in the appendix.
- Keep long code listings out of the main body; include only short snippets when necessary for explanation.

## Figures and Tables Requirements

- Minimum 3 total visual artifacts (figures and/or tables)
- At least 1 architecture diagram
- At least 1 evaluation results table or plot
- Figures are required and must be cited (\cite{} in LaTeX) within the body text (for example, "Figure 1 shows...")
- Caption placement rule: table captions go above tables, and figure captions go below figures
- Every figure/table must:
	- have a caption,
	- be referenced in the text,
	- be readable at normal zoom,
	- include labeled axes/legends when relevant

## Evidence and Integrity Requirements

- Report what actually happened
- Do not overclaim performance or completion
- All major claims must be supported by evidence (tests, logs, outputs, or demo observations)

## Submission Requirements

Submit one final PDF per team on Moodle.
Before submitting, use an external agent to check that your PDF adheres to all requirements in this document.

Submission logistics:

- File name must be `CSC343_Project_Name1_Name2.pdf`
- One team member submits on Moodle
- The PDF must include the team repository link and any demo link
- Late submissions follow the course late policy in the syllabus

Before submission:

- Run an external agent(s) to review the PDF against this requirements document
- Verify the PDF is complete, readable, and in final form
- Verify all required sections are present
- Verify figures/tables and references appear correctly in the PDF

## Grading Weights

Paper grading uses the following weights:

- Requirements compliance (format, tables/figures, in-text citations, required sections, word count, submission rules, etc.): 10%
- Technical clarity and organization: 10%
- Evaluation methodology and evidence quality: 25%
- Results analysis and honesty of reporting: 25%
- Architecture and implementation coherence: 15%
- References and citation quality: 5%
- Proposal Delta and Individual Contributions sections: 10%

Required narrative sections not listed as standalone grading lines, including Title and Team Members, Abstract, Introduction, Limitations and Failure Analysis, and Conclusions and Future Work, are assessed through Technical clarity and organization and Results analysis and honesty of reporting, with baseline inclusion enforced under Requirements compliance.

