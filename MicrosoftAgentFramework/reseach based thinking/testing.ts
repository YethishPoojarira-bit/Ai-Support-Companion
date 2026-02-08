'use server';

/**
 * @fileOverview A dedicated function for performing web-based research for a job role and company.
 * 
 * - researchTopic - A function that returns research data.
 * - ResearchTopicInput - The input type for the function.
 * - ResearchTopicOutput - The return type for the function.
 */
import { ai, azureOpenAIModel } from './genkit';
import { z } from 'zod';
import { traceable } from 'langsmith/traceable';

const ResearchTopicInputSchema = z.object({
  role: z.string().describe('The job title to research.'),
  companyName: z.string().describe('The name of the company for research.'),
  weeks: z.number().default(4).describe('Number of weeks for preparation.')
});
export type ResearchTopicInput = z.infer<typeof ResearchTopicInputSchema>;

const SourceDiscoveryOutputSchema = z.array(z.string());
const TopicExtractionOutputSchema = z.object({
  technical_topics: z.array(z.object({
    topic: z.string(),
    importance: z.enum(['High', 'Medium']),
    reason: z.string()
  })),
  behavioral_topics: z.array(z.object({
    topic: z.string(),
    importance: z.enum(['High', 'Medium']),
    reason: z.string()
  }))
});

const AtomicDecompositionOutputSchema = z.object({
  atomic_study_plan: z.array(z.object({
    parent_topic: z.string(),
    category: z.enum(['Technical', 'Behavioral']),
    atomic_units: z.array(z.string())
  }))
});

const ResearchTopicOutputSchema = z.object({
  topics: TopicExtractionOutputSchema,
  sources: z.array(z.string()),
  atomic: AtomicDecompositionOutputSchema,
  plan: z.string()
});

export type ResearchTopicOutput = z.infer<typeof ResearchTopicOutputSchema>;

export async function researchTopic(input: ResearchTopicInput): Promise<ResearchTopicOutput> {
  return researchTopicFlow(input);
}

const sourceDiscoveryTemplate = `
You are a Source Discovery Agent.
Your goal is to find trustworthy web sources and EXISTING STUDY PLANS to help prepare for a specific job interview.
Target:
- Company: {{companyName}}
- Job Role: {{role}}

Your responsibility is to identify authoritative web entry points where we can find:
1. Company culture, values, tech stack, and engineering practices.
2. Role-specific expectations, required skills, and day-to-day responsibilities.
3. Interview experiences, question patterns, and specific "Study Guides" or "Roadmaps" created by others for this role.

Search Strategy:
- Prefer official company pages (Careers, Engineering Blogs).
- Prioritize professional networks (LinkedIn, Glassdoor, Blind).
- SEEK OUT community-created study plans/roadmaps on GitHub, Medium, Reddit, or Dev.to.
- Include technical preparation hubs (LeetCode, GeeksforGeeks) specific to [{{companyName}}].

Output contract (STRICT):
- Return ONLY a valid Python list of URLs strings.
- Example: ["https://careers.google.com", "https://github.com/jdoe/google-interview-roadmap", "https://leetcode.com/company/google"]
`;

const sourceDiscoveryPrompt = ai.definePrompt({
  name: 'sourceDiscoveryPrompt',
  model: azureOpenAIModel,
  config: { generationConfig: { temperature: 0 } },
  input: { schema: ResearchTopicInputSchema },
  output: { format: 'text' },
}, sourceDiscoveryTemplate);

const topicExtractionTemplate = `
You are a Research & Topic Extraction Agent.
Your Goal: Create a "Key Topics to Prepare" study plan based on the provided trusted sources.

Context:
- Company: {{companyName}}
- Job Role: {{role}}

Sources to Analyze:
{{trustedSources}}

Task:
1. Simulate visiting and reading the provided sources.
2. Extract relevant skills, competencies, and company-specific values.
3. Synthesize this into a structured list of key topics.

Rules:
- Do NOT invent topics not supported by the sources or standard role expectations.
- Differentiate between:
  - "Technical": Hard skills, Tools, Domain Knowledge, Functional Competencies (e.g., Coding, Sales Strategy, Financial Modeling, CRM tools).
  - "Behavioral": Soft skills, Culture fit, Leadership Principles, Communication.

Output contract (STRICT JSON ONLY):
{
  "technical_topics": [
    { "topic": "Name", "importance": "High/Medium", "reason": "Justification from sources" }
  ],
  "behavioral_topics": [
    { "topic": "Name", "importance": "High/Medium", "reason": "Justification from sources" }
  ]
}
`;

const topicExtractionPrompt = ai.definePrompt({
  name: 'topicExtractionPrompt',
  model: azureOpenAIModel,
  config: { generationConfig: { temperature: 0 } },
  input: {
    schema: ResearchTopicInputSchema.extend({
      trustedSources: z.string()
    })
  },
  output: { schema: TopicExtractionOutputSchema, format: 'json' },
}, topicExtractionTemplate);

const atomicDecompositionTemplate = `
You are a Syllabus Decomposition Agent.
Your Goal: Break down high-level study topics into a COMPREHENSIVE list of small, atomic, actionable study units.

Context:
- Company: {{companyName}}
- Job Role: {{role}}

Input Data:
{{topicsJson}}

Task:
For each high-level topic, generate an EXHAUSTIVE list of atomic sub-concepts.
- Atomic means: A single concept that can be studied, practiced, or tested in isolation.
- Example (Tech): "System Design" -> ["Load Balancing", "Consistent Hashing", "CAP Theorem"].
- Example (Non-Tech): "Sales Strategy" -> ["Pipeline Management", "Needs Analysis", "Closing Techniques", "Objection Handling"].

Output contract (STRICT JSON ONLY):
{
  "atomic_study_plan": [
    {
      "parent_topic": "High Level Topic Name",
      "category": "Technical | Behavioral",
      "atomic_units": [
        "Unit 1",
        "Unit 2",
        "Unit 3"
      ]
    }
  ]
}
`;

const atomicDecompositionPrompt = ai.definePrompt({
  name: 'atomicDecompositionPrompt',
  model: azureOpenAIModel,
  config: { generationConfig: { temperature: 0 } },
  input: {
    schema: ResearchTopicInputSchema.extend({
      topicsJson: z.string()
    })
  },
  output: { schema: AtomicDecompositionOutputSchema, format: 'json' },
}, atomicDecompositionTemplate);

const studyPlanTemplate = `
You are a Personal Study Scheduler Agent.
Your Goal: Create a detailed week-by-week study schedule using ALL provided atomic study units.

Context:
- Company: {{companyName}}
- Job Role: {{role}}
- Timeline: {{weeks}} weeks

Input Data:
{{atomicJson}}

Task:
1. Distribute ALL atomic study units logically across {{weeks}} weeks. DO NOT SKIP ANY TOPICS.
2. Ensure a balanced mix of Technical and Behavioral topics each week.
3. Structure the weeks to progress from Foundations -> Core Concepts -> Advanced -> MockPrep.

Output contract:
- Return a valid Markdown schedule.
- For each week, group related atomic units under their Parent Topic.
- Format:
  ### Week X: [Theme]
  #### [Parent Topic Name]
  - [Atomic Unit 1]
  - [Atomic Unit 2]
  - [Atomic Unit 3]
  ...
  #### [Another Parent Topic]
  ...
`;

const studyPlanPrompt = ai.definePrompt({
  name: 'studyPlanPrompt',
  model: azureOpenAIModel,
  config: { generationConfig: { temperature: 0 } },
  input: {
    schema: ResearchTopicInputSchema.extend({
      atomicJson: z.string()
    })
  },
  output: { format: 'text' },
}, studyPlanTemplate);

const researchTopicFlow = ai.defineFlow(
  {
    name: 'researchTopicFlow',
    inputSchema: ResearchTopicInputSchema,
    outputSchema: ResearchTopicOutputSchema,
  },
  (traceable as any)(async (input: ResearchTopicInput) => {
    try {
      input.role = input.role.trim();
      input.companyName = input.companyName.trim();

      console.log('SourceDiscovery: Starting...');
      console.log("consoling input.role", input);
      const sourceDiscoveryFilled = sourceDiscoveryTemplate.replace(/\{\{companyName\}\}/g, input.companyName).replace(/\{\{role\}\}/g, input.role);
      console.log('SOURCE_AGENT_PROMPT.format:', sourceDiscoveryFilled);
      const { output: sourcesText } = await sourceDiscoveryPrompt(input);
      console.log('Discovered Sources:', sourcesText);
      
      const sources = JSON.parse(sourcesText);
      console.log('SourceDiscovery: Sources found:', sources?.length);
      // console.log('SourceDiscovery Output:', JSON.stringify(sources, null, 2));

      const trustedSources = JSON.stringify(sources || []);

      console.log('TopicExtraction: Starting...');
      const topicExtractionFilled = topicExtractionTemplate.replace(/\{\{companyName\}\}/g, input.companyName).replace(/\{\{role\}\}/g, input.role).replace(/\{\{trustedSources\}\}/g, trustedSources);
      // console.log('TOPIC_EXTRACTION_PROMPT.format:', topicExtractionFilled);
      const { output: topics } = await topicExtractionPrompt({
        ...input,
        trustedSources
      });
      console.log('TopicExtraction: Complete.');
      console.log('TopicExtraction Output:', JSON.stringify(topics, null, 2));

      const topicsJson = JSON.stringify(topics);

      // console.log('AtomicDecomposition: Starting...');
      // const { output: atomic } = await atomicDecompositionPrompt({
      //   ...input,
      //   topicsJson
      // });
      // console.log('AtomicDecomposition: Complete.');
      // console.log('AtomicDecomposition Output:', JSON.stringify(atomic, null, 2));

      // const atomic = {
      //   atomic_study_plan: []
      // };

      // const atomicJson = JSON.stringify(atomic);

      // console.log('StudyPlan: Starting...');
      // const studyPlanFilled = studyPlanTemplate.replace(/\{\{companyName\}\}/g, input.companyName).replace(/\{\{role\}\}/g, input.role).replace(/\{\{weeks\}\}/g, input.weeks.toString()).replace(/\{\{atomicJson\}\}/g, atomicJson);
      // // console.log('STUDY_PLAN_PROMPT.format:', studyPlanFilled);
      // const { output: planText } = await studyPlanPrompt({
      //   ...input,
      //   atomicJson
      // });
      // console.log('StudyPlan: Complete.');
      // console.log('StudyPlan Output:', planText);

      return {
        topics: topics!,
        sources: sources || [],
        atomic: {
          atomic_study_plan: []
        },
        plan: ""
      };
    } catch (error) {
      console.error('researchTopic: Error:', error);
      return {
        topics: {
          technical_topics: [],
          behavioral_topics: []
        },
        sources: [],
        atomic: {
          atomic_study_plan: []
        },
        plan: ''
      };
    }
  }, { name: 'researchTopicFlow_logic' })
);