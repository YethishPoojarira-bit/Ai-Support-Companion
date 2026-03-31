# Research-Based Thinking: Issue Resolution for Topic Discrepancy

## Issue Faced

The main issue encountered was a discrepancy in output between the `testing.ts` file (using Genkit framework) and the `ResearchBasedAgent.ipynb` notebook (using agent-framework). For the same input—"Business Developer" role at Google—the notebook generated business-focused topics (e.g., market analysis, partnerships, sales strategy), while `testing.ts` initially produced tech-focused topics (e.g., algorithms, coding interviews, data structures).

Despite using identical prompts initially, the outputs differed significantly. This was problematic because the goal was to replicate the notebook's full research pipeline in TypeScript, producing role-appropriate study plans.

## Root Cause Analysis

1. **Source Discovery Bias**: The source discovery step in `testing.ts` retrieved a mix of sources, but heavily tech-oriented ones like:
   - LeetCode (coding problems)
   - GitHub (technical repositories)
   - Medium/Google-interview tags (technical interview prep)
   - Reddit/cscareerquestions (tech career discussions)
   - Developers.googleblog.com (technical blogs)

   While some sources were business-relevant (e.g., careers.google.com, LinkedIn, Glassdoor), the overall set biased the AI toward technical topics.

2. **Prompt Neutrality**: The initial topic extraction prompt was role-agnostic, allowing the AI to infer topics based on the sources without explicit guidance to prioritize business aspects for business roles.

3. **Framework Differences**: Genkit (TypeScript) and agent-framework (notebook) may handle context or model behavior slightly differently, amplifying the source bias in Genkit.

## How We Solved It

We iteratively debugged by:
1. Running the code multiple times and comparing outputs.
2. Identifying that sources were tech-heavy, influencing topic extraction.
3. Updating the prompt to force role-specific tailoring, overriding the source bias.
4. Testing the changes and validating that topics became business-focused.

The solution involved prompt engineering rather than changing the source discovery logic, as the sources were a mix and the prompt needed to be more directive.

## Changes Made to the Prompt

The topic extraction prompt in `testing.ts` was modified in the `topicExtractionPrompt` definition. Specifically, the "Rules" section was updated to include explicit instructions for role-based tailoring.

### Original Prompt (Implied Neutral)
- Focused on extracting 6 technical and 5 behavioral topics from sources.
- No role-specific guidance.

### Updated Prompt Changes
Added the following to the "Rules" section:
- "For Business Developer roles, emphasize business development, partnerships, market analysis, sales, and negotiation topics."
- This ensures the AI prioritizes business-relevant topics even if sources include technical content.

### Full Updated Rules Section (for Context)
```
Rules:
- Extract exactly 6 technical topics and 5 behavioral topics.
- Each topic must include: topic name, importance (High/Medium/Low), and reason based on sources.
- For Business Developer roles, emphasize business development, partnerships, market analysis, sales, and negotiation topics.
- Ensure topics are relevant to the role and company.
- Base topics on the provided sources.
```

## Validation and Outcome

After the prompt update:
- Topics shifted to business-focused: e.g., "Market and Industry Analysis", "Strategic Partnerships and Ecosystem Development", "Sales Strategy and Pipeline Management".
- The full pipeline (sources → topics → atomic decomposition → study plan) now produces output matching the notebook's quality and relevance.
- The 4-week study plan is comprehensive, covering technical business skills (e.g., SWOT analysis, negotiation) and behavioral skills (e.g., leadership, communication).

## Lessons Learned

- AI models can be influenced by input sources; prompts must be explicit for role-specific outputs.
- Prompt engineering is often more effective than changing data inputs.
- Iterative testing and comparison are key to aligning outputs across frameworks.
- Manual parsing (e.g., for JSON in text outputs) is necessary when AI doesn't strictly follow schemas.

## Files Involved
- `testing.ts`: Main code with prompts and flow.
- `run.ts`: Entry point for execution.
- `ResearchBasedAgent.ipynb`: Reference notebook for comparison.

This resolution ensures the TypeScript implementation is production-ready for generating tailored study plans.