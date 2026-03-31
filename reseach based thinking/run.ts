import { researchTopic, ResearchTopicInput } from './testing';

async function main() {
  const input: ResearchTopicInput = {
    role: 'Business Developer',
    companyName: 'Google',
    weeks: 4
  };

  console.log('Running Research Topic Flow...');
  const result = await researchTopic(input);
  console.log('Final Result:', JSON.stringify(result, null, 2));
}

main().catch(console.error);
